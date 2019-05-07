"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V /
|  _  ||  _  || ___ \ ___ \ \ /
| | | || | | || |_/ / |_/ / | |
\_| |_/\_| |_/\____/\____/  \_/

Copyright (c) IRSTEA-EDF-AFB 2017-2018

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import os
import sys
from io import StringIO
import numpy as np
from copy import deepcopy

from src_GUI import preferences_GUI
from src import hdf5_mod
from src import manage_grid_mod


def load_ascii_and_cut_grid(file_path, path_prj, progress_value, q=[], print_cmd=False, fig_opt={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not fig_opt:
        fig_opt = preferences_GUI.create_default_figoption()
    minwh = fig_opt['min_height_hyd']

    # progress
    progress_value.value = 10

    # load data from txt file
    data_2d_from_ascii, data_description = load_ascii_model(file_path, path_prj)
    data_2d_whole_profile = deepcopy(data_2d_from_ascii)

    # progress from 10 to 90 : from 0 to len(units_index)
    delta = int(80 / int(data_description["reach_number"]))

    # for each reach
    for reach_num in range(int(data_description["reach_number"])):
        # for each units
        for unit_num, unit_index in enumerate(data_description["unit_list"].split(", ")):
            # conca xy with z value to facilitate the cutting of the grid (interpolation)
            xy = np.insert(data_2d_from_ascii["xy"][reach_num][unit_num],
                           2,
                           values=data_2d_from_ascii["z"][reach_num][unit_num],
                           axis=1)  # Insert values before column 2
            # [tin_data, xy, h_data, v_data, ind_new] = manage_grid_mod.cut_2d_grid(data_2d_from_ascii["tin"][reach_num][unit_num],
            #                                                                            xy,
            #                                                                            data_2d_from_ascii["h"][reach_num][unit_num],
            #                                                                            data_2d_from_ascii["v"][reach_num][unit_num],
            #                                                                            progress_value,
            #                                                                            delta,
            #                                                                            minwh,
            #                                                                            True)
            # if not isinstance(tin_data, np.ndarray):
            #     print("Error: cut_2d_grid")
            #     q.put(mystdout)
            #     return

            # if we want to disable cut_2d_grid (for dev)
            tin_data = data_2d_from_ascii["tin"][reach_num][unit_num]
            ind_new = np.array([10] * len(data_2d_from_ascii["tin"][reach_num][unit_num]))
            h_data = data_2d_from_ascii["h"][reach_num][unit_num]
            v_data = data_2d_from_ascii["v"][reach_num][unit_num]

            # replace cuted grid in dict
            data_2d_from_ascii["tin"][reach_num][unit_num] = tin_data
            data_2d_from_ascii["i_whole_profile"][reach_num][unit_num] = ind_new
            data_2d_from_ascii["xy"][reach_num][unit_num] = xy[:, :2]
            data_2d_from_ascii["h"][reach_num][unit_num] = h_data
            data_2d_from_ascii["v"][reach_num][unit_num] = v_data
            data_2d_from_ascii["z"][reach_num][unit_num] = xy[:, 2]

    # ALL CASE SAVE TO HDF5
    progress_value.value = 90  # progress

    # hyd description
    hyd_description = dict()
    hyd_description["hyd_filename_source"] = data_description["filename_source"]
    hyd_description["hyd_model_type"] = data_description["model_type"]
    hyd_description["hyd_model_dimension"] = data_description["model_dimension"]
    hyd_description["hyd_variables_list"] = "h, v, z"
    hyd_description["hyd_epsg_code"] = data_description["epsg_code"]
    hyd_description["hyd_reach_list"] = data_description["reach_list"]
    hyd_description["hyd_reach_number"] = data_description["reach_number"]
    hyd_description["hyd_reach_type"] = data_description["reach_type"]
    hyd_description["hyd_unit_list"] = data_description["unit_list"]
    hyd_description["hyd_unit_number"] = data_description["unit_number"]
    hyd_description["hyd_unit_type"] = data_description["unit_type"]
    hyd_description["hyd_unit_wholeprofile"] = "all"
    hyd_description["hyd_unit_z_equal"] = "True"

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(data_description["path_prj"],
                                   data_description["hdf5_name"])
    hdf5.create_hdf5_hyd(data_2d_from_ascii,
                         data_2d_whole_profile,
                         hyd_description)

    # progress
    progress_value.value = 92

    # export_mesh_whole_profile_shp
    hdf5.export_mesh_whole_profile_shp(fig_opt)

    # progress
    progress_value.value = 96

    # export shape
    hdf5.export_mesh_shp(fig_opt)

    # progress
    progress_value.value = 98

    # export_point_shp
    hdf5.export_point_shp(fig_opt)

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_ascii_model(filename, path_prj):
    """
    using a text file description of hydraulic outputs from a 2 D model (with or without substrate description)
    several reaches and units (discharges or times )descriptions are allowed
    :param filename: the name of the text file
    :param path_prj:
    :return: data_2d, data_description two dictionnary with elements for writing hdf5 datasets and attribute
    """
    path = os.path.dirname(filename)
    fnoden, ftinn = os.path.join(path,'wwnode.txt'), os.path.join(path,'wwtin.txt')
    fi = open(filename, 'r', encoding='utf8')
    fnode = open(fnoden, 'w', encoding='utf8')
    ftin = open(ftinn, 'w', encoding='utf8')
    kk, reachnumber,nbunitforall = 0, 0,0
    msg, unit_type = '', ''
    lunitall = []
    bq = False
    for i, ligne in enumerate(fi):
        ls = ligne.split()  # NB ls=s.split('\t') ne marche pas s[11]=='/t'-> FALSE
        # print (i,ls)
        if len(ls) == 0:  # empty line
            pass
        elif ls[0][0] == '#':  # comment line
            pass
        elif ls[0].upper() == 'HABBY':
            kk = 1
        elif 'EPSG' in ls[0].upper():
            if kk != 1:
                msg = 'EPSG but not HABBY just before'
                break
            kk = 2
            epsgcode = ls[1]
        elif ls[0][0:2].upper() == 'Q[' or ls[0][0:2].lower() == 't[' :
            if kk != 2 and kk!=4:
                msg = ls[0] +' but not EPSG just before or REACH before'
                break
            if len(ls) !=1:
                msg = 'unit description ' + ls[0] + '  but not the only one information'
                break
            if kk==4:
                if ls[0][0:2].lower() == 't[':
                    msg = ls[0] + ' but t[XXX  after REACH is forbiden all the reaches must have the same times units'
                    break
                else:
                    if bq == False and reachnumber !=1:
                        msg = ls[ 0] + ' This structure REACH unit description is forbiden '
                        break
                    bq=True
            unit_type = ls[0]
            lunit,nbunit = [],0
            kk = 3
        elif ls[0].upper() == 'REACH':
            if kk != 2 and kk!=3 and kk<7 :
                msg = ls[0] +' but not EPSG  or Q[XXX or t[XXX before'
                break
            if bq  and kk==3:
                msg = ls[0] + ' This structure REACH unit description is forbiden '
                break
            reachnumber+=1
            if reachnumber==1:
                lreachname=[('_'.join(ls[1:]))]
                nodei,nodef,tini,tinf=0,0,0,0
                lnode=[]
                ltin=[]
            else:
                lreachname.append(('_'.join(ls[1:])))
                lnode.append((nodei,nodef))
                ltin.append((tini, tinf))
                nodei, tini = nodef, tinf
            kk = 4
        elif ls[0].upper() == 'NODES':
            if kk != 3 and kk!=4:
                msg = ls[0] +' but not REACH or Units description (Q[XXX ,Q1,Q2.. or t[XXX,t1,t2  before'
                break
            if bq:
                if reachnumber==1:
                    nbunitforall=nbunit
                else:
                    if nbunitforall!=nbunit:
                        msg = ' the number of units Q[XXX ,Q1,Q2 after REACH must be constant for each reach'
                        break
            lunitall.append(lunit)
            kk = 5
        elif ls[0].lower() == 'x':
            if kk != 5:
                msg = 'x but not NODES just before'
                break
            if ls[1].lower() != 'y':
                msg = 'x but not y just after'
                break
            if ls[2].lower() == 'z':
                j = len(ls) - 3
                if j % 2 != 0:
                    msg = 'number of information after z not even'
                    break
                if j / 2 != nbunit:
                    msg = 'number of informations h v != number'
                    break
                ik = 0
                for k in range(3, len(ls), 2):
                    ik += 1
                    if ls[k][0].lower() != 'h' or ls[k + 1][0].lower() != 'v':
                        msg = ' information h or v not found'
                        break
                    if int(ls[k][1:]) != ik or int(ls[k + 1][1:]) != ik:
                        msg = ' information number after h or v not found'
                        break
            kk = 6
        elif ls[0].upper() == 'TIN':
            kk = 7
        elif kk == 3:
            nbunit += 1
            if len(ls) != 1:
                msg = 'unit description but not only one information'
                break
            lunit.append(ls[0])
        elif kk == 6:
            if len(ls) != 3 + 2 * nbunit:
                msg = 'NODES not the right number of informations waited for'
                break
            fnode.write(ligne)
            nodef+=1
        elif kk == 7:
            if len(ls) == 3:
                ftin.write('\t'.join(ls) + '\t' + '-1' + '\n')
            elif len(ls) == 4:
                ftin.write(ligne)
            else:
                msg = 'TIN not the right number of informations waited for'
                break
            tinf+=1

    if msg != '':
        print('ligne : ', i, '\n', ligne, '\n', msg)
        return False
    else:
        pass


    lnode.append((nodei, nodef))
    ltin.append((tini, tinf))
    fi.close()
    fnode.close()
    ftin.close()
    nodesall = np.loadtxt(fnoden,dtype=float)
    ikleall = np.loadtxt(ftinn,dtype=int)
    os.remove(fnoden)
    os.remove(ftinn)

    # creaet empty dict
    data_2d = dict()
    data_2d["tin"] = [[] for _ in range(reachnumber)]  # create a number of empty nested lists for each reach
    data_2d["i_whole_profile"] = [[] for _ in range(reachnumber)]
    data_2d["xy"] = [[] for _ in range(reachnumber)]
    data_2d["h"] = [[] for _ in range(reachnumber)]
    data_2d["v"] = [[] for _ in range(reachnumber)]
    data_2d["z"] = [[] for _ in range(reachnumber)]

    for reach_num in range(reachnumber):
        nodes=np.array(nodesall[lnode[reach_num][0]:lnode[reach_num][1],:])
        ikle =np.array(ikleall[ltin[reach_num][0]:ltin[reach_num][1],:])
        nbnodes = len(nodes)
        if ikle.max() != nbnodes - 1:
            print('REACH :', lreachname[reach_num], "max(ikle)!= nbnodes TIN and Nodes number doesn't fit ")
            return False
        # managing  the 4angles (for triangle last index=-1)
        ikle3 = ikle[np.where(ikle[:, [3]] == -1)[0]]
        ikle4 = ikle[np.where(ikle[:, [3]] != -1)[0]]
        ikle = ikle3[:, 0:3]
        if len(ikle4): # partitionning each 4angles in 4 triangles
            for i in range( len(ikle4)):
                nbnodes+=1
                ikle = np.append(ikle, np.array([[ikle4[i][0], nbnodes-1, ikle4[i][3]], [ikle4[i][0], ikle4[i][1], nbnodes-1],
                                                 [ikle4[i][1], ikle4[i][2], nbnodes-1], [nbnodes-1, ikle4[i][2], ikle4[i][3]]]),
                                 axis=0)
                newnode=np.mean(nodes[[ikle4[i][0],ikle4[i][1],ikle4[i][2],ikle4[i][3]],:], axis=0)
                nodes=np.append(nodes,np.array([newnode]),axis=0)
        for unit_num in range(nbunit):
            data_2d["tin"][reach_num].append(ikle)
            data_2d["i_whole_profile"][reach_num].append(ikle)
            data_2d["xy"][reach_num].append(nodes[:, :2])
            data_2d["h"][reach_num].append(nodes[:, 2+unit_num*2+1])
            data_2d["v"][reach_num].append(nodes[:, 2+unit_num*2+2])
            data_2d["z"][reach_num].append(nodes[:, 2])

    data_description = dict(path_prj=path_prj,
                              name_prj=os.path.basename(path_prj),
                              hydrau_case="unknown",
                              filename_source=os.path.basename(filename),
                              path_filename_source=path,
                              hdf5_name=os.path.splitext(os.path.basename(filename))[0] + ".hyd",
                              model_type="ASCII",
                              model_dimension=str(2),
                              epsg_code=epsgcode)
    # data_description
    data_description["unit_list"] = ", ".join(lunit) # TODO lunitall indiquer par reach les debits
    data_description["unit_list_full"] = ", ".join(lunit) # TODO lunitall indiquer par reach les debits
    data_description["unit_list_tf"] = []
    data_description["unit_number"] = str(nbunit)
    data_description["unit_type"] = unit_type
    data_description["reach_list"] = ", ".join(lreachname)
    data_description["reach_number"] = str(reachnumber)
    data_description["reach_type"] = "river"
    if unit_type.upper()[0]=='Q' :
        data_description["flow_type"] = "continuous flow"
    else:
        data_description["flow_type"] = "transient flow"
    return data_2d, data_description


def get_time_step(file_path):
    faiload = [-99], [-99]
    # file exist ?
    if not os.path.isfile(file_path):
        print('Error: The ascci text file does not exist. Cannot be loaded.')
        return faiload

    nbtimes = 0
    timestep_string = "0"

    return nbtimes, timestep_string
