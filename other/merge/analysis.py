import numpy as np
import scipy.optimize
import scipy.stats
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import csv
import math


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

def interpret(data,lock_nsubvalue=False,nsubvalue=None):
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






if __name__=="__main__":

    file=open("results.csv","r")
    reader=csv.reader(file)
    data=[]
    for row in reader:
        data+=[row]
    interpret(data)
    # fit_and_plot(data,1,51,False,True)
    plt.show()



