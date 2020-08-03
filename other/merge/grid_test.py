from MergeL import build_hyd_sub_mesh, merge, build_hyd_data, tinareadensity
import time
import numpy as np
import multiprocessing as mp
import cProfile


#
# def run_test(nbpointhyd, nbpointsub, seedhyd=6, seedsub=42, rectangles=np.array([[0, 0, 100, 100], ]),
#              coefficient_list=[0.5], defautsub=np.array([1, 1]), results_file="results.csv"):
#     defautsub = np.array([1, 1])
#     hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data = create_mesh_in_shape(nbpointhyd, nbpointsub, rectangles, seedhyd,
#                                                                       seedsub)
#     hyd_data, iwholeprofile, hyd_data_c = build_hyd_data(hyd_xy, hyd_tin, 7, 22, 33)
#     for coeffgrid in coefficient_list:
#         t0 = time.time()
#         nxymerge1, niklemerge1, iwholeprofilemerge, merge_data_c, datasubmerge = merge(hyd_xy, hyd_data, hyd_tin,
#                                                                                        iwholeprofile, hyd_data_c,
#                                                                                        sub_xy, sub_tin, sub_data,
#                                                                                        defautsub, coeffgrid)
#         t1 = time.time()
#         dt = t1 - t0
#         results = open(results_file, "a")
#         results.write(str(nbpointhyd) + "," + str(nbpointsub) + "," + str(len(niklemerge1)) + "," + str(
#             len(nxymerge1)) + "," + str(hyd_mesh_density) + "," + str(sub_mesh_density) + "," + str(
#             coeffgrid) + "," + str(dt) + "\n")
#         results.close()
#         print("nhyd=", nbpointhyd, " nsub=", nbpointsub, " coeffgrid=", coeffgrid, " time=", dt)
#         ##TODO prendre la densite
#         ##TODO


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
                   mesh_array, array_i=None, array_j=None, output_shape=[10, 10, 1], array_k=None, array_l=None,
                   parallelizing_coefficient=False):
    hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data = build_hyd_sub_mesh(False, nbpointhyd, nbpointsub, seedhyd, seedsub)
    hyd_data, iwholeprofile, hyd_data_c = build_hyd_data(hyd_xy, hyd_tin, 7, 22, 33)
    hyd_mesh_density = tinareadensity(hyd_xy, hyd_tin)[1]
    sub_mesh_density = tinareadensity(sub_xy, sub_tin)[1]
    mesh_array[2 * output_shape[1] * array_i + 2 * array_j] = hyd_mesh_density
    mesh_array[2 * output_shape[1] * array_i + 2 * array_j + 1] = sub_mesh_density

    if parallelizing_coefficient:
        coeffgrid = coefficient_list[array_k]
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
            grid_methods[array_l])
        t1 = time.time()
        dt = t1 - t0
        time_array[np.prod(output_shape[1:]) * array_i + np.prod(output_shape[2:]) * array_j + output_shape[
            3] * array_k + array_l] = dt  # time_array is a flat shared array that will later be reshaped to have the correct form
        print("nhyd=", nbpointhyd, "nsub=", nbpointsub, "\n", "coefficient=", coeffgrid, "grid method :", array_l)
        print("time=", dt)

    else:
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
                print("nhyd=", nbpointhyd, "nsub=", nbpointsub, "\n", "coefficient=", coeffgrid, "grid method :", l)
                print("time=", dt)


def calculate_time_given_mesh(mesh, coefficient_list, grid_methods, defautsub, time_array, output_shape, array_i,
                              array_j, array_k, array_l):
    t0 = time.time()
    i, j, k, l = array_i, array_j, array_k, array_l
    merge_xy1, merge_data_node, merge_tin1, iwholeprofilemerge, merge_data_mesh, merge_data_sub_mesh = merge(
        mesh["hyd_xy"][i][j], mesh["hyd_data"][i][j],
        mesh["hyd_tin"][i][j],
        mesh["iwholeprofile"][i][j],
        mesh["hyd_data_c"][i][j],
        mesh["sub_xy"][i][j],
        mesh["sub_tin"][i][j],
        mesh["sub_data"][i][j],
        defautsub,
        coefficient_list[k],
        grid_methods[l])
    t1 = time.time()
    dt = t1 - t0
    time_array[np.prod(output_shape[1:]) * array_i + np.prod(output_shape[2:]) * array_j + output_shape[
        3] * array_k + array_l] = dt  # time_array is a flat shared array that will later be reshaped to have the correct form
    print("nhyd=", len(mesh["hyd_xy"]), "nsub=", len(mesh["sub_xy"]), "\n", "coefficient=", coefficient_list[k],
          "grid method :", array_l)
    print("time=", dt)


def generate_mesh_set(nbpointhydlist, nbpointsublist, seedhyd, seedsub, seed1, seed2, seed3, output_mesh_density=False):
    m, n = len(nbpointhydlist), len(nbpointsublist)
    mesh_density_output = [[[[] for _ in [0, 1]] for j in range(n)] for i in range(m)]
    hyd_xylist = [[[] for j in range(n)] for i in range(m)]
    hyd_tinlist = [[[] for j in range(n)] for i in range(m)]
    sub_xylist = [[[] for j in range(n)] for i in range(m)]
    sub_tinlist = [[[] for j in range(n)] for i in range(m)]
    sub_datalist = [[[] for j in range(n)] for i in range(m)]
    hyd_datalist = [[[] for j in range(n)] for i in range(m)]
    iwholeprofilelist = [[[] for j in range(n)] for i in range(m)]
    hyd_data_clist = [[[] for j in range(n)] for i in range(m)]
    for i in range(m):
        for j in range(n):
            hyd_xylist[i][j], hyd_tinlist[i][j], sub_xylist[i][j], sub_tinlist[i][j], sub_datalist[i][
                j] = build_hyd_sub_mesh(False, nbpointhydlist[i], nbpointsublist[j], seedhyd, seedsub)
            hyd_datalist[i][j], iwholeprofilelist[i][j], hyd_data_clist[i][j] = build_hyd_data(hyd_xylist[i][j],
                                                                                               hyd_tinlist[i][j], seed1,
                                                                                               seed2, seed3)
            if output_mesh_density:
                mesh_density_output[i][j][0] = tinareadensity(hyd_xylist[i][j], hyd_tinlist[i][j])[1]
                mesh_density_output[i][j][1] = tinareadensity(sub_xylist[i][j], sub_tinlist[i][j])[1]
    if output_mesh_density:
        return {"hyd_xy": hyd_xylist, "hyd_tin": hyd_tinlist, "sub_xy": sub_xylist, "sub_tin": sub_tinlist,
                "sub_data": sub_datalist, "hyd_data": hyd_datalist, "iwholeprofile": iwholeprofilelist,
                "hyd_data_c": hyd_data_clist, "mesh_density": mesh_density_output}
    else:
        return {"hydxy": hyd_xylist, "hyd_tin": hyd_tinlist, "sub_xy": sub_xylist, "sub_tin": sub_tinlist,
                "sub_data": sub_datalist, "hyd_data": hyd_datalist, "iwholeprofile": iwholeprofilelist,
                "hyd_data_c": hyd_data_clist}

def run_process(mesh, nodenumberslisthyd, nodenumberslistsub, coefficient_list, grid_methods, defautsub,
                out_time_array, core_index=0, process_count=1):
    output_shape = (len(nodenumberslisthyd), len(nodenumberslistsub), len(coefficient_list), len(grid_methods))
    # for i in range(core_index, len(nodenumberslisthyd), process_count):
    for i in range(len(nodenumberslisthyd)):
        for j in range(len(nodenumberslistsub)):
            for k in range(core_index, len(coefficient_list), process_count):
                for l in range(len(grid_methods)):
                    calculate_time_given_mesh(mesh, coefficient_list, grid_methods, defautsub, out_time_array,
                                              output_shape, i, j, k, l)

def read_result_files(filename, shape=None):
    file = open(filename, "r")
    file_text = file.read()
    ##file will have the form metadata=label1,label2,label3,|dim1,dim2,dim3,|values1;values2;values3|xxx,xxx,xxx,...
    if file_text[:9] == "metadata=":
        splitfile = file_text[9:].split("|")
        labels = splitfile[0].split(",")
        shape = np.array(splitfile[1].split(",")).astype(int)
        values = []
        for elem in splitfile[2].split(";"):
            try:
                values += [np.array(elem.split(",")).astype(np.int)]
            except ValueError:
                values += [np.array(elem.split(",")).astype(np.float)]
        # values=np.array(values)
        flat_array = splitfile[3].split(",")

    else:
        flat_array = str.split(file_text, ",")
        labels = ""
    # print(flat_array)
    array = np.reshape(flat_array, shape).astype(np.float)
    return array, labels, values

def write_result_files(filename, flat_array, labels, output_shape, values_list):
    f = open(filename, "w")
    f.write("metadata=")
    towrite = ""
    for l in labels:
        towrite += str(l) + ","
    f.write(towrite[:-1] + "|")
    towrite = ""
    for dim in output_shape:
        towrite += str(dim) + ","
    f.write(towrite[:-1] + "|")
    towrite = ""
    for list in values_list:
        for value in list:
            towrite += str(value) + ","
        towrite = towrite[:-1] + ";"
    f.write(towrite[:-1] + "|")
    towrite = ""
    for elem in flat_array:
        towrite += str(elem) + ","
    f.write(towrite[:-1])
    f.close()

def run_test():
    core_count = mp.cpu_count() - 1
    defautsub = np.array([1, 1])
    coefficient_list = np.linspace(0.5, 10, 20)
    # nbpointvalues = range(500, 5500, 500)
    nbpointvalueshyd = [2000,5000,7000]
    nbpointvaluessub = [3000,6000]
    nbgridvalues = len(coefficient_list)
    grid_methods = [0, 1, 2, 3, 4]
    output_shape = (len(nbpointvalueshyd), len(nbpointvaluessub), len(coefficient_list), len(grid_methods))
    nbdonnees = len(("mesh_density", "triangle_number", "grid_coefficient", "time"))
    time_shared_array = mp.Array("d", np.zeros(np.prod(output_shape)))
    prearray = np.frombuffer(time_shared_array.get_obj())
    results = prearray.reshape(output_shape)

    # mesh_densities_shared_array = mp.Array("d", np.zeros(np.prod(output_shape[0:2]) * 2))
    # ##mesh_densities is a m×n×2 array containing the hyd and sub mesh densities for each pair nhyd,nsub
    # mesh_densities = np.frombuffer(mesh_densities_shared_array.get_obj()).reshape(
    #     (output_shape[0], output_shape[1], 2))
    mesh = generate_mesh_set(nbpointvalueshyd, nbpointvaluessub, 7, 42, 13, 2, 9, True)
    mesh_densities_flat_array=np.array(mesh["mesh_density"]).flatten()

    if core_count > len(coefficient_list):
        process_count = core_count
    else:
        process_count = len(coefficient_list)
    processes = [None for _ in range(process_count)]

    for core_index in range(process_count):
        processes[core_index] = mp.Process(target=run_process, args=(
            mesh, nbpointvalueshyd, nbpointvaluessub, coefficient_list, grid_methods, defautsub, time_shared_array,
            core_index, process_count))
    for core_index in range(process_count):
        processes[core_index].start()
    for core_index in range(process_count):
        processes[core_index].join()

    write_result_files("time_output.csv", time_shared_array,
                       ["hydraulic nodes", "substrate nodes", "grid coefficient", "grid method"], output_shape,
                       [nbpointvalueshyd, nbpointvaluessub, coefficient_list, grid_methods])
    write_result_files("mesh_output.csv", mesh_densities_flat_array,
                       ["hydraulic nodes", "substrate nodes", "mesh type"], [output_shape[0], output_shape[1], 2],
                       [nbpointvalueshyd, nbpointvaluessub, [0, 1]])


    # time_output = open("time_output.csv", "w")
    # mesh_output = open("mesh_output.csv", "w")
    # time_output.write(
    #     "metadata=hydraulic nodes,substrate nodes,grid coefficient,grid method|" + str(output_shape)[1:-1].replace(", ",
    #                                                                                                                ",") + "|"+str(nbpointvalueshyd)[1:-1].replace(", ",","))
    # time_output.write()
    # mesh_output.write(
    #     "metadata=hydraulic nodes,substrate nodes|" + str(output_shape[:2])[1:-1].replace(", ", ",") + ",2|")
    # for elem in time_shared_array:
    #     time_output.write(str(elem) + ",")
    # for elem in mesh_densities_shared_array:
    #     mesh_output.write(str(elem) + ",")
    # time_output.close()
    # mesh_output.close()

    # rectangles = np.array([[0, 0, 50, 30], [40, 30, 10, 70], [50, 80, 50, 20]])

    # if not os.path.exists("results.csv"):
    #     results = open("results.csv", "w")
    #     results.write("nhyd,nsub,mesh_elements,mesh_nodes,sub_mesh_density,hyd_mesh_density,coeffgrid,time\n")
    #     results.close()

if __name__ == "__main__":
    print("to rodando")
    run_test()
    # time_results,time_results_labels=read_result_files("time_output.csv")
    # mesh_results,mesh_results_labels=read_result_files("mesh_output.csv")
    # print("time")
    # print(time_results)
    # print(time_results_labels)
    # print("mesh")
    # print(mesh_results)
    # print(mesh_results_labels)
