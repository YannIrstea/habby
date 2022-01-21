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


def hrr(hydrosignature_description, progress_value, q=[], print_cmd=False, project_properties={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    # progress
    progress_value.value = 10

    # deltatlist = hydrosignature_description["deltatlist"]
    deltatlist = [0,3.6*3600,2.5*3600,1.8*3600]  # TODO: change it
    input_filename_1 = hydrosignature_description["hdf5_name"]
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
            # TODO: pandas data can have several dtype
            datanode1=hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].to_numpy()
            datanode2 = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"].to_numpy()


            i_whole_profile1 = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
            i_whole_profile2 = hdf5_1.data_2d[reach_number][unit_number-1]["mesh"]["i_whole_profile"]
            sortwp1, sortwp2, iwholedone, rwp1, rwp2=analyse_whole_profile(i_whole_profile1, i_whole_profile2)
            imeshpt3=0
            tin3 = []
            datamesh3=[]
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
                datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0] + k]])

                iwholedone[iwp] = 1

            # progress
            delta_mesh = delta_unit / len(iwholedone)

            for iwp in range(len(iwholedone)):

                # progress
                progress_value.value = progress_value.value + delta_mesh

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
                        #         datamesh3.append(datamesh1.iloc[sortwp1[rwp1[iwp][0] ]]) # ou quelque chose du genre
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
            hrr3=(deltaz3/max_slope_bottom3)/(deltat*3600)
            xy3=np.array(xy3)
            datanode3=np.array(datanode3)
            #TODO datamesh3

            #remove_duplicate_points
            # don't do xy3b, indices2, indices3 = np.unique... because indices2 haven't got the good size
            xy3b, indices2 = np.unique(xy3, axis=0, return_inverse=True)
            if len(xy3b)<len(xy3):
                tin3= indices2[tin3]
                xy3b,indices3 = np.unique(xy3, axis=0, return_index=True)
                datanode3= datanode3[indices3]

            unit_list[reach_number][unit_counter_3] = q1+'>'+q2
            new_data_2d[reach_number][unit_counter_3].unit_name = q1+'>'+q2
            new_data_2d[reach_number][unit_counter_3]["mesh"]["tin"] = tin3
            new_data_2d[reach_number][unit_counter_3]["mesh"]["data"] = pd.DataFrame()  # TODO: datamesh3 (à l'origine iwhole,isplikt et peut être des choses en volume fini) il faut refaire un pandas data mesh with pandas_array.iloc
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



if __name__ == '__main__':
    # set working directory to "C:\habby_dev\habby"
    path_prj = r"C:\Users\Quent\Documents\HABBY_projects\DefaultProj" # C:\Users\yann.lecoarer\Documents\HABBY_projects\DefaultProj

    project_properties = load_project_properties(path_prj)
    hrr_description_dict = dict(deltatlist=[0, 3.6 * 3600, 2.5 * 3600, 1.8 * 3600],
                           hdf5_name="a1_a2_a3_a4.hyd")
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
