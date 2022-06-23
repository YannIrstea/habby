import sys
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
    paramlimdist0=0.001 #parameter at this distance we consider that a point belongs to the segment of a triangle
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    # progress
    progress_value.value = 10

    # deltatlist = hrr_description["deltatlist"]
    deltatlist = [0,3.6*3600,2.5*3600,1.8*3600]  # TODO: change it
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
            # Todo et recuperer temps depuis deltatlist
            deltat=deltatlist[unit_number]

            q1=hdf5_1.data_2d[reach_number][unit_number].unit_name #q1>q2
            q2 = hdf5_1.data_2d[reach_number][unit_number-1].unit_name  # q2<q1
            #Todo check that the discharge are increasing time step hydropeaking the flow is increasing or decreasing  TXT file must indicate time interval and the way the information is sorted
            tin1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"]
            tin2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["tin"]
            datamesh1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]  # TODO: pandas_array.iloc
            # locawp, countcontactwp = connectivity_mesh_table(tin1)
            # loca1, countcontact1=connectivity_mesh_table(tin1)
            # loca2, countcontact2 = connectivity_mesh_table(tin2)
            # countcontact1 = countcontact1.flatten()
            # countcontact2 = countcontact2.flatten()

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

            def getxyzhi(kk):

                for k in range(3):
                    xyzh[k,0:2]=np.array(xy1[tin1[i11][k]])
                    xyzh[k,2] = np.array(h1[tin1[i11][k]])
                    xyzh[k,3] = np.array(z1[tin1[i11][k]])
                    ixyzh[k] = np.array(tin1[i11][k])
                    xyzh[kk+k,0:2]=np.array(xy2[tin2[i21][k]])
                    xyzh[kk+k,2] = np.array(h2[tin2[i21][k]])
                    xyzh[kk+k,3] = np.array(z2[tin2[i21][k]])
                    ixyzh[kk + k] = np.array(tin2[i21][k])
                return
            def getxyzhi_q2():
                for k in range(3):
                    for ki in range(6,9):
                        if not((np.array(xy2[tin2[i22][k]])==xyzh[ki,0:2]).all()):
                            xyzh[9,0:2]=np.array(xy2[tin2[i22][k]])
                            xyzh[9,2] = np.array(h2[tin2[i22][k]])
                            xyzh[9,3] = np.array(z2[tin2[i22][k]])
                            ixyzh[9] = np.array(tin2[i22][k])
                return

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

            def store_2mesh_tin1(imeshpt3):
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
                tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 3])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                tin3.append([imeshpt3+1, imeshpt3 + 2, imeshpt3 + 3])
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0]][1]])
                iwholedone[iwp] = 1




            def calculate_deltaz3(iwp, level1=4, minimum_surrounding_wetted_mesh=5): #iwp, locawp, countcontactwp, sortwp1, sortwp2, rwp1, rwp2, tin1, tin2, zsurf1, zsurf2,level=4, minimum_surrounding_mesh=4
                if countcontactwp[iwp] == 0:
                    return np.nan
                if deltaz12wp[iwp] != -1:
                    return deltaz12wp[iwp]
                meshkept = []
                zsurf1kept = []
                zsurf2kept = []
                a = set(locawp[iwp][:countcontactwp[iwp]]) | {iwp}
                aa = set(locawp[iwp][:countcontactwp[iwp]])
                level=0
                breakarm=False
                while True: # for ilevel in range(level):
                    b = set()
                    for ij in aa:
                        b = b | set(locawp[ij][:countcontactwp[ij]])
                    aa = b - a
                    for iwpk in aa:
                        # condition for keeping the mesh
                        if iwpk < rwp2.shape[0] and rwp2[iwpk][1] == 1 and rwp1[iwpk][1] == 1:
                            zsurf1k = zsurf1[sortwp1[rwp1[iwpk][0]][1]]  # zsurf1[tin1[sortwp1[rwp1[iwpk][0]][1]]]
                            zsurf2k = zsurf2[sortwp2[rwp2[iwpk][0]][1]]  # zsurf2[tin2[sortwp2[rwp2[iwpk][0]][1]]]
                            if zsurf2k < zsurf1k:
                                meshkept.append(iwpk)
                                zsurf1kept.append(zsurf1k)
                                zsurf2kept.append(zsurf2k)
                    a = a | b
                    c=np.array(list(aa))
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
                    else:
                        deltaz =  np.nan
                if nb_new_surronding_wet==0 or level>level1:
                    for iwpk in a:
                        if iwpk<=iwpmax:
                            deltaz12wp[iwpk]=deltaz

                return deltaz



            # progress bar
            delta_mesh = delta_unit / len(iwholedone)

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
                                #Todo FACTORISER *************************************************
                                getxyzhi(5)
                                bok=False
                                for k1 in range( 3):
                                    for k2 in range(3):
                                        if np.logical_and( xyzh[k1,0]==xyzh[k2+5,0],  xyzh[k1][1]==xyzh[k2+5,1]):
                                            bok=True
                                            break
                                if not(bok):
                                    # Todo faire quelque chose
                                    # print("ca va pas CASE 2a")
                                    iwholedone[iwp] = -1
                                    continue
                                else:
                                    passa(k1,k2)
                                    if d0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[7,0:2])<paramlimdist0:
                                        if d0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[6,0:2])<paramlimdist0:
                                            lambda7=lambda0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[7,0:2])
                                            lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2])
                                            anodelist2 = [[1, 2], [0, 2, lambda7], [0, 1, lambda6]]
                                        else:
                                            # Todo faire quelque chose
                                            # print("ca va pas CASE 2a")
                                            iwholedone[iwp] = -1
                                            continue
                                    elif d0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[7,0:2])<paramlimdist0:
                                        if d0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[6,0:2])<paramlimdist0:
                                            lambda7=lambda0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[7,0:2])
                                            lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2])
                                            anodelist2 = [[1, 2], [0, 2, lambda6], [0, 1, lambda7]]
                                        else:
                                            # Todo faire quelque chose
                                            # print("ca va pas CASE 2a")
                                            iwholedone[iwp] = -1
                                            continue
                                    # Todo FIN FACTORISER *************************************************
                                    deltaz3_ = calculate_deltaz3(iwp)
                                    store_2mesh_tin1(imeshpt3)
                                    imeshpt3 += 4
                                    iwholedone[iwp] = 1
                            elif i_split1[i11] == 1 and i_split2[i21] == 1:
                                if rwp2[iwp][1] == 2: #CASE 3C
                                    iwholedone[iwp] = -1
                                elif  rwp2[iwp][1] == 1: #CASE 3A & 3B
                                    titi=4
                                    # # Todo FACTORISER *************************************************
                                    # getxyzhi(5)
                                    # bok = False
                                    # for k1 in range(3):
                                    #     for k2 in range(3):
                                    #         if np.logical_and(xyzh[k1, 0] == xyzh[k2 + 5, 0],
                                    #                           xyzh[k1][1] == xyzh[k2 + 5, 1]):
                                    #             bok = True
                                    #             break
                                    # if not (bok):
                                    #     # Todo faire quelque chose
                                    #     # print("ca va pas CASE 2a")
                                    #     iwholedone[iwp] = -1
                                    #     continue
                                    # else:
                                    #     passa(k1, k2)
                                    #     if d0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[7, 0:2]) < paramlimdist0:
                                    #         if d0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2]) < paramlimdist0:
                                    #             lambda7 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[7, 0:2])
                                    #             lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[6, 0:2])
                                    #             anodelist2 = [[1, 2], [0, 2, lambda7], [0, 1, lambda6]]
                                    #         else:
                                    #             # Todo faire quelque chose
                                    #             # print("ca va pas CASE 2a")
                                    #             iwholedone[iwp] = -1
                                    #             continue
                                    #     elif d0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[7, 0:2]) < paramlimdist0:
                                    #         if d0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2]) < paramlimdist0:
                                    #             lambda7 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[7, 0:2])
                                    #             lambda6 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[6, 0:2])
                                    #             anodelist2 = [[1, 2], [0, 2, lambda6], [0, 1, lambda7]]
                                    #         else:
                                    #             # Todo faire quelque chose
                                    #             # print("ca va pas CASE 2a")
                                    #             iwholedone[iwp] = -1
                                    #             continue
                                    #     # Todo FIN FACTORISER *************************************************
                                    #     if lambda7<=1 and lambda6<=1:
                                    #         deltaz3_ = calculate_deltaz3(iwp)
                                    #         store_2mesh_tin1(imeshpt3)
                                    #         imeshpt3 += 4
                                    #         iwholedone[iwp] = 1
                                    #     else:
                                    #         # Todo faire quelque chose
                                    #         # print("ca va pas CASE 2a")
                                    #         iwholedone[iwp] = -1
                                    #         continue




                            elif i_split1[i11]==0 and i_split2[i21]==0: #CASE 00
                                iwholedone[iwp] = 2
                            else:
                                iwholedone[iwp] = -1
                        elif rwp2[iwp][1] == 2:
                            i21 = sortwp2[rwp2[iwp][0]][1]
                            i22 = sortwp2[rwp2[iwp][0]+1][1]
                            if i_split1[i11] == 0 and i_split2[i21] == 1:  # CASE 2b we assume that the second triangle of tin2 has also isplit=1
                                getxyzhi(6) # 0,1,2  6,7,8
                                getxyzhi_q2() # 0,1,2  6,7,8,9
                                l1,l2=[],[]
                                for k1 in range( 3):
                                    for k2 in range(6,10):
                                        if np.logical_and( xyzh[k1,0]==xyzh[k2,0],  xyzh[k1,1]==xyzh[k2,1]):
                                            l1.append(k1)
                                            l2.append(k2)
                                if len(l1)!=2:
                                    # Todo faire quelque chose
                                    # print("ca va pas CASE 2b")
                                    continue
                                else:
                                    passatq(l1, l2)
                                    if d0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[9,0:2])<paramlimdist0:
                                        if d0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[8,0:2])<paramlimdist0:
                                            lambda9=lambda0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[9,0:2])
                                            lambda8 = lambda0segment(axyzh[0, 0:2], axyzh[1, 0:2], axyzh[8, 0:2])
                                            anodelist = [[0], [0, 2, lambda9], [0, 1, lambda8]]
                                        else:
                                            # Todo faire quelque chose
                                            # print("ca va pas CASE 2b")
                                            continue
                                    elif d0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[9,0:2])<paramlimdist0:
                                        if d0segment(axyzh[0,0:2],axyzh[2,0:2],axyzh[8,0:2])<paramlimdist0:
                                            lambda9=lambda0segment(axyzh[0,0:2],axyzh[1,0:2],axyzh[9,0:2])
                                            lambda8 = lambda0segment(axyzh[0, 0:2], axyzh[2, 0:2], axyzh[8, 0:2])
                                            anodelist = [[0], [0, 2, lambda8], [0, 1, lambda9]]
                                        else:
                                            # Todo faire quelque chose
                                            # print("ca va pas CASE 2b")
                                            continue
                                    deltaz3_ = calculate_deltaz3(iwp)
                                    store_mesh_tin1(0, imeshpt3)
                                    imeshpt3 += 3
                                    iwholedone[iwp] = 1
                    elif rwp1[iwp][1] == 2:
                        if rwp2[iwp][1] == 0:  # CASE 1c the tin1 2 meshes has been dryed
                            deltaz3_ =calculate_deltaz3(iwp)
                            for k in range(2):
                                anodelist=[] # important
                                store_mesh_tin1(k,imeshpt3)
                                imeshpt3 += 3
                                iwholedone[iwp] = 1


                    else: # unknown domain
                                iwholedone[iwp] = 2

            tin3 = np.array(tin3)
            i_whole_profile3 = np.array(i_whole_profile3)
            i_split3 = np.array(i_split3)
            max_slope_bottom3=np.array(max_slope_bottom3)
            deltaz3=np.array(deltaz3)
            with np.errstate(divide='ignore'): # disable zero division warnings
                hrr3=np.divide(deltaz3,max_slope_bottom3)/(deltat*3600)
            xy3=np.array(xy3)
            datanode3=np.array(datanode3)
            #TODO verifier datamesh3
            datamesh3 = np.array(datamesh3)

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
    # titi = 1
