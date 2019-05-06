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
    data_2d_whole_profile = dict(data_2d_from_ascii)

    # progress from 10 to 90 : from 0 to len(units_index)
    delta = int(80 / int(data_description["reach_number"]))

    # for each reach
    for reach_num in range(int(data_description["reach_number"])):
        # for each units
        for i, unit_index in enumerate(data_description["unit_list"].split(", ")):
            # conca xy with z value to facilitate the cutting of the grid (interpolation)
            xy = np.insert(data_2d_from_ascii["xy"][reach_num][i],
                           2,
                           values=data_2d_from_ascii["z"][reach_num][i],
                           axis=1)  # Insert values before column 2
            [tin_data, xy_data, h_data, v_data, ind_new] = manage_grid_mod.cut_2d_grid(data_2d_from_ascii["tin"][reach_num][i],
                                                                                       xy,
                                                                                       data_2d_from_ascii["h"][reach_num][i],
                                                                                       data_2d_from_ascii["v"][reach_num][i],
                                                                                       progress_value,
                                                                                       delta,
                                                                                       minwh,
                                                                                       True)
            if not isinstance(tin_data, np.ndarray):
                print("Error: cut_2d_grid")
                q.put(mystdout)
                return

            data_2d_from_ascii["tin"][reach_num][i] = tin_data
            data_2d_from_ascii["i_whole_profile"][reach_num][i] = ind_new
            data_2d_from_ascii["xy"][reach_num][i] = xy_data[:, :2]
            data_2d_from_ascii["h"][reach_num][i] = h_data
            data_2d_from_ascii["v"][reach_num][i] = v_data
            data_2d_from_ascii["z"][reach_num][i] = xy_data[:, 2]

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
    hyd_description["hyd_unit_z_equal"] = "all"

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
    path = os.path.dirname(filename)
    fnoden, ftinn = os.path.join(path,'wwnode.txt'), os.path.join(path,'wwtin.txt')
    fi = open(filename, 'r', encoding='utf8')
    fnode = open(fnoden, 'w', encoding='utf8')
    ftin = open(ftinn, 'w', encoding='utf8')
    kk, reachnumber = 0, 0
    msg, unittype = '', ''
    lunitall = []
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
        elif ls[0].lower() == 'number':
            if kk != 2:
                msg = 'number but not EPSG just before'
                break
            if len(ls) != 2:
                msg = 'unit description number but not only one information just after'
                break
            unittype = ls[1]
            lunit,nbnumber = [],0
            kk = 3
        elif ls[0].upper() == 'REACH':
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
                if j / 2 != nbnumber:
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
            nbnumber += 1
            if int(ls[0]) != nbnumber:
                msg = 'not the right number waited for'
                # print(type(nbnumber), type(ls[0]))
                break
            if len(ls) != 2:
                msg = 'unit description number but not only one information just after'
                break
            lunit.append(ls[1])
        elif kk == 6:
            if len(ls) != 3 + 2 * nbnumber:
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

    lunitall.append(lunit)
    lnode.append((nodei, nodef))
    ltin.append((tini, tinf))
    fi.close()
    fnode.close()
    ftin.close()
    nodesall = np.loadtxt(fnoden)
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
        for unit_num in range(nbnumber):
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
                              model_type="ASCII txt",
                              model_dimension=str(2),
                              epsg_code=epsgcode)
    # data_description
    data_description["unit_list"] = ", ".join(lunit)
    data_description["unit_list_full"] = ", ".join(lunit)
    data_description["unit_list_tf"] = []
    data_description["unit_number"] = str(nbnumber)
    data_description["unit_type"] = unittype
    data_description["reach_list"] = ", ".join(lreachname)
    data_description["reach_number"] = str(reachnumber)
    data_description["reach_type"] = "river"
    if unittype.upper()[0]=='Q' :
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
