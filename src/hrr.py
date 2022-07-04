import sys
import os
from io import StringIO
from time import sleep
import numpy as np
import pandas as pd
from multiprocessing import Value, Queue

from src.hdf5_mod import Hdf5Management
from src.manage_grid_mod import connectivity_mesh_table
from src.data_2d_mod import Data2d
from src.project_properties_mod import load_project_properties, save_project_properties


def analyse_whole_profile(i_whole_profile1,i_whole_profile2):
    iwpmax=max(max(i_whole_profile1),max(i_whole_profile2))

    sortwp1=np.c_[i_whole_profile1,np.arange(len(i_whole_profile1))]
    sortwp2 = np.c_[i_whole_profile2,np.arange(len(i_whole_profile2))]
    sortwp1 = sortwp1[np.lexsort((sortwp1[:, 1], sortwp1[:, 0]))]
    sortwp2 = sortwp2[np.lexsort((sortwp2[:, 1], sortwp2[:, 0]))]
    iwholedone = np.zeros((iwpmax+1,),  dtype=np.int8)
    rwp1=np.zeros((iwpmax+1, 2),  dtype=np.int64)
    rwp2 = np.zeros((iwpmax + 1,2),  dtype=np.int64)

    for k in range(len(i_whole_profile1)):
        if rwp1[sortwp1[k][0]][1]==0:
                rwp1[sortwp1[k][0]][0]=k
        rwp1[sortwp1[k][0]][1] +=1
    for k in range(len(i_whole_profile2)):
        if rwp2[sortwp2[k][0]][1]==0:
                rwp2[sortwp2[k][0]][0]=k
        rwp2[sortwp2[k][0]][1] +=1
    return iwpmax,sortwp1,sortwp2,iwholedone,rwp1,rwp2




def hrr(hrr_description, progress_value, q=[], print_cmd=False, project_properties={}):
    paramlimdist0=0.005 #parameter at this distance we consider that a point belongs to the segment of a triangle
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    # progress
    progress_value.value = 10

    # # TODO en cas d'erreur
    # print("Error: All selected units or timestep are under " +
    #       project_properties['min_height_hyd'] + " water minimum value.")
    # # warnings
    # if not print_cmd:
    #     sys.stdout = sys.__stdout__
    #     if q:
    #         q.put(mystdout)
    #         sleep(0.1)  # to wait q.put() ..
    # return
    #


    # TODO: change it with Quentin deltat seconds
    # deltatlist = hrr_description["deltatlist"]
    deltatlist = [0,24017] #T2b1-b3 deltat en s pour Qi : 9.2   35
    # deltatlist = [0,13947,10070,7724,11058,10198,10549,5961,16689]  #T2 deltat en s pour Qi : 9.2	21.2	35	48.4	74.7	110	150	175	259
    # deltatlist = [0,11557,9743,4037,4816,9938,9305,5485,15104]   # T345-OLD deltat en s pour Qi : 9.2	25.5	48.4	60	76	110	150	175	259
    # deltatlist = [0,13183,11686,4800,5673,11622,10497,6209,16756]  # T345-2022deltat en s pour Qi : 9.2	25.5	48.4	60	76	110	150	175	259
    input_filename_1 = hrr_description["hdf5_name"]
    path_prj = project_properties["path_prj"]

    # load file
    hdf5_1 = Hdf5Management(path_prj, input_filename_1, new=False, edit=False)
    # Todo check only one wholeprofile
    #Todo rajouter datamesh dans le cas d'un volume fini
    hdf5_1.load_hdf5(whole_profil=True)
    unit_list = [["temp"] * (hdf5_1.data_2d[0].unit_number - 1)]  # TODO: multi reach not done
    new_data_2d = Data2d(reach_number=hdf5_1.data_2d.reach_number,
                         unit_list=unit_list)  # new
    #prepare log
    hrr_logfile_name= os.path.join(path_prj,'output','text',hdf5_1.filename[:-4] + "_HRR.log")
    hrr_logfile=''
    hrr_txtfile_name= os.path.join(path_prj,'output','text',hdf5_1.filename[:-4] + "_HRR.txt")
    hrr_txtfile=''

    # get attr
    new_data_2d.__dict__.update(hdf5_1.data_2d.__dict__)  # copy all attr
    # loop
    for reach_number in range(hdf5_1.data_2d.reach_number):

        # progress
        delta_reach = 90 / new_data_2d.reach_number

        xy_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["node"]["xy"]
        z_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["node"]["z"]
        tin_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["mesh"]["tin"]
        locawp, countcontactwp = connectivity_mesh_table(tin_whole_profile)
        countcontactwp = countcontactwp.flatten()
        lenwhole=len(countcontactwp)

        #data adjustment for whole profile
        hdf5_1.data_2d_whole[reach_number][0]["mesh"]["data"] = pd.DataFrame()
        hdf5_1.data_2d_whole[reach_number][0]["node"]["data"]=pd.DataFrame(hdf5_1.data_2d_whole[reach_number][0]["node"]["z"],columns=["z"])
        #calculation of max_slope_bottom for the whole profile
        hdf5_1.data_2d_whole[reach_number][0].c_mesh_max_slope_bottom()
        max_slope_bottom_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["mesh"]["data"][
            hdf5_1.data_2d_whole.hvum.max_slope_bottom.name].to_numpy()
        unit_counter_3 = -1
        for unit_number in range(len(hdf5_1.data_2d[0])-1,0,-1): #Todo transitoire

            # progress
            delta_unit = delta_reach / len(range(len(hdf5_1.data_2d[0])-1,0,-1))

            unit_counter_3 += 1
            # Todo et recuperer temps depuis deltatlist + VERIFIER valeur locale non nulle
            deltat=deltatlist[unit_number]

            q1 = hdf5_1.data_2d[reach_number][unit_number].unit_name #q1>q2
            q2 = hdf5_1.data_2d[reach_number][unit_number-1].unit_name  # q2<q1
            #Todo check that the discharge are increasing time step hydropeaking the flow is increasing or decreasing  TXT file must indicate time interval and the way the information is sorted
            tin1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"]
            tin2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["tin"]
            datamesh1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]  # TODO: pandas_array.iloc
            hdf5_1.data_2d[reach_number][unit_number].c_mesh_mean_from_node_values('h')
            hmoy1=hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]['h'].to_numpy()
            hdf5_1.data_2d[reach_number][unit_number].c_mesh_mean_from_node_values('z')
            zsurf1 =hmoy1+ hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]['z'].to_numpy()
            hdf5_1.data_2d[reach_number][unit_number-1].c_mesh_mean_from_node_values('h')
            hmoy2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["data"]['h'].to_numpy()
            hdf5_1.data_2d[reach_number][unit_number-1].c_mesh_mean_from_node_values('z')
            zsurf2 =hmoy2+ hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["data"]['z'].to_numpy()
            i_split1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["i_split"]
            i_split2 = hdf5_1.data_2d[reach_number][unit_number - 1]["mesh"]["data"]["i_split"]
            xy1 = hdf5_1.data_2d[reach_number][unit_number]["node"]["xy"]
            xy2 = hdf5_1.data_2d[reach_number][unit_number-1]["node"]["xy"]
            h1 = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"]["h"].to_numpy()
            h2 = hdf5_1.data_2d[reach_number][unit_number-1]["node"]["data"]["h"].to_numpy()
            z1 = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"]["z"].to_numpy()
            z2 = hdf5_1.data_2d[reach_number][unit_number-1]["node"]["data"]["z"].to_numpy()
            # Todo ask Quentin
            area1 = 0.5 * (np.abs(
                (xy1[tin1[:, 1]][:, 0] - xy1[tin1[:, 0]][:, 0]) * (
                        xy1[tin1[:, 2]][:, 1] - xy1[tin1[:, 0]][:, 1]) - (
                        xy1[tin1[:, 2]][:, 0] - xy1[tin1[:, 0]][:, 0]) * (
                        xy1[tin1[:, 1]][:, 1] - xy1[tin1[:, 0]][:, 1])))
            # TODO: pandas data can have several dtype
            datanode1=hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].to_numpy()
            datanode2 = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].to_numpy()


            i_whole_profile1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
            i_whole_profile2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["i_whole_profile"]
            iwpmax,sortwp1, sortwp2, iwholedone, rwp1, rwp2=analyse_whole_profile(i_whole_profile1, i_whole_profile2)
            # np array 1 if wether a mesh of tin1 or tin2 is at least partially wet
            rwp12 = np.zeros((lenwhole), dtype=np.int64) #lenwhole !!
            for wpk in range(iwpmax+1):
                if rwp1[wpk][1] != 0 or rwp2[wpk][1] != 0:
                    rwp12[wpk] = 1
            imeshpt3=0
            tin3 = []
            datamesh3=[]
            i_whole_profile3 = []
            i_split3 = []
            max_slope_bottom3=[]
            deltaz3=[]
            xy3=[]
            datanode3=[]
            deltaz12wp = np.full((iwpmax+1,), -1,
                                 dtype=np.float64)  # to store for whole profile mesh only wetted at Q1 the closest deltaz


            xyzh=np.zeros((10,4), dtype=np.float64)
            ixyzh=np.zeros((10), dtype=np.int64)
            axyzh=np.zeros((10,4), dtype=np.float64)
            aixyzh=np.zeros((10), dtype=np.int64)
            lambda6,lambda7,lambda8,lambda9=0,0,0,0
            anodelist,anodelist2=[],[]
            iwholexy = np.zeros((3, 2), dtype=np.float64)


            def compute_delta_zmean():
                iwhole_entirely_wetted_q1_q2=np.full((iwpmax + 1), False)
                deltaz_mean = 0
                total_area_wp_both = 0
                for iiwp in range(iwpmax + 1):
                    if rwp1[iiwp, 1] == 1 and rwp2[iiwp, 1] == 1:
                        i1 = sortwp1[rwp1[iiwp][ 0]][1]
                        i2 = sortwp2[rwp2[iiwp][ 0]][1]
                        if i_split1[i1] == 0 and i_split2[i2] == 0:
                            iwhole_entirely_wetted_q1_q2[iiwp] = True
                            total_area_wp_both += area1[i1]
                            deltaz_mean += area1[i1] * (zsurf1[i1] - zsurf2[i2])
                            deltaz12wp[iiwp] = zsurf1[i1] - zsurf2[i2]
                if total_area_wp_both !=0:
                    deltaz_mean=deltaz_mean/total_area_wp_both
                else:
                    deltaz_mean=np.nan
                return iwhole_entirely_wetted_q1_q2, deltaz_mean
            def getxyiwhole():
                for  k in range(3):
                    iwholexy[k]=np.array(xy_whole_profile[tin_whole_profile[iwp,k]])
            def getxyzhi(kk,decal1):
                for k in range(3):
                    xyzh[k+decal1,0:2]=np.array(xy1[tin1[i11][k]])
                    xyzh[k+decal1,2] = np.array(h1[tin1[i11][k]])
                    xyzh[k+decal1,3] = np.array(z1[tin1[i11][k]])
                    ixyzh[k+decal1] = np.array(tin1[i11][k])
                    xyzh[kk+k,0:2]=np.array(xy2[tin2[i21][k]])
                    xyzh[kk+k,2] = np.array(h2[tin2[i21][k]])
                    xyzh[kk+k,3] = np.array(z2[tin2[i21][k]])
                    ixyzh[kk + k] = np.array(tin2[i21][k])
                return
            def getxyzhi_q1():
                for k in range(3):
                    bfound=False
                    for ki in range(1,4):
                        if (np.array(xy1[tin1[i12][k]])==xyzh[ki,0:2]).all():
                            bfound=True
                    if not bfound:
                        xyzh[4,0:2]=np.array(xy1[tin1[i12][k]])
                        xyzh[4,2] = np.array(h1[tin1[i12][k]])
                        xyzh[4,3] = np.array(z1[tin1[i12][k]])
                        ixyzh[4] = np.array(tin1[i12][k])
                        return True
                return False
            def getxyzhi_q2():
                for k in range(3):
                    bfound = False
                    for ki in range(6,9):
                        if (np.array(xy2[tin2[i22][k]])==xyzh[ki,0:2]).all():
                            bfound = True
                    if not bfound:
                        xyzh[9,0:2]=np.array(xy2[tin2[i22][k]])
                        xyzh[9,2] = np.array(h2[tin2[i22][k]])
                        xyzh[9,3] = np.array(z2[tin2[i22][k]])
                        ixyzh[9] = np.array(tin2[i22][k])
                        return True
                return False
            def getxyzhi_q2b():
                for k in range(3):
                    bfound = False
                    for ki in range(5,8):
                        if (np.array(xy2[tin2[i22][k]])==xyzh[ki,0:2]).all():
                            bfound = True
                    if not bfound:
                        xyzh[8,0:2]=np.array(xy2[tin2[i22][k]])
                        xyzh[8,2] = np.array(h2[tin2[i22][k]])
                        xyzh[8,3] = np.array(z2[tin2[i22][k]])
                        ixyzh[8] = np.array(tin2[i22][k])
                        return True
                return False
            def affecta(ka,kb):
                axyzh[ka, :] = xyzh[kb, :]
                aixyzh[ka] = ixyzh[kb]
            def passa(k1,k2):
                lrot=[[0,1,2],[1,2,0],[2,0,1]]
                for k in range(3):
                    axyzh[k,:] = xyzh[lrot[k1][k],:]
                    aixyzh[k] = ixyzh[lrot[k1][k]]
                    axyzh[5+k, :] = xyzh[lrot[k2][k]+5,:]
                    aixyzh[5 + k] = ixyzh[lrot[k2][k] + 5]
            def passatq(l1,l2):
                kk1=1
                for k in range(3):
                    if k in l1:
                        axyzh[kk1,:] = xyzh[k,:]
                        aixyzh[kk1] = ixyzh[k]
                        kk1+=1
                    else:
                        axyzh[0,:] = xyzh[k,:]
                        aixyzh[0] = ixyzh[k]
                kk1,kk2 = 6,8
                for k in range(6,10):
                    if k in l2:
                        axyzh[kk1,:] = xyzh[k,:]
                        aixyzh[kk1] = ixyzh[k]
                        kk1+=1
                    else:
                        axyzh[kk2,:] = xyzh[k,:]
                        aixyzh[kk2] = ixyzh[k]
                        kk2 += 1
            def store_mesh_tin1(k,imeshpt3):
                i_whole_profile3.append(iwp)
                max_slope_bottom3.append(max_slope_bottom_whole_profile[iwp])
                deltaz3.append(deltaz3_)
                i_split3.append(
                    0)  # even in the case of isplit1=1 ie cut2D have left a triangle part of the mesh that was partially wetted
                if len(anodelist)==0:
                    for i3 in range(3):
                        xy3.append(xy1[tin1[sortwp1[rwp1[iwp][0] + k][1]][i3]])
                        datanode3.append(datanode1[tin1[sortwp1[rwp1[iwp][0] + k][1]][i3]])
                else:
                    for l3 in anodelist:
                        if len(l3)==1:
                            xy3.append(xy1[aixyzh[l3[0]]])
                            datanode3.append(datanode1[aixyzh[l3[0]]])
                        else: #(2 index for a and one lambda0)
                            xy3.append(l3[2]*(axyzh[l3[1],0:2]-axyzh[l3[0],0:2])+axyzh[l3[0],0:2])
                            datanode3.append(l3[2]*(datanode1[aixyzh[l3[1]]]-datanode1[aixyzh[l3[0]]])+datanode1[aixyzh[l3[0]]])
                tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 2])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0] + k][1]])
                iwholedone[iwp] = 1
            def store_2mesh_tin1(imeshpt3,busual=True):
                for k in range(2):
                    i_whole_profile3.append(iwp)
                    max_slope_bottom3.append(max_slope_bottom_whole_profile[iwp])
                    deltaz3.append(deltaz3_)
                    i_split3.append(
                        0)  # even in the case of isplit1=1 ie cut2D have left a triangle part of the mesh that was partially wetted
                for l3 in anodelist2:
                    if len(l3)==2:
                        for k in range(2):
                            xy3.append(xy1[aixyzh[l3[k]]])
                            datanode3.append(datanode1[aixyzh[l3[k]]])
                    else: #(2 index for a and one lambda0)
                        xy3.append(l3[2]*(axyzh[l3[1],0:2]-axyzh[l3[0],0:2])+axyzh[l3[0],0:2])
                        datanode3.append(l3[2]*(datanode1[aixyzh[l3[1]]]-datanode1[aixyzh[l3[0]]])+datanode1[aixyzh[l3[0]]])
                if busual:
                    tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 3])
                else:
                    tin3.append([imeshpt3, imeshpt3 + 2, imeshpt3 + 1])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                tin3.append([imeshpt3+1, imeshpt3 + 2, imeshpt3 + 3])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                iwholedone[iwp] = 1
            def store_3mesh_tin1(imeshpt3):
                for kk in range(3):
                    i_whole_profile3.append(iwp)
                    max_slope_bottom3.append(max_slope_bottom_whole_profile[iwp])
                    deltaz3.append(deltaz3_)
                    i_split3.append(
                        0)  # even in the case of isplit1=1 ie cut2D have left a triangle part of the mesh that was partially wetted
                for kk in range(3):
                    xy3.append(xy1[aixyzh[anodelist3[0][kk]]])
                    datanode3.append(datanode1[aixyzh[anodelist3[0][kk]]])
                for kk in range(1,3):
                    l3=anodelist3[kk]
                    xy3.append(l3[2] * (axyzh[l3[1], 0:2] - axyzh[l3[0], 0:2]) + axyzh[l3[0], 0:2])
                    datanode3.append(
                        l3[2] * (datanode1[aixyzh[l3[1]]] - datanode1[aixyzh[l3[0]]]) + datanode1[aixyzh[l3[0]]])
                tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 2])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                tin3.append([imeshpt3, imeshpt3 + 2, imeshpt3 + 3])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                tin3.append([imeshpt3, imeshpt3 + 3, imeshpt3 + 4])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                iwholedone[iwp] = 1
            def calculate_deltaz3(iwp, level1=4, minimum_surrounding_wetted_mesh=5): #iwp, locawp, countcontactwp, sortwp1, sortwp2, rwp1, rwp2, tin1, tin2, zsurf1, zsurf2,level=4, minimum_surrounding_mesh=4

                # for whole profile
                # locawp  the np array of 3 columns for each line/triangle the 3 index of neighbour triangles (-1 if not)
                # countcontact for each line/triangle the number of neighbouring triangles maximum (3)
                # deltaz12wp to store mesh index only wetted at Q1 the closest deltaz -1 if the value has not been founded yet or will never be

                if countcontactwp[iwp] == 0:
                    return np.nan
                if deltaz12wp[iwp] != -1:
                    return deltaz12wp[iwp]
                meshkept = []
                zsurf1kept = []
                zsurf2kept = []
                aa = set(locawp[iwp][:countcontactwp[iwp]])
                a = aa | {iwp}
                level=0
                breakarm=False
                while True: # for ilevel in range(level):
                    b = set()
                    d = []
                    for ij in aa:
                        b = b | set(locawp[ij][:countcontactwp[ij]])
                    for iwpk in b:
                        if iwpk < rwp1.shape[0]:
                            if rwp1[iwpk][1]==0:
                                d.append(iwpk)
                        else:
                            d.append(iwpk)
                    b= b-set(d)
                    aa = b - a
                    for iwpk in aa:
                        # condition for keeping the mesh
                        # if iwpk < rwp2.shape[0] and rwp2[iwpk][1] == 1 and rwp1[iwpk][1] == 1:
                        if iwpk < rwp2.shape[0] and iwhole_entirely_wetted_q1_q2[iwpk]:
                            zsurf1k = zsurf1[sortwp1[rwp1[iwpk][0]][1]]  # zsurf1[tin1[sortwp1[rwp1[iwpk][0]][1]]]
                            zsurf2k = zsurf2[sortwp2[rwp2[iwpk][0]][1]]  # zsurf2[tin2[sortwp2[rwp2[iwpk][0]][1]]]
                            if zsurf2k < zsurf1k:
                                meshkept.append(iwpk)
                                zsurf1kept.append(zsurf1k)
                                zsurf2kept.append(zsurf2k)
                    a = a | b
                    c=np.array(list(aa))
                    if len(c)==0:
                        nb_new_surronding_wet =0
                    else:
                        nb_new_surronding_wet=np.sum(rwp12[c])

                    if nb_new_surronding_wet==0: # case of side arm or puddle isolated and dry at Q2
                        break
                    if len(meshkept) >= minimum_surrounding_wetted_mesh:
                        break
                    level += 1
                    if level>level1: #side arm connected to the main channel but dry at Q2
                        for iwpk in meshkept:
                            if deltaz12wp[iwpk] !=-1:
                                deltaz=deltaz12wp[iwpk]
                                breakarm=True
                                break

                surroundingmesh = list(a - {iwp})


                # Todo moyenne ou autre ???
                if not(breakarm):
                    if len(meshkept) != 0:  # minimum value of local deltaz to cope with hydraulic aberrations
                        index_min2 = min(range(len(zsurf2kept)), key=zsurf2kept.__getitem__)
                        deltaz = zsurf1kept[index_min2] - zsurf2kept[index_min2]
                        deltaz12wp[iwp]=deltaz
                    else:
                        deltaz = deltaz_mean # It's a choice not to use deltaz =  np.nan
                if nb_new_surronding_wet==0 or level>level1:
                    for iwpk in a:
                        if iwpk<=iwpmax:
                            if deltaz12wp[iwpk] == -1 and rwp1[iwpk][1]!=0:
                                deltaz12wp[iwpk]=deltaz

                return deltaz



            # progress bar
            delta_mesh = delta_unit / len(iwholedone)

            iwhole_entirely_wetted_q1_q2, deltaz_mean = compute_delta_zmean()
            for iwp in range(len(iwholedone)):

                # progress
                progress_value.value = progress_value.value + delta_mesh
                if iwholedone[iwp]==0:
                    if rwp1[iwp][1]==0: #  CASE 0a  the tin1 mesh is dryed
                        if rwp2[iwp][1]==0:
                            iwholedone[iwp]=2
                        else: # CASE 0b & 0c
                            iwholedone[iwp] = -1
                    elif rwp1[iwp][1]==1:
                        i11=sortwp1[rwp1[iwp][0]][1]
                        if rwp2[iwp][1]==0: # CASE 1a & 1b the tin1 mesh has been dryed
                            deltaz3_ = calculate_deltaz3(iwp)
                            anodelist=[] #important
                            store_mesh_tin1(0, imeshpt3)
                            imeshpt3 += 3
                            iwholedone[iwp] = 1
                        elif rwp2[iwp][1] ==1:
                            i21=sortwp2[rwp2[iwp][0]][1]
                            if i_split1[i11] == 0 and i_split2[i21] == 1:  # CASE 2a
                                # Todo FACTORISER *************************************************
                                getxyzhi(5,0)
                                bok = False
                                for k1 in range(3):
                                    if bok:
                                        break
                                    for k2 in range(3):
                                        if np.logical_and(xyzh[k1, 0] == xyzh[k2 + 5, 0],
                                                          xyzh[k1][1] == xyzh[k2 + 5, 1]):
                                            bok = True
                                            k1ok, k2ok = k1, k2
                                            break
                                if not (bok):
                                    # Todo faire quelque chose
                                    hrr_logfile += '['+str(reach_number)+',' + q1+'-'+q2 +']\t'+str(iwp)+'\tCASE_2a_1\n'
                                    iwholedone[iwp] = -1
                                    continue
                                else:
                                    passa(k1ok, k2ok)
                                    bok = False
                                    if d0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[7, 0:2]) < paramlimdist0:
                                        if d0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2]) < paramlimdist0:
                                            lambda7 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[7, 0:2])
                                            lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2])
                                            anodelist2 = [[1, 2], [0, 2, lambda7], [0, 1, lambda6]]
                                            bok = True
                                    elif d0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[7, 0:2]) < paramlimdist0:
                                        if d0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2]) < paramlimdist0:
                                            lambda7 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[7, 0:2])
                                            lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2])
                                            anodelist2 = [[1, 2], [0, 2, lambda6], [0, 1, lambda7]]
                                            bok = True
                                    # Todo FIN FACTORISER *************************************************
                                    if not bok:# possible link to paramlimdist0 value
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_2a_2\n'
                                        iwholedone[iwp] = -1
                                        continue
                                    deltaz3_ = calculate_deltaz3(iwp)
                                    store_2mesh_tin1(imeshpt3)
                                    imeshpt3 += 4
                                    iwholedone[iwp] = 1
                            elif i_split1[i11] == 1 and i_split2[i21] == 1:
                                if rwp2[iwp][1] == 2: #CASE 3C
                                    iwholedone[iwp] = -1
                                    continue
                                elif  rwp2[iwp][1] == 1: #CASE 3A & 3B
                                    # Todo FACTORISER *************************************************
                                    getxyzhi(5,0)
                                    bok = False
                                    for k1 in range(3):
                                        if bok:
                                            break
                                        for k2 in range(3):
                                            if np.logical_and(xyzh[k1, 0] == xyzh[k2 + 5, 0],
                                                              xyzh[k1][1] == xyzh[k2 + 5, 1]):
                                                bok = True
                                                k1ok,k2ok=k1,k2
                                                break
                                    if not (bok):
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_2a_3\n'
                                        iwholedone[iwp] = -1
                                        continue
                                    else:
                                        passa(k1ok,k2ok)
                                        bok=False
                                        if d0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[7, 0:2]) < paramlimdist0:
                                            if d0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2]) < paramlimdist0:
                                                lambda7 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[7, 0:2])
                                                lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2])
                                                anodelist2 = [[1, 2], [0, 2, lambda7], [0, 1, lambda6]]
                                                bok=True
                                        elif d0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[7, 0:2]) < paramlimdist0:
                                            if d0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2]) < paramlimdist0:
                                                lambda7 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[7, 0:2])
                                                lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2])
                                                anodelist2 = [[1, 2], [0, 2, lambda6], [0, 1, lambda7]]
                                                bok = True
                                        # Todo FIN FACTORISER *************************************************
                                        if not bok: # possible link to paramlimdist0 value
                                            # Todo faire quelque chose
                                            hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2+']\t'+str(iwp) + '\tCASE_3a_1\n'
                                            iwholedone[iwp] = -1
                                            continue
                                        if lambda7>0 and lambda7<=1 and lambda6>0 and lambda6<=1:
                                            deltaz3_ = calculate_deltaz3(iwp)
                                            store_2mesh_tin1(imeshpt3)
                                            imeshpt3 += 4
                                            iwholedone[iwp] = 1
                            elif i_split1[i11]==0 and i_split2[i21]==0: #CASE 00
                                iwholedone[iwp] = 2
                            else:
                                iwholedone[iwp] = -1
                        elif rwp2[iwp][1] == 2:
                            i21 = sortwp2[rwp2[iwp][0]][1]
                            i22 = sortwp2[rwp2[iwp][0]+1][1]
                            if i_split1[i11] == 0 and i_split2[i21] == 1:  # CASE 2b we assume that the second triangle of tin2 has also isplit=1
                                getxyzhi(6,0) # 0,1,2  6,7,8
                                if not getxyzhi_q2(): # 0,1,2  6,7,8,9
                                    # Todo faire quelque chose
                                    hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_2b_1\n'
                                    iwholedone[iwp] = -1
                                    continue
                                l1,l2=[],[]
                                for k1 in range( 3):
                                    for k2 in range(6,10):
                                        if np.logical_and( xyzh[k1,0]==xyzh[k2,0],  xyzh[k1,1]==xyzh[k2,1]):
                                            l1.append(k1)
                                            l2.append(k2)
                                if len(l1)!=2:
                                    # Todo faire quelque chose
                                    hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_2b_2\n'
                                    iwholedone[iwp] = -1
                                    continue
                                else:
                                    passatq(l1, l2)
                                    bok=False
                                    if d0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[9,0:2])<paramlimdist0:
                                        if d0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[8,0:2])<paramlimdist0:
                                            lambda9=lambda0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[9,0:2])
                                            lambda8 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[8, 0:2])
                                            anodelist = [[0], [0, 2, lambda9], [0, 1, lambda8]]
                                            bok=True
                                    elif d0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[9,0:2])<paramlimdist0:
                                        if d0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[8,0:2])<paramlimdist0:
                                            lambda9=lambda0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[9,0:2])
                                            lambda8 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[8, 0:2])
                                            anodelist = [[0], [0, 2, lambda8], [0, 1, lambda9]]
                                            bok = True
                                    if not bok:# possible link to paramlimdist0 value
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_2b_3\n'
                                        iwholedone[iwp] = -1
                                        continue
                                    deltaz3_ = calculate_deltaz3(iwp)
                                    store_mesh_tin1(0, imeshpt3)
                                    imeshpt3 += 3
                                    iwholedone[iwp] = 1

                    elif rwp1[iwp][1] == 2:
                        i11 = sortwp1[rwp1[iwp][0]][1]
                        i12 = sortwp1[rwp1[iwp][0] + 1][1]
                        if rwp2[iwp][1] == 0:  # CASE 1c the tin1 2 meshes has been dryed
                            deltaz3_ =calculate_deltaz3(iwp)
                            for k in range(2):
                                anodelist=[] # important
                                store_mesh_tin1(k,imeshpt3)
                                imeshpt3 += 3
                                iwholedone[iwp] = 1
                        elif rwp2[iwp][1] == 1 or rwp2[iwp][1] == 2:  # CASE 4a & CASE 4b
                            i21 = sortwp2[rwp2[iwp][0]][1]
                            if i_split1[i11] == 1 and i_split2[i21] == 1:
                                getxyzhi(5, 1)  # 1,2,3  5,6,7
                                if not getxyzhi_q1():  # 1,2,3,4  5,6,7
                                    # Todo faire quelque chose
                                    hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4a_1\n'
                                    iwholedone[iwp] = -1
                                    continue
                                #//////////////////////////////////////////////////////////////
                                getxyiwhole()
                                l4w=[]
                                l4=[]
                                for k in range(3):
                                    for kk in range(1,5):
                                        if (iwholexy[k]==xyzh[kk,0:2]).all():
                                            l4w.append(k)
                                            l4.append(kk)
                                if len(l4w) !=2:
                                    # Todo faire quelque chose
                                    hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4a_or_CASE_4b-1\n'
                                    iwholedone[iwp] = -1
                                    continue
                                #rotation of copy of whole profile mesh : numbering the node a fix way
                                if l4w != [1, 2]:
                                    if l4w==[0,1]:
                                        iwholexy[[0, 2]] = iwholexy[[2, 0]]
                                    if l4w == [0, 2]:
                                        iwholexy[[0, 1]] = iwholexy[[1, 0]]
                                    iwholexy[[1, 2]] = iwholexy[[2, 1]]
                                if l4w == [0, 2]:
                                    affecta(1, l4[1])
                                    affecta(2, l4[0])
                                else:
                                    affecta(1, l4[0])
                                    affecta(2, l4[1])

                                l34=list(set([1,2,3,4])-set(l4))
                                bok=False
                                if d0segment(iwholexy[0],iwholexy[2],xyzh[l34[0],0:2]) < paramlimdist0:
                                    if d0segment(iwholexy[0],iwholexy[1],xyzh[l34[1],0:2]) < paramlimdist0:
                                        affecta(4, l34[0])
                                        affecta(3, l34[1])
                                        bok=True
                                elif d0segment(iwholexy[0],iwholexy[2],xyzh[l34[1],0:2]) < paramlimdist0:
                                    if d0segment(iwholexy[0],iwholexy[1],xyzh[l34[0],0:2]) < paramlimdist0:
                                        affecta(4, l34[1])
                                        affecta(3, l34[0])
                                        bok = True
                                if not bok:
                                    # Todo faire quelque chose
                                    hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4a_or_CASE_4b-2\n'
                                    iwholedone[iwp] = -1
                                    continue
                                # //////////////////////////////////////////////////////////////
                                if rwp2[iwp][1] == 1:

                                    # a ce stade a1234 on place 5,6,7
                                    bok = False
                                    p=[[1,2,3],[2,4,1]]
                                    pp=[[2,4,3],[4,3,1]]
                                    for k in range(5,8):
                                        if bok:
                                            break
                                        for ip in range(2):
                                            if (axyzh[p[ip][0],0:2]==xyzh[k,0:2]).all():
                                                affecta(5, k)
                                                l67 = list(set([5, 6, 7]) - set([k]))
                                                bbok=False
                                                if d0segment(axyzh[p[ip][0],0:2], axyzh[p[ip][2],0:2], xyzh[l67[0], 0:2]) < paramlimdist0:
                                                    if d0segment(axyzh[p[ip][0],0:2], axyzh[p[ip][1],0:2], xyzh[l67[1], 0:2]) < paramlimdist0:
                                                        affecta(7, l67[0])
                                                        affecta(6, l67[1])
                                                        bbok=True
                                                elif d0segment(axyzh[p[ip][0],0:2], axyzh[p[ip][2],0:2], xyzh[l67[1], 0:2]) < paramlimdist0:
                                                    if d0segment(axyzh[p[ip][0],0:2], axyzh[p[ip][1],0:2], xyzh[l67[0], 0:2]) < paramlimdist0:
                                                        affecta(7, l67[1])
                                                        affecta(6, l67[0])
                                                        bbok = True
                                                if bbok:
                                                    lambda7 = lambda0segment(axyzh[p[ip][0], 0:2], axyzh[p[ip][2], 0:2], axyzh[7, 0:2])
                                                    lambda6 = lambda0segment(axyzh[p[ip][0], 0:2], axyzh[p[ip][1], 0:2], axyzh[6, 0:2])
                                                    if (lambda7>0 and lambda7<1) and (lambda6>0 and lambda6<1):
                                                        bok=True
                                                        anodelist3 = [pp[ip], [p[ip][0], p[ip][2], lambda7], [p[ip][0], p[ip][1], lambda6]]
                                                        deltaz3_ = calculate_deltaz3(iwp)
                                                        store_3mesh_tin1(imeshpt3)
                                                        imeshpt3 += 5
                                                        iwholedone[iwp] = 1
                                                        break
                                    if not bok:
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4a_2\n'
                                        iwholedone[iwp] = -1
                                        continue
                                elif rwp2[iwp][1] == 2:  # CASE 4b
                                    i22 = sortwp2[rwp2[iwp][0] + 1][1]
                                    # a ce stade a1234 on place 5,6,7,8
                                    if not getxyzhi_q2b():  # 1,2,3,4  5,6,7,8
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4b_1\n'
                                        iwholedone[iwp] = -1
                                        continue
                                    l56=[]
                                    for k in range(5,9):
                                        if (axyzh[1,0:2]==xyzh[k,0:2]).all() or (axyzh[2,0:2]==xyzh[k,0:2]).all():
                                            l56.append(k)
                                    if len(l56)!=2:
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4b_2\n'
                                        iwholedone[iwp] = -1
                                        continue
                                    l34 = list(set([5, 6, 7, 8]) - set(l56)) # Todo renommmer ici l78
                                    bbok = False

                                    if d0segment(axyzh[1, 0:2], axyzh[3, 0:2],
                                                 xyzh[l34[0], 0:2]) < paramlimdist0:
                                        if d0segment(axyzh[2, 0:2], axyzh[4, 0:2],
                                                     xyzh[l34[1], 0:2]) < paramlimdist0:
                                            affecta(7, l34[0])
                                            affecta(8, l34[1])
                                            bbok = True
                                    elif d0segment(axyzh[1, 0:2], axyzh[3, 0:2],
                                                   xyzh[l34[1], 0:2]) < paramlimdist0:
                                        if d0segment(axyzh[2, 0:2], axyzh[4, 0:2],
                                                     xyzh[l34[0], 0:2]) < paramlimdist0:
                                            affecta(7, l34[1])
                                            affecta(8, l34[0])
                                            bbok = True
                                    if bbok:
                                        lambda7 = lambda0segment(axyzh[1, 0:2], axyzh[3, 0:2],
                                                                 axyzh[7, 0:2])
                                        lambda8 = lambda0segment(axyzh[2, 0:2], axyzh[4, 0:2],
                                                                 axyzh[8, 0:2])
                                        if (lambda7 > 0 and lambda7 < 1) and (lambda8 > 0 and lambda8 < 1):
                                            bok = True
                                            anodelist2 = [[3,4], [1, 3, lambda7],
                                                          [2, 4, lambda8]]
                                            deltaz3_ = calculate_deltaz3(iwp)
                                            store_2mesh_tin1(imeshpt3, False)
                                            imeshpt3 += 4
                                            iwholedone[iwp] = 1
                                    if not bok: # possible link to paramlimdist0 value
                                        # Todo faire quelque chose
                                        hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4b_3\n'
                                        iwholedone[iwp] = -1
                                        continue
                            else:
                                # Todo faire quelque chose
                                hrr_logfile += '['+str(reach_number)+',' +q1+'-'+q2 +']\t'+str(iwp) + '\tCASE_4a_or_CASE_4b-3\n'
                                iwholedone[iwp] = -1
                                continue
                    else: # unknown domain
                                iwholedone[iwp] = 2

            tin3 = np.array(tin3)
            i_whole_profile3 = np.array(i_whole_profile3)
            i_split3 = np.array(i_split3)
            max_slope_bottom3=np.array(max_slope_bottom3)
            deltaz3=np.array(deltaz3)
            with np.errstate(divide='ignore'): # disable zero division warnings we can get infinite values
                hrr3=np.divide(deltaz3,max_slope_bottom3)/(deltat/3600) #unit="m/h"
                # Todo change the values of hrr3 in order to get a constant scale for matplotlib and to cope with infinite values
                # Todo , better do it in Habby/matplotlib !!!!
                hrr3[hrr3 > 4] = 4


            vrr3=deltaz3/(deltat/3600) #unit="m/h"
            xy3=np.array(xy3)
            datanode3=np.array(datanode3)
            #TODO verifier datamesh3
            datamesh3 = np.array(datamesh3)
            # ExportTextHRR
            # Todo ask Quentin
            area3 = 0.5 * (np.abs(
                (xy3[tin3[:, 1]][:, 0] - xy3[tin3[:, 0]][:, 0]) * (
                        xy3[tin3[:, 2]][:, 1] - xy3[tin3[:, 0]][:, 1]) - (
                        xy3[tin3[:, 2]][:, 0] - xy3[tin3[:, 0]][:, 0]) * (
                        xy3[tin3[:, 1]][:, 1] - xy3[tin3[:, 0]][:, 1])))
            max_slope_bottom3_mean=np.sum(max_slope_bottom3*area3)/np.sum(area3)
            vrr3_mean =deltaz_mean/deltat
            if max_slope_bottom3_mean!=0:
                deltab3_mean=deltaz_mean/max_slope_bottom3_mean
                hrr3_mean =vrr3_mean/max_slope_bottom3_mean
            else:
                deltab3_mean,hrr3_mean =0,0
            #'q1-q2\tdeltat\tmaxslopeBottom_mean\tdeltazsurf_mean\tdeltab3_mean\tVRR_MEAN\tHRR_MEAN\n'
            #'[m3/s]\t[s]\t[%]\t[m]\t[m]\t[cm/h]\t[cm/h]\n'
            hrr_txtfile += q1+'-' + q2+'\t'+str(deltat)+'\t'+str(max_slope_bottom3_mean*100)+'\t'+str(deltaz_mean)+'\t'+str(deltab3_mean)+'\t'+str(vrr3_mean*3600*100)+'\t'+str(hrr3_mean*3600*100)+'\n'


            #remove_duplicate_points
            xy3b, indices3, indices2 = np.unique(xy3, axis=0, return_index=True, return_inverse=True)
            if len(xy3b)<len(xy3):
                tin3= indices2[tin3]
                datanode3= datanode3[indices3]

            unit_list[reach_number][unit_counter_3] = q1+'-'+q2
            new_data_2d[reach_number][unit_counter_3].unit_name = q1+'-'+q2
            new_data_2d[reach_number][unit_counter_3]["mesh"]["tin"] = tin3
            # TODO: verifier datamesh3 (à l'origine iwhole,isplikt et peut être des choses en volume fini) il faut refaire un pandas data mesh with pandas_array.iloc
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"] = pd.DataFrame(datamesh3, columns=hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"].columns)
            new_data_2d[reach_number][unit_counter_3]["mesh"]["i_whole_profile"] = i_whole_profile3
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"]["i_split"] = i_split3
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"]["max_slope_bottom"] = max_slope_bottom3
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"]["delta_level"] = deltaz3
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"]["hrr"] = hrr3
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"]["vrr"] = vrr3
            new_data_2d[reach_number][unit_counter_3]["node"]["xy"] = xy3b
            new_data_2d[reach_number][unit_counter_3]["node"]["data"] = pd.DataFrame(datanode3, columns=hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].columns)

    # hvum copy
    new_data_2d.hvum = hdf5_1.data_2d.hvum
    # delta_level
    new_data_2d.hvum.delta_level.position = "mesh"
    new_data_2d.hvum.delta_level.hdf5 = True
    new_data_2d.hvum.hdf5_and_computable_list.append(new_data_2d.hvum.delta_level)
    # hrr
    new_data_2d.hvum.hrr.position = "mesh"
    new_data_2d.hvum.hrr.hdf5 = True
    new_data_2d.hvum.hdf5_and_computable_list.append(new_data_2d.hvum.hrr)
    # vrr
    new_data_2d.hvum.vrr.position = "mesh"
    new_data_2d.hvum.vrr.hdf5 = True
    new_data_2d.hvum.hdf5_and_computable_list.append(new_data_2d.hvum.vrr)


    # compute area  # TODO: get original areas
    new_data_2d.compute_variables([new_data_2d.hvum.area])
    # get_dimension
    new_data_2d.get_dimension()
    # export new hdf5
    hdf5 = Hdf5Management(path_prj, hdf5_1.filename[:-4] + "_HRR" + hdf5_1.extension, new=True)
    # HYD
    new_data_2d.unit_list = unit_list  # update
    # new_data_2d.path_filename_source = hdf5_1.data_2d.path_filename_source
    # new_data_2d.hyd_unit_correspondence = hdf5_1.data_2d.hyd_unit_correspondence
    # new_data_2d.hyd_model_type = hdf5_1.data_2d.hyd_model_type
    hdf5.create_hdf5_hyd(new_data_2d,
                         hdf5_1.data_2d_whole,
                         project_properties)
    #log in output txt
    if len(hrr_logfile) !=0:
        with open(hrr_logfile_name, "w") as f:
            f.write('[reach_number,q1-q2]\t'+'i_whole_profile' + '\tHRR_CASE\n')
            f.write(hrr_logfile)
    # hrr_txtfile
    if len(hrr_txtfile) !=0:
        with open(hrr_txtfile_name, "w") as f:
            f.write('q1-q2\tdeltat\tmaxslopeBottom_mean\tdeltazsurf_mean\tdeltab3_mean\tVRR_MEAN[m/h]\tHRR_MEAN[m/h]\n')
            f.write('[m3/s]\t[s]\t[%]\t[m]\t[m]\t[cm/h]\t[cm/h]\n')
            f.write(hrr_txtfile)

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0

def lambda0segment(xya,xyb,xym):
    dab=np.sum((xya-xyb)**2)
    if dab==0:
        lambda0 = np.nan
    else:
        lambda0=np.sum((xym-xya)*(xyb-xya))/dab
    return lambda0
def d0segment(xya,xyb,xym):
    u=xyb[1]-xya[1]
    v=xya[0]-xyb[0]
    w=xya[1]*xyb[0]-xya[0]*xyb[1]
    norm=np.sqrt(u**2+v**2)
    if norm==0:
        return np.nan
    else:
        return np.abs(u*xym[0]+v*xym[1]+w)/norm

if __name__ == '__main__':
    # set working directory to "C:\habby_dev\habby"
    # path_prj = r"C:\Users\Quent\Documents\HABBY_projects\DefaultProj" # C:\Users\yann.lecoarer\Documents\HABBY_projects\DefaultProj
    path_prj = r"C:\Users\yann.lecoarer\Documents\HABBY_projects\DefaultProj"
    project_properties = load_project_properties(path_prj)
    hrr_description_dict = dict(deltatlist=[0, 3.6 * 3600, 2.5 * 3600, 1.8 * 3600],
                           hdf5_name="d1_d2_d3_d4.hyd")
    # class MyProcess
    progress_value = Value("d", 0.0)
    q = Queue()
    hrr(hrr_description_dict,
               progress_value,
               q,
               print_cmd=True,
               project_properties=project_properties)

    # xy = hdf5_1.data_2d[reach_number][unit_number]["node"]["xy"]
    # z_fond_node = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"]["z"]
    # h_node = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"]["h"]
    # h_mesh = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["h"]
    # i_whole_profile = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
    # i_split = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["i_split"]
    #
    # # get tin first reach first unit whole_profile
    # xy_whole_profile = hdf5_1.data_2d_whole[reach_number][unit_number]["node"]["xy"]
    # tin_whole_profile = hdf5_1.data_2d_whole[reach_number][unit_number]["mesh"]["tin"]

