import numpy as np
import scipy.optimize
import scipy.stats
from matplotlib import pyplot as plt
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
    analysis = np.array(data[startline:endline]).T.astype(np.float)
    ngrid = analysis[4]
    t = analysis[5]
    a, b, c = quadratic_fit(ngrid, t)
    y = quadratic_function(ngrid, a, b, c)
    if draw_plot:
        plt.plot(ngrid, t, "b+")
        plt.plot(ngrid, y)

    ngrid_min = (-b / (2 * a))
    print("optimal ngrid= " + str(ngrid_min))
    if return_nopt:
        return ngrid_min


# file = open("results.txt", "r")
# reader = csv.reader(file)
# data = []
# for row in reader:
#     data += [row]

# n = []
# nopt = []
# noptsq = []
# for i in range(2, len(data), 45):
#     analysis = np.array(data[i:i + 45]).T.astype(np.float)
#     ngrid = analysis[4]
#     t = analysis[9]
#     n += [analysis[0][0]]
#     print("n1=", analysis[0][0])
#     index = np.argmin(t, axis=0)
#     nopt += [fit_and_plot(data, i, i + 45, return_nopt=True, draw_plot=False)]
#     noptsq += [nopt[-1] ** 2]

file=open("results.csv","r")
reader=csv.reader(file)
data=[]
for row in reader:
    data+=[row]
fit_and_plot(data,1,-1)




# index = n.index(3000)
# n = np.array(n)
# nexp = n[:index]
# nlin = n[index:]
# noptexp = nopt[:index]
# noptlin = nopt[index:]
# regression = scipy.stats.linregress(nlin, noptlin)
# a1, b1 = regression[0], regression[1]
# print(regression)
# ylin = linear_function(nlin, a1, b1)
# plt.plot(nlin, ylin)

# plt.plot(n, nopt, "r+")
# (a2, b2, c2), pcov = scipy.optimize.curve_fit(exponential_function, nexp, noptexp, p0=(-70, -0.001, 70))
# print(a2, b2, c2)
# yexp = exponential_function(nexp, a2, b2, c2)
# plt.plot(nexp, yexp, "g")

plt.show()
