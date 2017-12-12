import numpy as np
import bisect
from src import load_hdf5
from src import manage_grid_8
import scipy.interpolate


def chronic_hydro(merge_files, path_merges, discharge_input, discharge_output, name_prj, path_prj
                  , min_height=0.0, model_type='chronic_hydro'):
    """
    This function used the hydraulic data (velocity and height) modelled at particular discharges to estimate hydraulic
    data at the discharge given in dicharge_output. This function would only work well if the discharge in the outputs
    are close to the discharge present in the merge_files. Indeed, this function is just a linear interpolation, so
    it only functions for small changes in discharges. It cannot be used in cases where the discharge in dicharge output
    is outside the range modelled or there were not a sufficient number of discharges modelled.

    We assume that the subtrate is not changing as a function of the discharge.

    :param merge_files: A list with the name of the file merged
    :param path_merges: the paths to these files
    :param discharge_input: the discharge for each time steps in the merges files (careful, we might have a
            merge file with more than one time step, so len(marge_file) != len(discharge_input) is possible
    :param discharge_output: a list with the time and discharge for the output
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: in this case, it is ""chronic_hydro", this is not really an hydraulic model.
    :param min_height: the minimum water height acceptable to be accounted for
    :return: A new merge file where each time step has the discharge given in discharge output
    """
    failload = [-99]
    warn1 = True
    sim_name_all = []
    ikle_full = []
    point_all_full = []
    inter_vel_full = []
    inter_height_full = []
    substrate_pg_full = []
    substrate_dom_full = []

    # load all merge
    if len(merge_files) != len(path_merges):
        print("Error: the name of the hydraulic files and their paths is not coherent. \n")
        return failload

    if len(discharge_input)<2:
        print('Error: at least two discharge needed as input\n')
        return failload

    ikle_all_m = []
    point_all_m = []
    inter_vel_all_m = []
    inter_height_all_m = []
    substrate_pg_all_m = []
    substrate_dom_all_m = []

    for i in range(0, len(merge_files)):
        [ikle_all, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom] = \
            load_hdf5.load_hdf5_hyd(merge_files[i], path_merges[i], True)
        # special cases and checks
        if len(ikle_all) == 1 and ikle_all[0] == [-99]:
            print('Error: hydrological data could not be loaded.')
            return failload
        if not ikle_all:
            print('Error: no connectivity table found for the hydrology. Check the format of the hdf5 file. \n')
            return failload
        # add hydro data to list
        ikle_all_m.extend(ikle_all[1:])  # first profile is full profile without water
        point_all_m.extend(point_all[1:])
        inter_vel_all_m.extend(inter_vel_all[1:])
        inter_height_all_m.extend(inter_height_all[1:])
        substrate_pg_all_m.extend(substrate_all_pg[1:])
        substrate_dom_all_m.extend(substrate_all_dom[1:])

        # simulation name
        sim_name = load_hdf5.load_timestep_name(merge_files[i], path_merges[i])
        sim_name_all.extend(sim_name)

        # one full, uncut, dry profile (if more than one, take the first one)
        if i ==0:
            ikle_full = ikle_all[0]
            point_all_full = point_all[0]
            inter_vel_full = inter_vel_all[0]
            inter_height_full = inter_height_all[0]
            substrate_pg_full = substrate_all_pg[0]
            substrate_dom_full = substrate_all_dom[0]

    if len(merge_files) == 0:
        print('Error: no merge files given \n')
        return

    # check if discharge in put is coherent with merge
    if len(discharge_input) != len(ikle_all_m):
        print('Error: The number of discharge inputs is not equal to the number of timesteps in the merge files \n')
        return failload
    if len(list(set(discharge_input))) != len(discharge_input):
        print('Error: Two identical discharges in the input data \n')
        return failload

    # order discharge and data so it goes from the lower dicharge to the highest
    ind = np.argsort(discharge_input)

    discharge_input = [discharge_input[i] for i in ind]
    ikle_all_m = [ikle_all_m[i] for i in ind]
    point_all_m = [point_all_m[i] for i in ind]
    inter_vel_all_m = [inter_vel_all_m[i] for i in ind]
    inter_height_all_m = [inter_height_all_m[i] for i in ind]
    substrate_pg_all_m = [substrate_pg_all_m[i] for i in ind]
    substrate_dom_all_m = [substrate_dom_all_m[i] for i in ind]

    # for each discharge output, we calculate the new height and velocity
    dmax = max(discharge_input)
    dmin = min(discharge_input)
    # here we add the full first dry profile to the future output
    # the other time step will be added in the loop below
    ikle_all_new = [ikle_full]
    point_all_new = [point_all_full]
    inter_vel_all_new = [inter_vel_full]
    inter_height_all_new = [inter_height_full]
    substrate_pg_all_new = [substrate_pg_full]
    substrate_dom_all_new = [substrate_dom_full]
    # the interpolation on the original discharge should be kept aswe might re-use more than once
    vel_base_inter = [[] for i in range(0, len(discharge_input))]
    height_base_inter =[[] for i in range(0, len(discharge_input))]

    for idx, d in enumerate(discharge_output):

        # check if in the range, if not ignore
        if d > dmax or d < dmin:
            ikle_all_new.append([])
            point_all_new.append([])
            inter_vel_all_new.append([])
            inter_height_all_new.append([])
            substrate_pg_all_new.append([substrate_pg_full])
            substrate_dom_all_new.append([substrate_dom_full])
            if warn1:
                print('Warning: One or more output are neglected as they are outside of the modelling range. \n')
                warn1 = False
        else:
            # if yes, find the two discharge inputs close to the discharge output
            indh = bisect.bisect(discharge_input, d) - 1  # dicharge min

            dis_min = discharge_input[indh]
            dis_max = discharge_input[indh + 1]

            # cases where the discharge is already known
            if d == dis_max:
                ikle_all_new.append(ikle_all_m[indh+1])
                point_all_new.append(point_all_m[indh+1])
                inter_vel_all_new.append(inter_vel_all_m[indh + 1])
                inter_height_all_new.append(inter_height_all_m[indh + 1])
                substrate_pg_all_new.append(substrate_pg_all_m[indh+1])
                substrate_dom_all_new.append(substrate_dom_all_m[indh + 1])
            elif d == dis_min:
                ikle_all_new.append(ikle_all_m[indh])
                point_all_new.append(point_all_m[indh])
                inter_vel_all_new.append(inter_vel_all_m[indh])
                inter_height_all_new.append(inter_height_all_m[indh])
                substrate_pg_all_new.append(substrate_pg_all_m[indh])  # updated based on the cut_2d_grid
                substrate_dom_all_new.append(substrate_dom_all_m[indh])

            # cases where the difference is too big betwen input and asked outputs
            # TO DO find a good rule for this.
            elif 1 == 0:
                ikle_all_new.append([])
                point_all_new.append([])
                inter_vel_all_new.append([])
                inter_height_all_new.append([])
                substrate_pg_all_new.append([substrate_pg_full])
                substrate_dom_all_new.append([substrate_dom_full])
                if warn1:
                    print('Warning: One or more output are neglected as the difference between modelled discharge was '
                          'too big. \n')
                    warn1 = False

            # normal case, calculation should be done
            else:
                # we use the grid of the higher discharge (often the bigger one even if not true everywhere)
                ikle_here_all_r = ikle_all_m[indh+1]
                point_here_all_r = point_all_m[indh+1]
                vel_base_here_high = inter_vel_all_m[indh + 1]
                height_base_here_high = inter_height_all_m[indh + 1]
                substrate_pg_base_here_high = substrate_pg_all_m[indh+1]
                substrate_dom_base_here_high = substrate_dom_all_m[indh + 1]

                # check if an interpolation between these two discharges exists
                if len(vel_base_inter[indh]) > 0:
                    vel_base_here = vel_base_inter[indh]
                    height_base_here = height_base_inter[indh]

                else:
                    # if not found, interpolate the lower discharge to the grid of the higher dicharge
                    point_old_all_r = point_all_m[indh]
                    vel_old_all_r = inter_vel_all_m[indh]
                    height_old_all_r = inter_height_all_m[indh]

                    # The mean of vel_base_here will be lower than the mean of vel_old_all_r as we add area with 0
                    # [vel_base_here, height_base_here, blob, blob] = manage_grid_8.pass_grid_cell_to_node_lin(
                    #     point_here_all_r, point_old_all_r, vel_old_all_r, height_old_all_r, False)
                    vel_base_here = []
                    height_base_here = []
                    for r in range(0, len(vel_base_here_high)):
                        # linear interpolation is not a good choice here
                        inter_vel = scipy.interpolate.griddata(point_old_all_r[r], vel_old_all_r[r], point_here_all_r[r],
                                                               method='nearest')
                        inter_vel[np.isnan(inter_vel)] = 0
                        inter_h = scipy.interpolate.griddata(point_old_all_r[r], height_old_all_r[r], point_here_all_r[r],
                                                             method='nearest')
                        inter_h[np.isnan(inter_h)] = 0
                        vel_base_here.append(inter_vel)
                        height_base_here.append(inter_h)

                    # figures to debug the interpolation
                    # ikle_old_all_r = ikle_all_m[indh]
                    # manage_grid_8.plot_grid_simple(point_old_all_r, ikle_old_all_r, {},vel_old_all_r, height_old_all_r,
                    #                                path_prj)
                    # manage_grid_8.plot_grid_simple(point_here_all_r, ikle_here_all_r, {}, vel_base_here, height_base_here,
                    #                                path_prj)
                    # import matplotlib.pyplot as plt
                    # plt.show()

                # for each point of the grid of the higher discharge, get the velocity and the heigth data
                # data = (1_x)* data_low + x * data_low where x depends on the dicharge d
                x = (d-dis_min)/(dis_max - dis_min)
                if x > 1 or x < 0:
                    x = 0.0
                vel_here = []
                height_here = []
                for r in range(0, len(vel_base_here)):
                    vel_here_r = (1-x) * vel_base_here[r] + x * vel_base_here_high[r]
                    height_here_r = (1-x) * height_base_here[r] + x*height_base_here_high[r]
                    vel_here.append(vel_here_r)
                    height_here.append(height_here_r)

                # figures to debug cutting
                # manage_grid_8.plot_grid_simple(point_here_all_r, ikle_here_all_r, {}, vel_here, height_here,path_prj)

                # figure of the old input (high - low )
                # ikle_old_all_r = ikle_all_m[indh]
                # manage_grid_8.plot_grid_simple(point_here_all_r, ikle_here_all_r, {}, vel_base_here_high,
                #                                height_base_here_high, path_prj)
                # manage_grid_8.plot_grid_simple(point_old_all_r, ikle_old_all_r, {}, vel_old_all_r, height_old_all_r,
                # path_prj)

                # # cut the new grid to the water height is zeros
                [ikle_here_all_r, point_here_all_r, height_here, vel_here, ind_new_all] = \
                    manage_grid_8.cut_2d_grid_all_reach(ikle_here_all_r, point_here_all_r, height_here, vel_here,
                                                        min_height, True)

                # figures to debug cutting
                # manage_grid_8.plot_grid_simple(point_here_all_r, ikle_here_all_r, {}, vel_here, height_here, path_prj)
                # import matplotlib.pyplot as plt
                # plt.show()

                # figure to debug the result
                # manage_grid_8.plot_grid_simple(point_here_all_r, ikle_here_all_r, {}, vel_here, height_here, path_prj)
                # import matplotlib.pyplot as plt
                # plt.show()

                # save data for this discharge
                ikle_all_new.append(ikle_here_all_r)
                point_all_new.append(point_here_all_r)
                inter_vel_all_new.append(vel_here)
                inter_height_all_new.append(height_here)
                # substrate data
                sub_pg_all_r = []
                sub_dom_all_r = []
                for r in range(0, len(ikle_here_all_r)):
                    sub_pg_here = [substrate_pg_base_here_high[r][i] for i in ind_new_all[r]]
                    sub_dom_here = [substrate_dom_base_here_high[r][i] for i in ind_new_all[r]]
                    sub_pg_all_r.append(sub_pg_here)
                    sub_dom_all_r.append(sub_dom_here)
                substrate_pg_all_new.append(sub_pg_all_r)  # updated based on the cut_2d_grid
                substrate_dom_all_new.append(sub_dom_all_r)

    # save in a new merge file
    discharge_output_str = list(map(str,discharge_output))
    name_hdf5 = 'Chronic_' + merge_files[0][:-3]
    load_hdf5.save_hdf5(name_hdf5, name_prj, path_prj, model_type, 2, path_merges[0], ikle_all_new, point_all_new, [],
                        inter_vel_all_new, inter_height_all_new,  merge=True, sub_pg_all_t=substrate_pg_all_new,
                        sub_dom_all_t=substrate_dom_all_new, sim_name=discharge_output_str)



def main():
    """
    Used to test this module
    """

    merge_files = ['MERGE_Hydro_RIVER2D_test23.00.h5']
    path_merges = [r'D:\Diane_work\dummy_folder\inter_test\fichier_hdf5']
    discharge_input = range(23, 85)
    np.savetxt('discharge_river2d.txt', discharge_input, delimiter='\n')
    discharge_output = np.arange(28, 32) + 0.5
    name_prj = 'inter_test'
    path_prj = r'D:\Diane_work\dummy_folder\inter_test'
    chronic_hydro(merge_files, path_merges, discharge_input, discharge_output, name_prj, path_prj, 0.001)


if __name__ == '__main__':
    main()