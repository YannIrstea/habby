import numpy as np
import scipy.optimize
import scipy.stats
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import csv
import math
import grid_test
from grid_test import read_result_files


def approx(x):
    if x % 1 <= 0.5:
        return int(x)
    else:
        return int(x) + 1


def linear_function(x, a, b):
    return a * x + b


def quadratic_function(x, a, b, c):
    return a * x ** 2 + b * x + c


def quadratic_fit(x, y):
    (a, b, c), pcov = scipy.optimize.curve_fit(quadratic_function, x, y)
    return a, b, c


def exponential_function(x, a, b, c):
    return a * np.exp(b * x) + c


def fit_and_plot(data, startline, endline, return_nopt=False, draw_plot=True):

    analysis = np.array(data[startline:endline]).astype(np.float64)
    grid_coefficient=analysis[:,4]
    t = analysis[:,5]
    nhyd=analysis[0][0]
    nsub=analysis[0][1]
    a, b, c = quadratic_fit(grid_coefficient, t)
    y = quadratic_function(grid_coefficient, a, b, c)
    if draw_plot:
        fig=plt.figure()
        ax=fig.add_subplot()
        ax.set_title("nhyd="+str(nhyd)+"; "+"nsub="+str(nsub))
        ax.set_xlabel("coefficient")
        ax.set_ylabel("temps")
        ax.plot(grid_coefficient, t, "b+")
        ax.plot(grid_coefficient, y)


    grid_coefficient_min = (-b / (2 * a))
    print("optimal coefficient= " + str(grid_coefficient_min))
    if return_nopt:
        return grid_coefficient_min

def interpret_old(data,lock_nsubvalue=False,nsubvalue=None):
    nhyd = []
    nsub = []
    optimal_coefficient = []
    for i in range(1, len(data), 50):
        analysis = np.array(data[i:i + 50]).astype(np.float64)
        if analysis[0][1]==nsubvalue or lock_nsubvalue==False:
            grid_coefficient = analysis[:,4]
            t = analysis[:,5]
            nhyd += [analysis[0][0]]
            nsub+= [analysis[0][1]]
            minindex= np.argmin(t, axis=0)
            # optimal_coefficient+=[grid_coefficient[minindex]]
            optimal_coefficient+=[fit_and_plot(data,i,i+50,True,False)]
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(nhyd,nsub,optimal_coefficient, c="r", marker="o")
    ax.set_xlabel("noeuds hydrauliques")
    ax.set_ylabel("noeuds substrat")
    ax.set_zlabel("coefficient optimal")

# def read_result_files(filename, shape):
#     file = open(filename, "r")
#     flat_array = file.read()
#     flat_array = str.split(flat_array, ",")[:-1]
#     array = np.reshape(flat_array, (shape)).astype(np.float)
#     return array

def plot_time(time_results,nbpointsvalueshyd,nbpointvaluessub,coefficient_list,grid_methods,values):
    #plots time×coeffgrid for each method in grid_methods
    #values should be a tuple containing nbnoeudshyd and nbnoeudssub
    i=list.index(list(nbpointsvalueshyd),values[0])
    j=list.index(list(nbpointvaluessub),values[1])
    plt.plot(coefficient_list,time_results[i,j,:,0],"ro")
    plt.plot(coefficient_list,time_results[i,j,:,1],"bo")
    plt.plot(coefficient_list,time_results[i,j,:,2],"go")
    plt.plot(coefficient_list, time_results[i, j, :, 3], "yo")
    plt.plot(coefficient_list, time_results[i, j, :, 4], "ko")



if __name__=="__main__":
    # nbpointvalueshyd = [4000,7000,10000]
    # nbpointvaluessub = [5000]
    # coefficient_list = np.linspace(31,45,15)
    # grid_methods = [0,1,2,3,4]
    # time_output_shape=(10,3,10,2)
    # mesh_densities=read_result_files("mesh_output.csv")[0]
    time_results,labels,values=read_result_files("time_output.csv")
    # print(mesh_densities)
    # print(time_results)
    plot_time(time_results,values[0],values[1],values[2],values[3],(5000,2000))
    print(time_results)
    best_times=np.min(time_results,2)
    print(best_times)

    avgtime=np.average(best_times[:,:,:],(0,1))
    print(avgtime)


    plt.show()


