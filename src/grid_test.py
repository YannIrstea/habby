import time
import numpy as np
import os.path

from src.MergeL import build_hyd_sub_mesh, merge, build_hyd_data
from src.plot_mod import plot_to_check_mesh_merging


def run_test(nbpointhyd, nbpointsub, seedhyd=6, seedsub=42, rectangles=np.array([[0, 0, 100, 100], ]),
             coefficient_list=[0.5], defautsub=np.array([1, 1]), results_file="results.csv"):
    defautsub = np.array([1, 1])
    hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data = create_mesh_in_shape(nbpointhyd, nbpointsub, rectangles, seedhyd,
                                                                      seedsub)
    hyd_data, iwholeprofile, hyd_data_c = build_hyd_data(hyd_xy, hyd_tin, 7, 22, 33)
    for coeffgrid in coefficient_list:
        t0 = time.time()
        nxymerge1, niklemerge1, iwholeprofilemerge, merge_data_c, datasubmerge = merge(hyd_xy, hyd_data, hyd_tin,
                                                                                       iwholeprofile, hyd_data_c,
                                                                                       sub_xy, sub_tin, sub_data,
                                                                                       defautsub, coeffgrid)
        t1 = time.time()
        dt = t1 - t0
        results = open(results_file, "a")
        results.write(str(nbpointhyd) + "," + str(nbpointsub) + "," + str(len(niklemerge1)) + "," + str(
            len(nxymerge1)) + "," + str(coeffgrid) + "," + str(dt) + "\n")
        results.close()
        print("nhyd=", nbpointhyd, " nsub=", nbpointsub, " coeffgrid=", coeffgrid, " time=", dt)


def create_mesh_in_shape(nbpointhyd, nbpointsub, rectangles, seedhyd=6, seedsub=42):
    """
    :param rectangles: numpy array with 4 columns where each line contains (x0, y0, width, height) for a rectangle
    """
    vertices, shapes = rectangles[:, 0:2], rectangles[:, 2:4]
    rectangle_area = np.prod(shapes, axis=1)
    total_area = np.sum(rectangle_area)
    area_proportion = rectangle_area / total_area
    hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data = build_hyd_sub_mesh(False, int(area_proportion[0] * nbpointhyd),
                                                                    int(area_proportion[0] * nbpointsub), seedhyd,
                                                                    seedsub, vertices[0], shapes[0])
    for i in range(1, len(rectangles)):
        hyd_xyi, hyd_tini, sub_xyi, sub_tini, sub_datai = build_hyd_sub_mesh(False,
                                                                             int(area_proportion[i] * nbpointhyd),
                                                                             int(area_proportion[i] * nbpointsub),
                                                                             seedhyd * (i + 1), seedsub * (i + 1),
                                                                             vertices[i], shapes[i])
        hyd_tin = np.concatenate((hyd_tin, hyd_tini + len(hyd_xy)), axis=0)
        sub_tin = np.concatenate((sub_tin, sub_tini + len(sub_xy)), axis=0)
        hyd_xy, sub_xy, sub_data = np.concatenate((hyd_xy, hyd_xyi)), np.concatenate((sub_xy, sub_xyi)), np.concatenate(
            (sub_data, sub_datai))

    return hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data


defautsub = np.array([1, 1])

rectangles = np.array([[0, 0, 50, 30], [40, 30, 10, 70], [50, 80, 50, 20]])
coefficient_list = np.linspace(0.1, 5, 50)

if not os.path.exists("results.csv"):
    results = open("results.csv", "w")
    results.write("nhyd,nsub,mesh_elements,mesh_nodes,coeffgrid,time\n")
    results.close()

nbpointvalues = range(500, 5500, 500)
for nbpointhyd in nbpointvalues:
    for nbpointsub in nbpointvalues:
        run_test(nbpointhyd, nbpointsub, 6, 42, rectangles, coefficient_list)
