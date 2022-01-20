from src.hdf5_mod import Hdf5Management
import numpy as np
import pandas as pd
from src.manage_grid_mod import connectivity_mesh_table
from src.merge_mod import finite_element_interpolation

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
        rwp1[sortwp2[k][0]][1] +=1
    return sortwp1,sortwp2,iwholedone,rwp1,rwp2

def calculate_deltaz3(iwp,locawp, countcontactwp,sortwp1, sortwp2,  rwp1, rwp2,tin1,tin2,zsurf1,zsurf2,level=4, minimum_surrounding_mesh=4):
    a = set(locawp[iwp][:countcontactwp[iwp]]) | {iwp}
    aa = set(locawp[iwp][:countcontactwp[iwp]])
    for ilevel in range(level):
        b = set()
        for ij in aa:
            b = b | set(locawp[ij][:countcontactwp[ij]])
        aa = b - a
        a = a | b
    surroundingmesh = list(a - {iwp})
    # condition for keeping the mesh
    if len(surroundingmesh)!=0:
        meshkept=[]
        zsurf1kept=[]
        zsurf2kept=[]
        for iwpk in surroundingmesh:
            if iwpk<rwp2.shape[0] and rwp2[iwpk][1]==1 and rwp1[iwpk][1]==1:
                zsurf1k=zsurf1[tin1[sortwp1[rwp1[iwpk][0]][1]]]
                zsurf2k=zsurf2[tin2[sortwp2[rwp2[iwpk][0]][1]]]
                if zsurf2k<zsurf1k:
                    meshkept.append(iwpk)
                    zsurf1kept.append(zsurf1k)
                    zsurf2kept.append(zsurf2k)
        if len(meshkept)!=0:#minimum value of local deltaz to cope with hydraulic aberrations
            index_min2 = min(range(len(zsurf2kept)), key=zsurf2kept.__getitem__)
            deltaz=zsurf1k[index_min2]-zsurf2k[index_min2]
            return deltaz
        else:
            return np.nan
    else:
        return np.nan

def hrr(input_filename_1,deltatlist):
    # load file
    hdf5_1 = Hdf5Management(path_prj, input_filename_1, new=False, edit=False)
    # Todo check only one wholeprofile
    #Todo rajouter datamesh dans le cas d'un volume fini
    hdf5_1.load_hdf5(whole_profil=True)

    hrrlistdic = []


    # loop
    for reach_number in range(hdf5_1.data_2d.reach_number):
        xy_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["node"]["xy"]
        z_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["node"]["z"]
        tin_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["mesh"]["tin"]
        locawp, countcontactwp = connectivity_mesh_table(tin_whole_profile)
        countcontactwp = countcontactwp.flatten()

        #data adjustment for whole profile
        hdf5_1.data_2d_whole[reach_number][0]["mesh"]["data"] = pd.DataFrame()
        hdf5_1.data_2d_whole[reach_number][0]["node"]["data"]=pd.DataFrame(hdf5_1.data_2d_whole[reach_number][0]["node"]["z"],columns=["z"])
        #calculation of max_slope_bottom for the whole profile
        hdf5_1.data_2d_whole[reach_number][0].c_mesh_max_slope_bottom()
        max_slope_bottom_whole_profile = hdf5_1.data_2d_whole[reach_number][0]["mesh"]["data"][
            hdf5_1.data_2d_whole.hvum.max_slope_bottom.name].to_numpy()
        hrrlistdic.append({'unit_name':[],'tin':[],'i_whole_profile':[],'i_split':[],'max_slope_bottom':[],'deltaz':[],'hrr':[],'xy':[],'datanode':[]})

        for unit_number in range(len(hdf5_1.data_2d[0])-1,0,-1): #Todo transitoire
            # Todo et recuperer temps depuis deltatlist
            deltat=deltatlist[unit_number]

            q1=hdf5_1.data_2d[reach_number][unit_number].unit_name #q1>q2
            q2 = hdf5_1.data_2d[reach_number][unit_number-1].unit_name  # q2<q1
            #Todo check that the discharge are increasing time step hydropeaking the flow is increasing or decreasing  TXT file must indicate time interval and the way the information is sorted
            tin1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"]
            tin2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["tin"]

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
            datanode1=hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].to_numpy()
            datanode2 = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].to_numpy()


            i_whole_profile1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
            i_whole_profile2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["i_whole_profile"]
            sortwp1, sortwp2, iwholedone, rwp1, rwp2=analyse_whole_profile(i_whole_profile1, i_whole_profile2)
            imeshpt3=0
            tin3 = []
            i_whole_profile3 = []
            i_split3 = []
            max_slope_bottom3=[]
            deltaz3=[]
            xy3=[]
            datanode3=[]

            def store_mesh_tin1(k,imeshpt3):
                i_whole_profile3.append(iwp)
                max_slope_bottom3.append(max_slope_bottom_whole_profile[iwp])
                deltaz3.append(deltaz3_)
                i_split3.append(
                    0)  # even in the case of isplit1=1 ie cut2D have left a triangle part of the mesh that was partially wetted

                for i3 in range(3):
                    xy3.append(xy1[tin1[sortwp1[rwp1[iwp][0] + k][1]][i3]])
                    datanode3.append(datanode1[tin1[sortwp1[rwp1[iwp][0] + k][1]][i3]])
                tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 2])

                iwholedone[iwp] = 1



            for iwp in range(len(iwholedone)):
                if iwholedone[iwp]==0:
                    if rwp1[iwp][1]==0: #  CASE 0  the tin1 mesh is dryed
                        if rwp2[iwp][1]==0:
                            iwholedone[iwp]=2
                        else:
                            iwholedone[iwp] = -1
                    elif rwp1[iwp][1]==1:
                        if rwp2[iwp][1]==0: # CASE 1a & 1b the tin1 mesh has been dryed
                            deltaz3_ = calculate_deltaz3(iwp, locawp, countcontactwp, sortwp1, sortwp2, rwp1, rwp2,
                                                         tin1, tin2, zsurf1, zsurf2)
                            # i_whole_profile3.append(iwp)
                            # max_slope_bottom3.append(max_slope_bottom_whole_profile[iwp])
                            # deltaz3.append(deltaz3_)
                            # i_split3.append(0) #even in the case of isplit1=1 ie cut2D have left a triangle part of the mesh that was partially wetted
                            # for i3 in range(3):
                            #     xy3.append(xy1[tin1[sortwp1[ rwp1[iwp][0] ][1]][i3]])
                            #     datanode3.append(datanode1[tin1[sortwp1[rwp1[iwp][0]][1]][i3]])
                            # tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 2])
                            # iwholedone[iwp] = 1
                            store_mesh_tin1(0, imeshpt3)
                            imeshpt3 += 3

                        elif rwp2[iwp][1] ==1:
                            if i_split1[sortwp1[rwp1[iwp][0]][1]]==1 and i_split2[sortwp2[rwp2[iwp][0]][1]]==1:




                                titi=3




                            elif i_split1[sortwp1[rwp1[iwp][0]][1]]==0 and i_split2[sortwp2[rwp2[iwp][0]][1]]==0: #CASE 1a
                                iwholedone[iwp] = 2
                            else:
                                iwholedone[iwp] = -1

                        # elif rwp2[iwp][1]>1: # the mesh has been partially dryed
                        #     deltaz3com=calculate_deltaz3(iwp, locawp, countcontactwp, sortwp1, sortwp2, rwp1, rwp2,
                        #                           tin1, tin2, zsurf1, zsurf2)
                        #     xyp=[]
                        #     datameshp=[]
                        #     for i3 in range(3):
                        #         xyp.append(xy1[tin1[sortwp1[ rwp1[iwp][0] ][1]][i3]])
                        #         datameshp.append(datanode1[tin1[sortwp1[rwp1[iwp][0]][1]][i3]])
                        #     xyp_=np.array(xyp)
                        #     datameshp_=np.array(datameshp)
                        #
                        #     for j in range(rwp2[iwp][1]):
                        #         tin3.append([imeshpt3, imeshpt3 + 1, imeshpt3 + 2])
                        #         i_whole_profile3.append(iwp)
                        #         max_slope_bottom3.append(max_slope_bottom_whole_profile[iwp])
                        #         deltaz3.append(deltaz3com)
                        #         i_split3.append(1)
                        #         imeshpt3 += 3
                        #         xyp=np.array()
                        #         for i3 in range(3):
                        #             xy3_=xy2[tin2[sortwp2[rwp2[iwp][0]][1] + j][i3]]
                        #             xy3.append(xy3_)
                        #             datanode3_=finite_element_interpolation(xy3_,xyp_,datameshp_)
                        #             datanode3.append(datanode3_)
                        #     iwholedone[iwp] = 1
                    elif rwp1[iwp][1] == 2:
                        if rwp2[iwp][1] == 0:  # CASE 3a the tin1 2 meshes has been dryed
                            deltaz3_ =calculate_deltaz3(iwp, locawp, countcontactwp, sortwp1, sortwp2, rwp1, rwp2,
                                                             tin1, tin2, zsurf1, zsurf2)
                            for k in range(2):
                                store_mesh_tin1(k,imeshpt3)
                                imeshpt3 += 3


                    else: # unknown domain
                                iwholedone[iwp] = 2

            tin3 = np.array(tin3)
            i_whole_profile3 = np.array(i_whole_profile3)
            i_split3 = np.array(i_split3)
            max_slope_bottom3=np.array(max_slope_bottom3)
            deltaz3=np.array(deltaz3)
            hrr3=(deltaz3/max_slope_bottom3)/deltat
            xy3=np.array(xy3)
            datanode3=np.array(datanode3)




            hrrlistdic[reach_number]['unit_name'].append(q1+'>'+q2)
            hrrlistdic[reach_number]['tin'].append(tin3)
            hrrlistdic[reach_number]['i_whole_profile'].append(i_whole_profile3)
            hrrlistdic[reach_number]['i_split'].append(i_split3)
            hrrlistdic[reach_number]['max_slope_bottom'].append(max_slope_bottom3)
            hrrlistdic[reach_number]['deltaz'].append(deltaz3)
            hrrlistdic[reach_number]['hrr'].append(hrr3)
            hrrlistdic[reach_number]['xy'].append(xy3)
            hrrlistdic[reach_number]['datanode'].append(datanode3)


    return hrrlistdic



if __name__ == '__main__':
    # set working directory to "C:\habby_dev\habby"
    path_prj = r"C:\Users\yann.lecoarer\Documents\HABBY_projects\DefaultProj"

    # first file
    input_filename_1 = "d1_d2_d3_d4.hyd"
    hrr(input_filename_1,[0,3.6*3600,2.5*3600,1.8*3600])




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
