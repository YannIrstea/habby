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
from copy import deepcopy
from io import StringIO

import numpy as np

from src.tools_mod import isstranumber
from src import hdf5_mod
from src import manage_grid_mod
from src import mesh_management_mod
from src_GUI import preferences_GUI


def load_ascii_and_cut_grid(hydrau_description, progress_value, q=[], print_cmd=False, fig_opt={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    file_path = os.path.join(hydrau_description["path_filename_source"], hydrau_description["filename_source"])
    path_prj = hydrau_description["path_prj"]
    sub_presence = False # no substrate init
    # minimum water height
    if not fig_opt:
        fig_opt = preferences_GUI.create_default_figoption()
    minwh = fig_opt['min_height_hyd']

    # progress
    progress_value.value = 10

    # load data from txt file
    data_2d_from_ascii, data_description = load_ascii_model(file_path, path_prj)
    if not data_2d_from_ascii and not data_description:
        q.put(mystdout)
        return

    if "sub" in data_2d_from_ascii.keys():
        sub_presence = True

    # create copy
    data_2d_whole_profile = deepcopy(data_2d_from_ascii)

    # create empty dict
    data_2d = dict()
    data_2d["tin"] = []
    data_2d["i_whole_profile"] = []
    data_2d["sub"] = []
    data_2d["xy"] = []
    data_2d["h"] = []
    data_2d["v"] = []
    data_2d["z"] = []

    # progress from 10 to 90 : from 0 to len(units_index)
    delta = int(80 / int(data_description["reach_number"]))

    # for each reach
    for reach_num in range(int(data_description["reach_number"])):
        data_2d["tin"].append([])
        data_2d["i_whole_profile"].append([])
        data_2d["sub"].append([])
        data_2d["xy"].append([])
        data_2d["h"].append([])
        data_2d["v"].append([])
        data_2d["z"].append([])

        # for each units
        for unit_num in reversed(range(len(data_description["unit_list"][reach_num]))):  # reversed for pop
            # get unit from according to user selection
            if hydrau_description["unit_list_tf"][reach_num][unit_num]:

                # conca xy with z value to facilitate the cutting of the grid (interpolation)
                xy = np.insert(data_2d_from_ascii["xy"][reach_num][unit_num],
                               2,
                               values=data_2d_from_ascii["z"][reach_num][unit_num],
                               axis=1)  # Insert values before column 2

                # cut mesh dry and cut partialy dry in option
                [tin_data, xy_cuted, h_data, v_data, i_whole_profile] = manage_grid_mod.cut_2d_grid(
                    data_2d_from_ascii["tin"][reach_num][unit_num],
                    xy,
                    data_2d_from_ascii["h"][reach_num][unit_num],
                    data_2d_from_ascii["v"][reach_num][unit_num],
                    progress_value,
                    delta,
                    fig_opt["CutMeshPartialyDry"],
                    minwh)

                if not isinstance(tin_data, np.ndarray):
                    print("Error: cut_2d_grid")
                    q.put(mystdout)
                    return

                # get substrate after cuting mesh
                if sub_presence:
                    sub = data_2d_from_ascii["sub"][reach_num][unit_num][i_whole_profile]

                # get cuted grid
                data_2d["tin"][reach_num].append(tin_data)
                data_2d["i_whole_profile"][reach_num].append(i_whole_profile)
                data_2d["xy"][reach_num].append(xy_cuted[:, :2])
                data_2d["h"][reach_num].append(h_data)
                data_2d["v"][reach_num].append(v_data)
                data_2d["z"][reach_num].append(xy_cuted[:, 2])
                if sub_presence:
                    data_2d["sub"][reach_num].append(sub)

            # erase unit in whole_profile
            else:
                data_2d_whole_profile["tin"][reach_num].pop(unit_num)
                data_2d_whole_profile["i_whole_profile"][reach_num].pop(unit_num)
                data_2d_whole_profile["xy"][reach_num].pop(unit_num)
                data_2d_whole_profile["h"][reach_num].pop(unit_num)
                data_2d_whole_profile["v"][reach_num].pop(unit_num)
                data_2d_whole_profile["z"][reach_num].pop(unit_num)

    # ALL CASE SAVE TO HDF5
    progress_value.value = 90  # progress

    # change unit from according to user selection
    for reach_units_index in range(len(hydrau_description["unit_list"])):
        hydrau_description["unit_list"][reach_units_index] = [x for x, y in zip(hydrau_description["unit_list"][reach_units_index], hydrau_description["unit_list_tf"][reach_units_index]) if y]
    hydrau_description["unit_number"] = str(len(hydrau_description["unit_list"][reach_units_index]))

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
    hyd_description["hyd_unit_list"] = hydrau_description["unit_list"]
    hyd_description["hyd_unit_number"] = hydrau_description["unit_number"]
    hyd_description["hyd_unit_type"] = data_description["unit_type"]
    hyd_description["hyd_unit_wholeprofile"] = "all"
    hyd_description["hyd_unit_z_equal"] = "True"
    if fig_opt["CutMeshPartialyDry"] == "False":
        namehdf5_old = os.path.splitext(data_description["hdf5_name"])[0]
        data_description["hdf5_name"] = namehdf5_old + "_no_cut.hyd"

    # change extension of hdf5 to create .hab
    if sub_presence:
        hyd_description["sub_classification_method"] = data_description["sub_classification_method"]
        hyd_description["sub_classification_code"] = data_description["sub_classification_code"]
        hyd_description["sub_mapping_method"] = data_description["sub_mapping_method"]
        hyd_description["hab_epsg_code"] = data_description["epsg_code"]
        data_description["hdf5_name"] = os.path.splitext(data_description["hdf5_name"])[0] + ".hab"

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(data_description["path_prj"],
                                   data_description["hdf5_name"])
    if not sub_presence:
        hdf5.create_hdf5_hyd(data_2d,
                             data_2d_whole_profile,
                             hyd_description,
                             fig_opt)
    if sub_presence:
        hdf5.create_hdf5_hab(data_2d,
                             data_2d_whole_profile,
                             hyd_description,
                             fig_opt)

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
    transforming v<0 in abs(v) ; hw<0 in hw=0 and where hw=0 v=0
    transforming each quadrangle into 4 triangle and taking care of partially wet quadrangles to interpolate the centers
    WARNING this function is parallel with get_ascii_model_description function and some integrity tests are similar
    :param filename: the name of the text file
    :param path_prj:
    :return: data_2d, data_description two dictionnary with elements for writing hdf5 datasets and attribute
    """
    faiload = False, False
    path = os.path.dirname(filename)
    fnoden, ftinn, fsubn = os.path.join(path, 'wwnode.txt'), os.path.join(path, 'wwtin.txt'), os.path.join(path,
                                                                                                           'wwsub.txt')
    fi = open(filename, 'r', encoding='utf8')
    fnode = open(fnoden, 'w', encoding='utf8')
    ftin = open(ftinn, 'w', encoding='utf8')
    kk, reachnumber, nbunitforall, nbreachsub = 0, 0, 0, 0
    msg, unit_type = '', ''
    lunitall = []  # a list of  [list of Q or t] per reach
    bq_per_reach, bsub,bmeshconstant = False, False, True
    sub_classification_code, sub_classification_method = '', ''
    nbsubinfo = 0
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
        elif ls[0][0:2].upper() == 'Q[' or ls[0][0:2].lower() == 't[':
            if kk != 2 and kk != 4:
                msg = ls[0] + ' but not EPSG just before or REACH before'
                break
            if len(ls) != 1:
                msg = 'unit description ' + ls[0] + '  but not the only one information'
                break
            if kk == 4:
                if ls[0][0:2].lower() == 't[':
                    msg = ls[0] + ' but t[XXX  after REACH is forbiden all the reaches must have the same times units'
                    break
                else:
                    if bq_per_reach == False and reachnumber != 1:
                        msg = ls[0] + ' This structure REACH unit description is forbiden '
                        break
                    bq_per_reach = True
            unit_type = ls[0]
            lunit, nbunit = [], 0
            kk = 3
        elif ls[0].upper() == 'REACH':
            if kk != 2 and kk != 3 and kk < 7:
                msg = ls[0] + ' but not EPSG  or Q[XXX or t[XXX before'
                break
            if bq_per_reach and kk == 3:
                msg = ls[0] + ' This structure REACH unit description is forbiden '
                break
            reachnumber += 1
            if reachnumber == 1:
                lreachname = [('_'.join(ls[1:]))]
                nodei, nodef, tini, tinf, tinfsub = 0, 0, 0, 0, 0
                lnode = []
                ltin = []
            else:
                lreachname.append(('_'.join(ls[1:])))
                lnode.append((nodei, nodef))
                ltin.append((tini, tinf))
                nodei, tini = nodef, tinf
                if bsub:
                    if tinfsub != tinf:
                        msg = ' number of meshes elements different between TIN and SUBSTRATE description'
                        break
            kk = 4
        elif ls[0].upper() == 'NODES':
            if kk != 3 and kk != 4:
                msg = ls[0] + ' but not REACH or Units description (Q[XXX ,Q1,Q2.. or t[XXX,t1,t2  before'
                break
            if bq_per_reach:
                if reachnumber == 1:
                    nbunitforall = nbunit
                else:
                    if nbunitforall != nbunit:
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
        elif ls[0].upper() == 'SUBSTRATE':
            if len(ls) != 2:
                msg = 'number of information for substrate_classification_code  not 2'
                break
            if reachnumber == 1:
                if ls[1].upper() == 'CEMAGREF':
                    sub_classification_code = "Cemagref"
                elif ls[1].upper() == 'SANDRE':
                    sub_classification_code = "Sandre"
                else:
                    msg = 'sub_classification_code given unknown'
                    break
            else:
                if ls[1].upper() != sub_classification_code.upper():
                    msg = 'sub_classification_code given not constant for all reaches'
                    break
            kk = 8
        elif ls[0].upper() == 'COARSER' or ls[0].upper() == 'S1':
            if kk != 8:
                msg = 'substrate_classification_method but not SUBSTRATE just before'
                break
            if ls[0].upper() == 'COARSER':
                if len(ls) != 2 or ls[1].upper() != 'DOMINANT':
                    msg = 'COARSER information given but not followed by DOMINANT'
                    break
                sub_classification_method = 'coarser-dominant'
            elif ls[0].upper() == 'S1':  # TODO  check Si ie S2 etc....
                if (len(ls) != 8 and sub_classification_code == "Cemagref") or (
                        len(ls) != 12 and sub_classification_code == "Sandre"):
                    msg = 'sub_classification_method percentage description irrelevant'
                    break
                sub_classification_method = 'percentage'
            if reachnumber == 1:
                nbsubinfo = len(ls)
                bsub = True
                fsub = open(fsubn, 'w', encoding='utf8')
            else:
                if len(ls) != nbsubinfo:
                    msg = 'sub_classification_method not constant for all reaches'
                    break
            kk = 9

        elif kk == 3:
            nbunit += 1
            if len(ls) != 1:
                msg = 'unit description but not only one information'
                break
            if not isstranumber(ls[0]):
                msg = 'unit description but not numeric information'
                break
            lunit.append(float(ls[0]))
        elif kk == 6:
            if len(ls) != 3 + 2 * nbunit:
                msg = 'NODES not the right number of informations waited for'
                break
            fnode.write(ligne)
            nodef += 1
        elif kk == 7:
            if len(ls) == 3:
                ftin.write('\t'.join(ls) + '\t' + '-1' + '\n')
            elif len(ls) == 4:
                ftin.write(ligne)
            else:
                msg = 'TIN not the right number of informations waited for'
                break
            tinf += 1
        elif kk == 9:
            if len(ls) != nbsubinfo:
                msg = 'number of integer given for substrate not correct'
                break
            tinfsub += 1
            fsub.write(ligne)

    if msg != '':
        print('Error:','ligne : ', i, ' {', ligne.rstrip() ,' }', msg)
        fi.close();
        fnode.close();
        ftin.close()
        os.remove(fnoden);
        os.remove(ftinn)
        if bsub:
            fsub.close();
            os.remove(fsubn)
        return faiload

    lnode.append((nodei, nodef))
    ltin.append((tini, tinf))
    fi.close()
    fnode.close()
    ftin.close()
    nodesall = np.loadtxt(fnoden, dtype=float)
    ikleall = np.loadtxt(ftinn, dtype=int)
    os.remove(fnoden)
    os.remove(ftinn)
    # transforming v<0 in abs(v) ; hw<0 in hw=0 and where hw=0 v=0
    for unit_num in range(nbunit):
        nodesall[:, 2 + unit_num * 2 + 2] = np.abs(nodesall[:, 2 + unit_num * 2 + 2])
        hwneg = np.where(nodesall[:, 2 + unit_num * 2 + 1] < 0)
        nodesall[:, 2 + unit_num * 2 + 1][hwneg] = 0
        hwnul = np.where(nodesall[:, 2 + unit_num * 2 + 1] == 0)
        nodesall[:, 2 + unit_num * 2 + 2][hwnul] = 0

    if bsub:
        fsub.close()
        suball = np.loadtxt(fsubn, dtype=int)
        os.remove(fsubn)
        if len(suball) != len(ikleall):
            print('Error:','the number of elements given for TIN  and SUBSTRATE description are different')
            return faiload
        if sub_classification_method == 'coarser-dominant':
            if sub_classification_code == "Cemagref":
                if suball.max() > 8 or suball.min() < 1:
                    msg = 'SUBSTRATE Cemagref coarser-dominant But extreme values are not in [1,8] '
            elif sub_classification_code == "Sandre":
                if suball.max() > 12 or suball.min() < 1:
                    msg = 'SUBSTRATE Sandre coarser-dominant But extreme values are not in [1,12] '
                if (suball[:, 0] >= suball[:, 1]).all() == False:
                    print(
                        'SUBSTRATE  coarser-dominant it happends that sizes seems incorrect coarser element < dominant element ')
        elif sub_classification_method == 'percentage':
            suball100 = np.sum(suball, axis=1)
            if (suball100 != 100).all():
                msg = 'SUBSTRATE percentage But not the all the sums =100 '
        if msg != '':
            print( 'Error:',msg)
            return faiload

    # create empty dict
    data_2d = dict()
    data_2d["tin"] = [[] for _ in range(reachnumber)]  # create a number of empty nested lists for each reach
    data_2d["i_whole_profile"] = [[] for _ in range(reachnumber)]
    if bsub:
        data_2d["sub"] = [[] for _ in range(reachnumber)]
    data_2d["xy"] = [[] for _ in range(reachnumber)]
    data_2d["h"] = [[] for _ in range(reachnumber)]
    data_2d["v"] = [[] for _ in range(reachnumber)]
    data_2d["z"] = [[] for _ in range(reachnumber)]

    for reach_num in range(reachnumber):
        nodes = np.array(nodesall[lnode[reach_num][0]:lnode[reach_num][1], :])
        ikle = np.array(ikleall[ltin[reach_num][0]:ltin[reach_num][1], :])
        if bsub:
            sub = np.array(suball[ltin[reach_num][0]:ltin[reach_num][1], :])
        nbnodes = len(nodes)
        if ikle.max() != nbnodes - 1:
            print('Error:','REACH :', lreachname[reach_num], "max(ikle)!= nbnodes TIN and Nodes number doesn't fit ")
            return faiload
        # managing  the 4angles (for triangle last index=-1)
        ikle3 = ikle[np.where(ikle[:, [3]] == -1)[0]]
        ikle4 = ikle[np.where(ikle[:, [3]] != -1)[0]]
        if bsub:
            sub4 = sub[np.where(ikle[:, [3]] != -1)[0]]
            sub = sub[np.where(ikle[:, [3]] == -1)[0]]
        ikle = ikle3[:, 0:3]

        if len(ikle4):  # partitionning each 4angles in 4 triangles
            for unit_num in range(nbunit):
                # always obtain the sames ikle3new,xynew,znew only hnew,vnew are differents
                ikle3new, xynew, znew, hnew, vnew = mesh_management_mod.quadrangles_to_triangles(ikle4, nodes[:, 0:2],
                                                                                                 nodes[:, 2], nodes[:,
                                                                                                              2 + unit_num * 2 + 1],
                                                                                                 nodes[:,
                                                                                                 2 + unit_num * 2 + 2])
                if unit_num == 0:
                    newnodes = np.concatenate((xynew, znew, hnew, vnew), axis=1)
                else:
                    newnodes = np.concatenate((newnodes, hnew, vnew), axis=1)
            ikle = np.append(ikle, ikle3new, axis=0)
            nodes = np.append(nodes, newnodes, axis=0)
            if bsub:
                for i in range(len(ikle4)):
                    sub = np.append(sub, np.array([sub4[i, :], ] * 4), axis=0)
        for unit_num in range(nbunit):
            data_2d["tin"][reach_num].append(ikle)
            data_2d["i_whole_profile"][reach_num].append(ikle)
            if bsub:
                data_2d["sub"][reach_num].append(sub)
            data_2d["xy"][reach_num].append(nodes[:, :2])
            data_2d["h"][reach_num].append(nodes[:, 2 + unit_num * 2 + 1])
            data_2d["v"][reach_num].append(nodes[:, 2 + unit_num * 2 + 2])
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
    data_description["unit_list"] = lunitall
    data_description["unit_list_full"] = lunitall
    data_description["unit_list_tf"] = []
    data_description["unit_number"] = str(nbunit)
    data_description["unit_type"] = unit_type
    data_description["reach_list"] = ", ".join(lreachname)
    data_description["reach_number"] = str(reachnumber)
    data_description["reach_type"] = "river"
    if unit_type.upper()[0] == 'Q':
        data_description["flow_type"] = "continuous flow"
    else:
        data_description["flow_type"] = "transient flow"
    if bsub:
        data_description["sub_mapping_method"] = "polygon"
        data_description["sub_classification_method"] = sub_classification_method  # "coarser-dominant" / "percentage"
        data_description["sub_classification_code"] = sub_classification_code  # "Cemagref" / "Sandre"

    return data_2d, data_description


def get_ascii_model_description(file_path):
    """
    using a text file description of hydraulic outputs from a 2 D model (with or without substrate description)
    several reaches and units (discharges or times )descriptions are allowed

    WARNING this function is parallel with  load_ascii_model function and some integrity tests are similar
    :param file_path:
    :return: the reachname list and the unit description (times or discharges)
    """
    faiload = False
    # file exist ?
    if not os.path.isfile(file_path):
        print('Error: The ascci text file does not exist. Cannot be loaded.')
        return faiload
    kk, reachnumber = 0, 0
    msg, unit_type = '', ''
    lunitall = []   # a list of  [list of Q or t] one element if all the Q or t are similar for all reaches
                    # or nbreaches elements
    epsgcode = ''
    bq_per_reach = False
    bsub =False
    with open(file_path, 'r', encoding='utf8') as fi:
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
            elif ls[0][0:2].upper() == 'Q[' or ls[0][0:2].lower() == 't[':
                if kk != 2 and kk != 4:
                    msg = ls[0] + ' but not EPSG just before or REACH before'
                    break
                if len(ls) != 1:
                    msg = 'unit description ' + ls[0] + '  but not the only one information'
                    break
                if kk == 4:
                    if ls[0][0:2].lower() == 't[':
                        msg = ls[
                                  0] + ' but t[XXX  after REACH is forbiden all the reaches must have the same times units'
                        break
                    else:
                        if bq_per_reach == False and reachnumber != 1:
                            msg = ls[0] + ' This structure REACH unit description is forbiden '
                            break
                        bq_per_reach = True
                unit_type = ls[0]
                lunit, nbunit = [], 0
                kk = 3
            elif ls[0].upper() == 'REACH':
                if kk != 2 and kk != 3 and kk < 7:
                    msg = ls[0] + ' but not EPSG  or Q[XXX or t[XXX before'
                    break
                if bq_per_reach and kk == 3:
                    msg = ls[0] + ' This structure REACH unit description is forbiden '
                    break
                reachnumber += 1
                if reachnumber == 1:
                    lreachname = [('_'.join(ls[1:]))]
                else:
                    lreachname.append(('_'.join(ls[1:])))
                kk = 4
            # .................
            elif ls[0].upper() == 'NODES':
                if kk != 3 and kk != 4:
                    msg = ls[0] + ' but not REACH or Units description (Q[XXX ,Q1,Q2.. or t[XXX,t1,t2  before'
                    break
                lunitall.append(lunit)
                kk = 5
            elif ls[0].upper() == 'TIN':
                kk = 7
            elif ls[0].upper() == 'SUBSTRATE':
                bsub=True
            elif kk == 3:
                nbunit += 1
                if len(ls) != 1:
                    msg = 'unit description but not only one information'
                    break
                lunit.append(ls[0])

        if msg != '':
            print('Error:','ligne : ', i, ' {', ligne.rstrip() ,' }', msg)
            return faiload

    # create dict
    ascii_description = dict(epsg_code=epsgcode,
                             unit_type=unit_type,
                             unit_list=lunitall,
                             reach_number=reachnumber,
                             reach_list=lreachname,
                             sub=bsub)

    return ascii_description
