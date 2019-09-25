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


def load_ascii_and_cut_grid(hydrau_description, progress_value, q=[], print_cmd=False, project_preferences={}, user_preferences_temp_path=''):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    file_path = os.path.join(hydrau_description["path_filename_source"], hydrau_description["filename_source"])
    path_prj = hydrau_description["path_prj"]
    sub_presence = False # no substrate init
    # minimum water height
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    minwh = project_preferences['min_height_hyd']

    # progress
    progress_value.value = 10

    # load data from txt file
    data_2d_from_ascii, data_description = load_ascii_model(file_path, path_prj, user_preferences_temp_path)
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
    data_2d["max_slope_bottom"] = []
    data_2d["max_slope_energy"] = []
    data_2d["shear_stress"] = []
    data_2d["total_wet_area"] = []

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
        data_2d["max_slope_bottom"].append([])
        data_2d["max_slope_energy"].append([])
        data_2d["shear_stress"].append([])
        data_2d["total_wet_area"].append([])

        # index to remove (from user selection GUI)
        index_to_remove = []

        # for each units
        for unit_num in range(len(data_description["unit_list"][reach_num])):
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
                    project_preferences["CutMeshPartialyDry"],
                    minwh)

                if not isinstance(tin_data, np.ndarray):
                    print("Error: cut_2d_grid")
                    q.put(mystdout)
                    return

                max_slope_bottom, max_slope_energy, shear_stress = manage_grid_mod.slopebottom_lopeenergy_shearstress_max(
                    xy1=xy_cuted[tin_data[:, 0]][:, [0, 1]],
                    z1=xy_cuted[tin_data[:, 0]][:, 2],
                    h1=h_data[tin_data[:, 0]],
                    v1=v_data[tin_data[:, 0]],
                    xy2=xy_cuted[tin_data[:, 1]][:, [0, 1]],
                    z2=xy_cuted[tin_data[:, 1]][:, 2],
                    h2=h_data[tin_data[:, 1]],
                    v2=v_data[tin_data[:, 1]],
                    xy3=xy_cuted[tin_data[:, 2]][:, [0, 1]],
                    z3=xy_cuted[tin_data[:, 2]][:, 2],
                    h3=h_data[tin_data[:, 2]],
                    v3=v_data[tin_data[:, 2]])

                # get area (based on Heron's formula)
                p1 = xy_cuted[tin_data[:, 0]][:, [0, 1]]
                p2 = xy_cuted[tin_data[:, 1]][:, [0, 1]]
                p3 = xy_cuted[tin_data[:, 2]][:, [0, 1]]
                d1 = np.sqrt((p2[:, 0] - p1[:, 0]) ** 2 + (p2[:, 1] - p1[:, 1]) ** 2)
                d2 = np.sqrt((p3[:, 0] - p2[:, 0]) ** 2 + (p3[:, 1] - p2[:, 1]) ** 2)
                d3 = np.sqrt((p3[:, 0] - p1[:, 0]) ** 2 + (p3[:, 1] - p1[:, 1]) ** 2)
                s2 = (d1 + d2 + d3) / 2
                area = s2 * (s2 - d1) * (s2 - d2) * (s2 - d3)
                area[area < 0] = 0  # -1e-11, -2e-12, etc because some points are so close
                area = area ** 0.5
                area_reach = np.sum(area)

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
                data_2d["max_slope_bottom"][reach_num].append(max_slope_bottom)
                data_2d["max_slope_energy"][reach_num].append(max_slope_energy)
                data_2d["shear_stress"][reach_num].append(shear_stress)
                data_2d["total_wet_area"][reach_num].append(area_reach)
                if sub_presence:
                    data_2d["sub"][reach_num].append(sub)
            # erase unit in whole_profile
            else:
                index_to_remove.append(unit_num)

        # index to remove (from user selection GUI)
        for index in reversed(index_to_remove):
            data_2d_whole_profile["tin"][reach_num].pop(index)
            data_2d_whole_profile["xy"][reach_num].pop(index)
            data_2d_whole_profile["z"][reach_num].pop(index)

    # remove unused keys
    del data_2d_whole_profile["i_whole_profile"]
    del data_2d_whole_profile["h"]
    del data_2d_whole_profile["v"]

    # ALL CASE SAVE TO HDF5
    progress_value.value = 90  # progress

    # change unit from according to user selection
    hydrau_description["unit_number"] = str(len(hydrau_description["unit_list"][0]))  # same unit len for each reach

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
    hyd_description["hyd_cuted_mesh_partialy_dry"] = str(project_preferences["CutMeshPartialyDry"])

    hyd_description["hyd_varying_mesh"] = data_description["varying_mesh"]
    if data_description["varying_mesh"]:
        hyd_description["hyd_unit_z_equal"] = False
    else:
        # TODO : check if all z values are equal between units
        hyd_description["hyd_unit_z_equal"] = True
    # if not project_preferences["CutMeshPartialyDry"]:
    #     namehdf5_old = os.path.splitext(data_description["hdf5_name"])[0]
    #     exthdf5_old = os.path.splitext(data_description["hdf5_name"])[1]
    #     data_description["hdf5_name"] = namehdf5_old + "_no_cut" + exthdf5_old

    # change extension of hdf5 to create .hab
    if sub_presence:
        hyd_description["sub_classification_method"] = data_description["sub_classification_method"]
        hyd_description["sub_classification_code"] = data_description["sub_classification_code"]
        hyd_description["sub_mapping_method"] = data_description["sub_mapping_method"]
        hyd_description["hab_epsg_code"] = data_description["epsg_code"]
        data_description["hdf5_name"] = hydrau_description["hdf5_name"]

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(data_description["path_prj"],
                                   hydrau_description["hdf5_name"])
    if not sub_presence:
        hdf5.create_hdf5_hyd(data_2d,
                             data_2d_whole_profile,
                             hyd_description,
                             project_preferences)
    if sub_presence:
        hdf5.create_hdf5_hab(data_2d,
                             data_2d_whole_profile,
                             hyd_description,
                             project_preferences)
        hdf5.export_stl()


    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_ascii_model(filename, path_prj, user_preferences_temp_path):
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
    path = os.path.dirname(filename)
    fnoden, ftinn, fsubn,ffvmn = os.path.join(user_preferences_temp_path, 'wwnode.txt'), os.path.join(user_preferences_temp_path, 'wwtin.txt'), os.path.join(user_preferences_temp_path,
                                                                                                           'wwsub.txt'), os.path.join(user_preferences_temp_path, 'wwfvm.txt')
    fi = open(filename, 'r', encoding='utf8')
    fnode = open(fnoden, 'w', encoding='utf8')
    ftin = open(ftinn, 'w', encoding='utf8')
    ffvm = open(ffvmn, 'w', encoding='utf8')
    kk, reachnumber, nbunitforall,nbunitforallvaryingmesh, nbreachsub = 0, 0, 0, 0,0
    msg, unit_type,sub = '', '',''
    lunitvaryingmesh=[]
    lunitall = []  # a list of  [list of Q or t] per reach
    bq_per_reach, bsub,bmeshconstant,bfvm = False, False, True,False
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
                nodei, nodef, tini, tinf, tinfsub,tinfvm = 0, 0, 0, 0, 0,0
                lnode = []
                ltin = []
            else:
                if '_'.join(ls[1:]) == lreachname[-1]:
                    if bmeshconstant :
                        msg = ' Structure whith reach description not truly available with variable mesh for each unit'
                        break
                    reachnumber -= 1
                    bmeshconstant = False
                else:
                    if not bmeshconstant :
                        lunitall.append(lunitvaryingmesh)
                        lunitvaryingmesh=[]
                    lreachname.append(('_'.join(ls[1:])))
                    if reachnumber>2 and nbunitforall !=nbunitforallvaryingmesh:
                        msg = ' varying mesh  an number of unit per reach not constant'
                        break
                    nbunitforallvaryingmesh=0
                lnode.append((nodei, nodef))
                ltin.append((tini, tinf))
                nodei, tini = nodef, tinf
                if bsub:
                    if tinfsub != tinf:
                        msg = ' number of meshes elements different between TIN and SUBSTRATE description'
                        break
                if bfvm:
                    if tinfvm != tinf:
                        msg = ' number of meshes elements different between TIN and FVM description'
                        break
            kk = 4
        elif ls[0].upper() == 'NODES':
            if kk != 3 and kk != 4:
                msg = ls[0] + ' but not REACH or Units description (Q[XXX ,Q1,Q2.. or t[XXX,t1,t2  before'
                break
            if bq_per_reach and bmeshconstant:
                if reachnumber == 1:
                    nbunitforall = nbunit
                else:
                    if nbunitforall != nbunit:
                        msg = ' the number of units Q[XXX ,Q1,Q2 after REACH must be constant for each reach'
                        break
            if  bmeshconstant:
                lunitall.append(lunit)
            else:
                if nbunit!=1:
                    msg = ' in case of variable mesh for each reach only one single unit per description is allowed !'
                    break
                if reachnumber == 1:
                    nbunitforall+=1
                    if len(lunitall)==1:
                        del lunitall[0]
                else:
                    nbunitforallvaryingmesh+=1
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
                if j==0:
                    bfvm = True
                else:
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
                        if  ls[k][1].lower() == 'u' and ls[k + 1][1].lower() == 'u':
                            if len(ls)!=5:
                                msg = ' detecting Varying Mesh but not the right number of information'
                                break
                            if bmeshconstant and nbunit!=1:  # or reachnumber!=1)
                                msg = ' detecting Varying Mesh but the number of unit in this case must be given one by one'
                                break
                            bmeshconstant=False
                        elif int(ls[k][1:]) != ik or int(ls[k + 1][1:]) != ik:
                            msg = ' information number after h or v not found'
                            break
                        else:
                            if not bmeshconstant:
                                msg = ' detecting Varying Mesh but not always'
                                break
            kk = 6
        elif ls[0].upper() == 'TIN':
            kk = 7
        elif ls[0].upper() == 'FVM':
            kk=70
            if not bfvm:
                msg = ' finite volume method not described properly you need to give only x y z for the nodes and velocity and depth for the mesh centers'
                break
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
                if not bsub:
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
            lunitvaryingmesh.append(float(ls[0]))
        elif kk == 6:
            if len(ls) != 3 + 2 * nbunit and (bfvm and len(ls)!= 3):
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
        elif kk == 70:
            if len(ls)  != 2*nbunit:
                msg = 'number of informations h v != nbunits'
                break
            ik = 0
            for k in range(0, len(ls), 2):
                ik += 1
                if ls[k].lower() != 'h' + str(ik) or ls[k + 1].lower() != 'v' + str(ik):
                    msg = ' information h' + str(ik) + ' or v' + str(ik) + ' not found'
                    break
            kk = 71
        elif kk == 71:
            if len(ls) != 2 * nbunit:
                msg = 'number of informations h v != nbunits'
                break
            tinfvm += 1
            ffvm.write(ligne)
        elif kk == 9:
            if len(ls) != nbsubinfo:
                msg = 'number of integer given for substrate not correct'
                break
            tinfsub += 1
            fsub.write(ligne)

    if not bmeshconstant:
        lunitall.append(lunitvaryingmesh)
        if reachnumber > 1 and nbunitforall != nbunitforallvaryingmesh:
            msg = ' varying mesh  an number of unit per reach not constant'
    if msg != '':
        fi.close();
        fnode.close();
        ftin.close()
        ffvm.close()
        os.remove(fnoden);
        os.remove(ftinn)
        os.remove(ffvmn)
        if bsub:
            fsub.close();
            os.remove(fsubn)
        print('Error: ligne : '+ str(i)+ ' {'+ ligne.rstrip() +' }'+ msg)
        return False,False

    lnode.append((nodei, nodef))
    ltin.append((tini, tinf))
    fi.close()
    fnode.close()
    ftin.close()
    ffvm.close()
    nodesall = np.loadtxt(fnoden, dtype=float)
    ikleall = np.loadtxt(ftinn, dtype=int)
    if bfvm:
        hvmesh=  np.loadtxt(ffvmn, dtype=float)
        if hvmesh.shape[0]!=ikleall.shape[0]:
            print('Error : the total number of meshes from TIN is not equal to FVM')
            return False, False

    os.remove(fnoden)
    os.remove(ftinn)
    os.remove(ffvmn)
    if bfvm:
        # calculating the coordinates of the mesh centers (triangle or quadrangle] from the nodes :xyzmesh34
        # xyzmesh=np.empty([ikleall.shape[0],3],np.float64 )
        # ikle3 = ikleall[np.where(ikleall[:, [3]] == -1)[0]]
        # ikle4 = ikleall[np.where(ikleall[:, [3]] != -1)[0]]
        nbmesh=ikleall.shape[0]
        hmesh = np.empty([nbmesh,nbunit], dtype=np.float64)
        vmesh=np.empty([nbmesh,nbunit], dtype=np.float64)
        for u in range(nbunit):
            hmesh[:,[u]]=hvmesh[:,[2*u]]
            vmesh[:, [u]] = hvmesh[:, [2 * u+1]]
        ikle2, nodes2,hnodes2,vnodes2=manage_grid_mod.finite_volume_to_finite_element_triangularxy(ikleall,nodesall,hmesh,vmesh)







    else:
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
            print('Error: ' +'the number of elements given for TIN  and SUBSTRATE description are different')
            return False,False
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
            print('Error: '+ msg)
            return False,False

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
        if bmeshconstant:
            nodes = np.array(nodesall[lnode[reach_num][0]:lnode[reach_num][1], :])
            ikle = np.array(ikleall[ltin[reach_num][0]:ltin[reach_num][1], :])
            if bsub:
                sub = np.array(suball[ltin[reach_num][0]:ltin[reach_num][1], :])
            nbnodes = len(nodes)
            if ikle.max() != nbnodes - 1:
                print('Error:' +' REACH :'+ lreachname[reach_num]+ "max(ikle)!= nbnodes TIN and Nodes number doesn't fit ")
                return False,False
            ikle, nodes, sub=reduce_quadrangles_to_triangles(ikle, nodes,nbunit, bsub, sub)
            for unit_num in range(nbunit):
                data_2d["tin"][reach_num].append(ikle)
                data_2d["i_whole_profile"][reach_num].append(ikle)
                if bsub:
                    data_2d["sub"][reach_num].append(sub)
                data_2d["xy"][reach_num].append(nodes[:, :2])
                data_2d["h"][reach_num].append(nodes[:, 2 + unit_num * 2 + 1])
                data_2d["v"][reach_num].append(nodes[:, 2 + unit_num * 2 + 2])
                data_2d["z"][reach_num].append(nodes[:, 2])
        else:
            for unit_num in range(nbunitforall):
                ilnode=reach_num*nbunitforall+unit_num
                nodes = np.array(nodesall[lnode[ilnode][0]:lnode[ilnode][1], :])
                ikle = np.array(ikleall[ltin[ilnode][0]:ltin[ilnode][1], :])
                if bsub:
                    sub = np.array(suball[ltin[ilnode][0]:ltin[ilnode][1], :])
                nbnodes = len(nodes)
                if ikle.max() != nbnodes - 1:
                    print('Error:' +' REACH :'+ lreachname[reach_num]+ "max(ikle)!= nbnodes TIN and Nodes number doesn't fit ")
                    return False,False
                ikle, nodes, sub=reduce_quadrangles_to_triangles(ikle, nodes,1, bsub, sub)
                data_2d["tin"][reach_num].append(ikle)
                data_2d["i_whole_profile"][reach_num].append(ikle)
                if bsub:
                    data_2d["sub"][reach_num].append(sub)
                data_2d["xy"][reach_num].append(nodes[:, :2])
                data_2d["h"][reach_num].append(nodes[:, 3])
                data_2d["v"][reach_num].append(nodes[:, 4])
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
    data_description["varying_mesh"] = not bmeshconstant
    if unit_type.upper()[0] == 'Q':
        data_description["flow_type"] = "continuous flow"
    else:
        data_description["flow_type"] = "transient flow"
    if bsub:
        data_description["sub_mapping_method"] = "polygon"
        data_description["sub_classification_method"] = sub_classification_method  # "coarser-dominant" / "percentage"
        data_description["sub_classification_code"] = sub_classification_code  # "Cemagref" / "Sandre"

    return data_2d, data_description


def reduce_quadrangles_to_triangles(ikle,nodes,nbunit,bsub,sub):
    """
    transforming   a set of triangles and 4angles into only triangles
    :param ikle:  a numpy array of four column describing the geometry of the quadrangles
    each line indicate the nodes index of the point describing the 4angles (for triangle last index=-1)
    :param nodes:  a numpy array x,y,z,h,v,..h,v..h,v
    :param nbunit:  the number of pair of  column height of water (h) velocity (v)  in the nodes numpy array
    :param bsub: a boolean True if the substrate description is available
    :param sub: a numpy array of at least 2 information for the coarser and dominant substrate classes
    :return:
    """

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
    return ikle,nodes,sub


def get_ascii_model_description(file_path):
    """
    using a text file description of hydraulic outputs from a 2 D model (with or without substrate description)
    several reaches and units (discharges or times )descriptions are allowed

    WARNING this function is parallel with  load_ascii_model function and some integrity tests are similar
    :param file_path:
    :return: the reachname list and the unit description (times or discharges)
    """
    # file exist ?
    if not os.path.isfile(file_path):
        return 'Error: The ascci text file does not exist. Cannot be loaded.'
    kk, reachnumber = 0, 0
    msg, unit_type = '', ''
    lunitall = []   # a list of  [list of Q or t] one element if all the Q or t are similar for all reaches
                    # or nbreaches elements
    epsgcode = ''
    bq_per_reach = False
    bsub,bmeshconstant =False,True
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
                lunit = []
                kk = 3
            elif ls[0].upper() == 'REACH':
                if kk != 2 and kk != 3 and kk < 7:
                    msg = ls[0] + ' but not EPSG  or Q[XXX or t[XXX before'
                    break
                if bq_per_reach and kk == 3:
                    msg = ls[0] + ' This structure REACH unit description is forbiden '
                    break
                reachnumber += 1
                bmeshconstant=True
                if reachnumber == 1:
                    lreachname = [('_'.join(ls[1:]))]
                else:
                    if '_'.join(ls[1:])== lreachname[-1]:
                        reachnumber -= 1
                        bmeshconstant = False
                    else:
                        lreachname.append(('_'.join(ls[1:])))
                kk = 4
            # .................
            elif ls[0].upper() == 'NODES':
                if kk != 3 and kk != 4:
                    msg = ls[0] + ' but not REACH or Units description (Q[XXX ,Q1,Q2.. or t[XXX,t1,t2  before'
                    break
                if bmeshconstant or len(lunit)==0:
                    lunitall.append(lunit)
                else:
                    lunitall[-1].extend(lunit)
                kk = 5
            elif ls[0].upper() == 'TIN':
                kk = 7
            elif ls[0].upper() == 'SUBSTRATE':
                bsub=True
            elif kk == 3:
                if len(ls) != 1:
                    msg = 'unit description but not only one information'
                    break
                lunit.append(ls[0])

        if msg != '':
            return 'Error: ligne : '+ str(i)+ ' {'+ ligne.rstrip() +' }'+ msg

    # create dict
    ascii_description = dict(epsg_code=epsgcode,
                             unit_type=unit_type,
                             unit_list=lunitall,
                             reach_number=reachnumber,
                             reach_list=lreachname,
                             sub=bsub)

    return ascii_description
