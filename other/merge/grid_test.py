from MergeL import build_hyd_sub_mesh, merge, build_hyd_data, tinareadensity
import time
import numpy as np
import multiprocessing as mp


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
            len(nxymerge1)) + "," + str(hyd_mesh_density) + "," + str(sub_mesh_density) + "," + str(
            coeffgrid) + "," + str(dt) + "\n")
        results.close()
        print("nhyd=", nbpointhyd, " nsub=", nbpointsub, " coeffgrid=", coeffgrid, " time=", dt)
        ##TODO prendre la densite
        ##TODO


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


def calculate_time(nbpointhyd, nbpointsub, seedhyd, seedsub, coefficient_list, grid_methods, defautsub, time_array,
                   mesh_array, array_i=None, array_j=None, output_shape=[10, 10, 1]):
    hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data = build_hyd_sub_mesh(False, nbpointhyd, nbpointsub, seedhyd, seedsub)
    hyd_data, iwholeprofile, hyd_data_c = build_hyd_data(hyd_xy, hyd_tin, 7, 22, 33)
    hyd_mesh_density = tinareadensity(hyd_xy, hyd_tin)[1]
    sub_mesh_density = tinareadensity(sub_xy, sub_tin)[1]
    mesh_array[2 * output_shape[1] * array_i + 2 * array_j] = hyd_mesh_density
    mesh_array[2 * output_shape[1] * array_i + 2 * array_j + 1] = sub_mesh_density

    for k in range(len(coefficient_list)):
        coeffgrid = coefficient_list[k]
        for l in range(len(grid_methods)):
            t0 = time.time()
            merge_xy1, merge_data_node, merge_tin1, iwholeprofilemerge, merge_data_mesh, merge_data_sub_mesh = merge(
                hyd_xy, hyd_data,
                hyd_tin,
                iwholeprofile,
                hyd_data_c,
                sub_xy,
                sub_tin,
                sub_data,
                defautsub,
                coeffgrid,
                grid_methods[l])
            t1 = time.time()
            dt = t1 - t0
            time_array[np.prod(output_shape[1:]) * array_i + np.prod(output_shape[2:]) * array_j + output_shape[
                3] * k + l] = dt  # time_array is a flat shared array that will later be reshaped to have the correct form
            print("nhyd=",nbpointhyd,"nsub=",nbpointsub,"\n","coefficient=",coeffgrid,"grid method :",l)
            print("time=",dt)



def run_process(nodenumberslisthyd, nodenumberslistsub, seedhyd, seedsub, coefficient_list, grid_methods, defautsub,
                out_time_array, out_mesh_array, core_index=0, process_count=1):
    output_shape = (len(nodenumberslisthyd), len(nodenumberslistsub), len(coefficient_list), len(grid_methods))
    for i in range(core_index, len(nodenumberslisthyd), process_count):
        for j in range(len(nodenumberslistsub)):
            calculate_time(nodenumberslisthyd[i], nodenumberslistsub[j], seedhyd, seedsub, coefficient_list,
                           grid_methods, defautsub, out_time_array, out_mesh_array, i, j, output_shape)


def read_result_files(filename, shape):
    file = open(filename, "r")
    flat_array = file.read()
    flat_array = str.split(flat_array, ",")[:-1]
    array = np.reshape(flat_array, (shape)).astype(np.float)
    return array


# rectangles = np.array([[0, 0, 50, 30], [40, 30, 10, 70], [50, 80, 50, 20]])

# if not os.path.exists("results.csv"):
#     results = open("results.csv", "w")
#     results.write("nhyd,nsub,mesh_elements,mesh_nodes,sub_mesh_density,hyd_mesh_density,coeffgrid,time\n")
#     results.close()


if __name__ == "__main__":
    core_count = mp.cpu_count() - 2
    defautsub = np.array([1, 1])
    coefficient_list = np.logspace(-1, 1, 10)
    # nbpointvalues = range(500, 5500, 500)
    nbpointvalueshyd = range(500,5500,500)
    nbpointvaluessub = [1000,3000,5000]
    nbgridvalues = len(coefficient_list)
    grid_methods = [0, 1]
    output_shape = (len(nbpointvalueshyd), len(nbpointvaluessub), len(coefficient_list), len(grid_methods))
    nbdonnees = len(("mesh_density", "triangle_number", "grid_coefficient", "time"))
    time_shared_array = mp.Array("d", np.zeros(np.prod(output_shape)))
    prearray = np.frombuffer(time_shared_array.get_obj())
    results = prearray.reshape(output_shape)

    mesh_densities_shared_array = mp.Array("d", np.zeros(np.prod(output_shape[0:2]) * 2))
    ##mesh_densities is a m×n×2 array containing the hyd and sub mesh densities for each pair nhyd,nsub
    mesh_densities = np.frombuffer(mesh_densities_shared_array.get_obj()).reshape((output_shape[0], output_shape[1], 2))

    if core_count > len(nbpointvalueshyd):
        process_count = core_count
    else:
        process_count = len(nbpointvalueshyd)
    processes = [None for _ in range(process_count)]

    for core_index in range(process_count):
        processes[core_index] = mp.Process(target=run_process, args=(
        nbpointvalueshyd, nbpointvaluessub, 6, 42, coefficient_list, grid_methods, defautsub, time_shared_array,
        mesh_densities_shared_array, core_index, process_count))
    for core_index in range(process_count):
        processes[core_index].start()
    for core_index in range(process_count):
        processes[core_index].join()

    time_output = open("time_output.csv", "w")
    mesh_output = open("mesh_output.csv", "w")
    for elem in time_shared_array:
        time_output.write(str(elem) + ",")
    for elem in mesh_densities_shared_array:
        mesh_output.write(str(elem) + ",")
    time_output.close()
    mesh_output.close()


