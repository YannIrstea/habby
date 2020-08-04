import multiprocessing as mp
import numpy as np
from multiprocessing import Process,Value,Array
def f(x):
    return x*x
def fbutharder(x,y):
    # x=tuple[0]
    # y=tuple[1]
    return x**x**x-y**y**y
def fbuteasier(x,y,results,i,j,m,n):
    results[flattened_array_coordinate(i,j,m,n)]=2*x+y
    # return 2*x+y
def flattened_array_coordinate(i,j,m,n):
    table=np.reshape(range(m*n),(m,n))
    return table[i][j]


if __name__ == '__main__':
    output=mp.Queue()
    m,n=5,10
    p=[0,]*10

    shared_array=mp.Array("d",n*m)

    # # prearray=np.frombuffer(shared_array.get_obj())
    # results=np.frombuffer(shared_array).reshape((m,n))

    # results=mp.Array("d",16)
    # print(results)
    # for elem in results:
    #     print(elem)
    # # results=mp.Array("d",[mp.Array("d",[0. for _ in range(4)]) for _ in range(4)])
    # # results=mp.Array("d",[[0 for _ in range(4)] for _ in range(4)])

    processes = [[None for _ in range(n)] for _ in range(m)]
    print(processes)
    for i in range(m):
        for j in range(n):
            processes[i][j]=mp.Process(target=fbuteasier,args=(i,j,shared_array,i,j,m,n))
    for i in range(m):
        for j in range(n):
            processes[i][j].start()
    for i in range(m):
        for j in range(n):
            processes[i][j].join()
    results=np.reshape(shared_array,(m,n))
    print(results)

    array=np.array(range(30))
    narray=array.reshape((6,5))
    print(narray)





    # results=mp.Array("d",10)
    # for i in range(10):
    #     p[i]=mp.Process(target=fbuteasier,args=(i,1+i,results,i,i))
    # for i in range(10):
    #     p[i].start()
    # for i in range(10):
    #     p[i].join()
    #     results[i]=output.get()
    #     print("what")
    # print(results[:])


# from multiprocessing import Process, Value, Array
#
# def f(n, a):
#     n.value = 3.1415927
#     for i in range(len(a)):
#         a[i] = -a[i]
#
# if __name__ == '__main__':
#     num = Value("d", 0.0)
#     arr = Array('i', range(10))
#
#     p = Process(target=f, args=(num, arr))
#     p.start()
#     p.join()
#
#     print(num.value)
#     print(arr[:])


