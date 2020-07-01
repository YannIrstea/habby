import numpy as np

from src import hdf5_mod
from src.hydrosignature import hydrosignature_calculation


def load_hydraulic_cut_to_hdf5(path_prj, hdf5_name_hyd):
    '''
    testing the hydrosignature program
    '''
    # load data_2d
    hdf5_hydro = hdf5_mod.Hdf5Management(path_prj, hdf5_name_hyd)
    hdf5_hydro.load_hdf5_hyd(units_index="all", whole_profil=True)

    # for each reach
    for reach_num in range(hdf5_hydro.data_2d.reach_num):
        # for each unit
        for unit_num in range(hdf5_hydro.data_2d.unit_num):
            # t = 0  # regarding this value different tests can be launched
            # if t == 0:  # random nbpointhyd, nbpointsub are the number of nodes/points to be randomly generated respectively for hydraulic and substrate TIN
            #     classhv = [[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 3], [0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 5]]
            #     hyd_tin = np.array([[0, 1, 3], [0, 3, 4], [1, 2, 3], [3, 4, 6], [3, 6, 7], [4, 5, 6]])
            #     hyd_xy_node = np.array([[821128.213280755, 1867852.71720679], [821128.302459342, 1867853.34262438],
            #                             [821128.314753232, 1867854.93690708], [821131.385434587, 1867854.6662084],
            #                             [821132.187889633, 1867852.67553172], [821136.547596803, 1867851.73984275],
            #                             [821136.717311027, 1867853.21858062], [821137.825096539, 1867853.68]])
            #     hyd_hv_node = np.array(
            #         [[1.076, 0.128], [0.889999985694885, 0.155], [0, 0], [0, 0], [0.829999983310699, 0.145], [1.127, 0.143],
            #          [0.600000023841858, 0.182], [0, 0]])
            #

            # input
            tin = hdf5_hydro.data_2d[reach_num][unit_num]["mesh"]["tin"]
            # ...

            # compute
            total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume = hydrosignature_calculation(
                classhv, hyd_tin, hyd_xy_node, hyd_hv_node)
            print(total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity,
                  max_velocity, hsarea, hsvolume)

            #save to attributes
            hdf5_hydro.data_2d[reach_num][unit_num].hs_total_area = total_area
            # ...

    # save to hdf5
    hdf5_hydro.add_hs()


    # export txt

