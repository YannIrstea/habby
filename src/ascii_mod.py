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
from copy import deepcopy
import numpy as np

from src import hdf5_mod
from src import manage_grid_mod
from src import mesh_management_mod
from src.tools_mod import isstranumber, create_empty_data_2d_dict, create_empty_data_2d_whole_profile_dict
from src.project_properties_mod import create_default_project_properties_dict
from src.variable_unit_mod import HydraulicVariableUnitManagement
from src.hydraulic_results_manager_mod import HydraulicSimulationResultsBase


class HydraulicSimulationResults(HydraulicSimulationResultsBase):
    """
    """
    def __init__(self, filename, folder_path, model_type, path_prj):
        super().__init__(filename, folder_path, model_type, path_prj)
        # HydraulicVariableUnit
        self.hvum = HydraulicVariableUnitManagement()
        # file attributes
        self.extensions_list = [".txt"]
        self.file_type = "ascii"
        # simulation attributes
        self.equation_type = ""  # FE or FV
        # reach
        self.multi_reach = False
        self.reach_num = 1
        self.reach_name_list = ["unknown"]
        self.morphology_available = True
        # # readable file ?
        # try:
        #     self.results_data_file = Selafin(self.filename_path)
        # except OSError:
        #     self.warning_list.append("Error: The file can not be opened.")
        #     self.valid_file = False

        # is extension ok ?
        if os.path.splitext(self.filename)[1] not in self.extensions_list:
            self.warning_list.append("Error: The extension of file is not : " + ", ".join(self.extensions_list) + ".")
            self.valid_file = False

        # if valid get informations
        if self.valid_file:
            self.get_ascii_model_description()
        else:
            self.warning_list.append("Error: File not valid.")

    def get_ascii_model_description(self):
        """
        using a text file description of hydraulic outputs from a 2 D model (with or without substrate description)
        several reaches and units (discharges or times )descriptions are allowed

        WARNING this function is parallel with  load_ascii_model function and some integrity tests are similar
        :param file_path:
        :return: the reachname list and the unit description (times or discharges)
        """
        kk, self.reach_num = 0, 0
        msg, unit_type = '', ''
        lunitall = []  # a list of  [list of Q or t] one element if all the Q or t are similar for all reaches
        # or nbreaches elements
        epsgcode = ''

        bfvm=False # a boolean to indicate whether  we have a finite element model or a finite volume model
        hyd_var_name_list=[] #list of hydraulic variables names
        hyd_var_unit_list = [] #list of hydraulic variables units

        bq_per_reach = False
        bsub, bmeshconstant = False, True
        with open(self.filename_path, 'r', encoding='utf8') as fi:
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
                            if bq_per_reach == False and self.reach_num != 1:
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
                    self.reach_num += 1
                    bmeshconstant = True
                    if self.reach_num == 1:
                        lreachname = [('_'.join(ls[1:]))]
                    else:
                        if '_'.join(ls[1:]) == lreachname[-1]:
                            self.reach_num -= 1
                            bmeshconstant = False
                        else:
                            lreachname.append(('_'.join(ls[1:])))
                    kk = 4
                # .................
                elif ls[0].upper() == 'NODES':
                    l1,l2=[],[]
                    if len(ls)>1:
                        for j in range(1,len(ls)):
                            t1,t2 =ls[j].find('['),ls[j].find(']')
                            if t1==-1 or t2==-1:
                                msg = ' finite volume method not described properly you need to give hydraulic variables with their units describe between [ ]'
                                break
                            l1.append(ls[j][:t1])
                            l2.append(ls[j][t1+1:t2])
                        msg2,hyd_var_name_list,hyd_var_unit_list=check_var_name_unit_lists(l1,l2,hyd_var_name_list,hyd_var_unit_list)
                        if msg2 != '':
                            msg = msg2
                            break



                    if kk != 3 and kk != 4:
                        msg = ls[0] + ' but not REACH or Units description (Q[XXX ,Q1,Q2.. or t[XXX,t1,t2  before'
                        break
                    if bmeshconstant or len(lunit) == 0:
                        lunitall.append(lunit)
                    else:
                        lunitall[-1].extend(lunit)
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
                        if j == 0:
                            bfvm = True
                    kk = 6
                elif ls[0].upper() == 'TIN':
                    kk = 7
                elif ls[0].upper() == 'FVM':
                    kk = 70
                    if not bfvm:
                        msg = ' finite volume method not described properly you need to give only x y z for the nodes and velocity and depth for the mesh centers'
                        break
                    l1, l2 = [], []
                    if len(ls) > 1:
                        for j in range(1, len(ls)):
                            t1, t2 = ls[j].find('['), ls[j].find(']')
                            if t1 == -1 or t2 == -1:
                                msg = ' finite volume method not described properly you need to give hydraulic variables with their units describe between [ ]'
                                break
                            l1.append(ls[j][:t1])
                            l2.append(ls[j][t1 + 1:t2])
                        msg2, hyd_var_name_list, hyd_var_unit_list = check_var_name_unit_lists(l1, l2,
                                                                                               hyd_var_name_list,
                                                                                               hyd_var_unit_list)
                        if msg2 != '':
                            msg = msg2
                            break
                elif ls[0].upper() == 'SUBSTRATE':
                    bsub = True
                elif kk == 3:
                    if len(ls) != 1:
                        msg = 'unit description but not only one information'
                        break
                    lunit.append(ls[0])
            if len(hyd_var_name_list) == 0 and len(hyd_var_unit_list) == 0:
                msg='the descriptions for hydraulic variable and their units  is not given'
            if msg != '':
                print('Error: ligne : ' + str(i) + ' {' + ligne.rstrip() + ' }' + msg)

        self.timestep_name_list = list(map(str, lunitall))
        self.timestep_nb = len(self.timestep_name_list[0])
        self.timestep_unit = unit_type

        # data_description
        if bfvm:
            self.equation_type = "FV"
        else:
            self.equation_type = "FE"
        if bsub:
            self.sub = True
        self.reach_name_list = lreachname
        self.reach_num = len(self.reach_name_list)
        if self.reach_num > 1:
            self.multi_reach = True
        self.varying_mesh = not bmeshconstant
        if unit_type.upper()[0] == 'Q':
            self.flow_type = "continuous flow"
        else:
            self.flow_type = "transient flow"

        # check witch variable is available
        variable_list = ["z"]
        self.hvum.detect_variable_from_software_attribute(variable_list)

    def load_hydraulic(self, timestep_name_wish_list):
        """
        """
        self.load_specific_timestep(timestep_name_wish_list)

        # prepare original data for data_2d
        for reach_num in range(self.reach_num):  # for each reach
            for timestep_index in self.timestep_name_wish_list_index:  # for each timestep
                val_all = self.results_data_file.getvalues(timestep_index)
                for variables_wish in self.hvum.software_detected_list:  # .varunits
                    if not variables_wish.precomputable_tohdf5:
                        variables_wish.data[reach_num].append(val_all[:, variables_wish.varname_index].astype(variables_wish.dtype))

                # struct
                self.hvum.xy.data[reach_num] = [np.array([self.results_data_file.meshx, self.results_data_file.meshy]).T] * self.timestep_wish_nb
                self.hvum.tin.data[reach_num] = [self.results_data_file.ikle2.astype(np.int64)] * self.timestep_wish_nb

        # prepare computable data for data_2d
        if self.hvum.v.precomputable_tohdf5:  # compute v for hdf5 ?
            for reach_num in range(self.reach_num):  # for each reach
                for timestep_index in range(len(self.timestep_name_wish_list_index)):
                    # compute from v_x v_y
                    self.hvum.hdf5_and_computable_list.get_from_name(self.hvum.v.name).data[reach_num].append(np.sqrt(self.hvum.hdf5_and_computable_list.get_from_name(self.hvum.v_x.name).data[reach_num][timestep_index] ** 2 + self.hvum.hdf5_and_computable_list.get_from_name(self.hvum.v_y.name).data[reach_num][timestep_index] ** 2))
                    self.hvum.hdf5_and_computable_list.get_from_name(self.hvum.v.name).position = "node"

        return self.get_data_2d()


def check_var_name_unit_lists(l1,l2,hyd_var_name_list,hyd_var_unit_list):
    msg2=''
    if not(l1 == hyd_var_name_list and l2==hyd_var_unit_list):
        if len(hyd_var_name_list)==0 and len(hyd_var_unit_list)==0:
            hyd_var_name_list, hyd_var_unit_list= list(l1),list(l2)
        else:
            msg2='the descriptions given for hydraulic variable and their units are not strictly identical'
    return msg2,hyd_var_name_list,hyd_var_unit_list


def load_ascii_model(filename, path_prj, user_pref_temp_path):
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
    fnoden, ftinn, fsubn, ffvmn = os.path.join(user_pref_temp_path, 'wwnode.txt'), os.path.join(
        user_pref_temp_path, 'wwtin.txt'), os.path.join(user_pref_temp_path,
                                                               'wwsub.txt'), os.path.join(user_pref_temp_path,
                                                                                          'wwfvm.txt')
    fi = open(filename, 'r', encoding='utf8')
    fnode = open(fnoden, 'w', encoding='utf8')
    ftin = open(ftinn, 'w', encoding='utf8')
    ffvm = open(ffvmn, 'w', encoding='utf8')
    kk, reachnumber, nbunitforall, nbunitforallvaryingmesh, nbreachsub = 0, 0, 0, 0, 0
    msg, unit_type, sub = '', '', ''
    lunitvaryingmesh = []
    lunitall = []  # a list of  [list of Q or t] per reach
    bq_per_reach, bsub, bmeshconstant, bfvm = False, False, True, False
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
                nodei, nodef, tini, tinf, tinfsub, tinfvm = 0, 0, 0, 0, 0, 0
                lnode = []
                ltin = []
            else:
                if '_'.join(ls[1:]) == lreachname[-1]:
                    if bmeshconstant:
                        msg = ' Structure whith reach description not truly available with variable mesh for each unit'
                        break
                    reachnumber -= 1
                    bmeshconstant = False
                else:
                    if not bmeshconstant:
                        lunitall.append(lunitvaryingmesh)
                        lunitvaryingmesh = []
                    lreachname.append(('_'.join(ls[1:])))
                    if reachnumber > 2 and nbunitforall != nbunitforallvaryingmesh:
                        msg = ' varying mesh  an number of unit per reach not constant'
                        break
                    nbunitforallvaryingmesh = 0
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
            if bmeshconstant:
                lunitall.append(lunit)
            else:
                if nbunit != 1:
                    msg = ' in case of variable mesh for each reach only one single unit per description is allowed !'
                    break
                if reachnumber == 1:
                    nbunitforall += 1
                    if len(lunitall) == 1:
                        del lunitall[0]
                else:
                    nbunitforallvaryingmesh += 1
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
                if j == 0:
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
                        if ls[k][1].lower() == 'u' and ls[k + 1][1].lower() == 'u':
                            if len(ls) != 5:
                                msg = ' detecting Varying Mesh but not the right number of information'
                                break
                            if bmeshconstant and nbunit != 1:  # or reachnumber!=1)
                                msg = ' detecting Varying Mesh but the number of unit in this case must be given one by one'
                                break
                            bmeshconstant = False
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
            kk = 70
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
            if len(ls) != 3 + 2 * nbunit and (bfvm and len(ls) != 3):
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
            if len(ls) != 2 * nbunit:
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
        fi.close()
        fnode.close()
        ftin.close()
        ffvm.close()
        os.remove(fnoden)
        os.remove(ftinn)
        os.remove(ffvmn)
        if bsub:
            fsub.close()
            os.remove(fsubn)
        print('Error: ligne : ' + str(i) + ' {' + ligne.rstrip() + ' }' + msg)
        return False, False

    lnode.append((nodei, nodef))
    ltin.append((tini, tinf))
    fi.close()
    fnode.close()
    ftin.close()
    ffvm.close()
    nodesall = np.loadtxt(fnoden, dtype=float)
    ikleall = np.loadtxt(ftinn, dtype=int)
    if bfvm:
        hvmesh = np.loadtxt(ffvmn, dtype=float)
        if hvmesh.shape[0] != ikleall.shape[0] and not hvmesh.ndim == 1:
            print('Error : the total number of meshes from TIN is not equal to FVM')
            return False, False

    os.remove(fnoden)
    os.remove(ftinn)
    os.remove(ffvmn)
    if bfvm:
        nbmesh = ikleall.shape[0]
        hmesh = np.empty([nbmesh, nbunit], dtype=np.float64)
        vmesh = np.empty([nbmesh, nbunit], dtype=np.float64)
        if hvmesh.ndim == 1:  # only one mesh
            for u in range(nbunit):
                hmesh[u] = hvmesh[2 * u]
                vmesh[u] = hvmesh[2 * u + 1]
        else:
            for u in range(nbunit):
                hmesh[:, [u]] = hvmesh[:, [2 * u]]
                vmesh[:, [u]] = hvmesh[:, [2 * u + 1]]
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
            print('Error: ' + 'the number of elements given for TIN  and SUBSTRATE description are different')
            return False, False
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
            print('Error: ' + msg)
            return False, False

    if bsub:
        data_2d = create_empty_data_2d_dict(reachnumber,
                                            mesh_variables=["sub"],
                                            node_variables=["h", "v"])
    else:
        data_2d = create_empty_data_2d_dict(reachnumber,
                                            node_variables=["h", "v"])

    for reach_num in range(reachnumber):
        if bmeshconstant:
            nodes = np.array(nodesall[lnode[reach_num][0]:lnode[reach_num][1], :])
            if ikleall.ndim == 1:  # if we only got one mesh and one unit
                ikleall = ikleall.reshape(1, ikleall.shape[0])
            ikle = np.array(ikleall[ltin[reach_num][0]:ltin[reach_num][1], :])
            if bsub:
                sub = np.array(suball[ltin[reach_num][0]:ltin[reach_num][1], :])
            nbnodes = len(nodes)
            if ikle.max() != nbnodes - 1:
                print('Error:' + ' REACH :' + lreachname[
                    reach_num] + "max(ikle)!= nbnodes TIN and Nodes number doesn't fit ")
                return False, False
            if bfvm:
                hmeshr = np.array(hmesh[ltin[reach_num][0]:ltin[reach_num][1], :])
                vmeshr = np.array(vmesh[ltin[reach_num][0]:ltin[reach_num][1], :])
                if bsub:
                    ikle2, nodes2, hnodes2, vnodes2, sub = manage_grid_mod.finite_volume_to_finite_element_triangularxy(
                        ikle, nodes, hmeshr, vmeshr, sub)
                else:
                    ikle2, nodes2, hnodes2, vnodes2 = manage_grid_mod.finite_volume_to_finite_element_triangularxy(ikle,
                                                                                                                   nodes,
                                                                                                                   hmeshr,
                                                                                                                   vmeshr)
                for unit_num in range(nbunit):
                    data_2d["mesh"]["tin"][reach_num].append(ikle2)
                    data_2d["mesh"]["i_whole_profile"][reach_num].append(ikle2)
                    if bsub:
                        data_2d["mesh"]["data"]["sub"][reach_num].append(sub)
                    data_2d["node"]["xy"][reach_num].append(nodes2[:, :2])
                    data_2d["node"]["z"][reach_num].append(nodes2[:, 2])
                    data_2d["node"]["data"]["h"][reach_num].append(hnodes2[:, unit_num])
                    data_2d["node"]["data"]["v"][reach_num].append(vnodes2[:, unit_num])
            else:
                ikle, nodes, sub = reduce_quadrangles_to_triangles(ikle, nodes, nbunit, bsub, sub)

                for unit_num in range(nbunit):
                    data_2d["mesh"]["tin"][reach_num].append(ikle)
                    data_2d["mesh"]["i_whole_profile"][reach_num].append(ikle)
                    if bsub:
                        data_2d["mesh"]["data"]["sub"][reach_num].append(sub)
                    data_2d["node"]["xy"][reach_num].append(nodes[:, :2])
                    data_2d["node"]["z"][reach_num].append(nodes[:, 2])
                    data_2d["node"]["data"]["h"][reach_num].append(nodes[:, 2 + unit_num * 2 + 1])
                    data_2d["node"]["data"]["v"][reach_num].append(nodes[:, 2 + unit_num * 2 + 2])
        else:
            for unit_num in range(nbunitforall):
                ilnode = reach_num * nbunitforall + unit_num
                nodes = np.array(nodesall[lnode[ilnode][0]:lnode[ilnode][1], :])
                ikle = np.array(ikleall[ltin[ilnode][0]:ltin[ilnode][1], :])
                if bsub:
                    sub = np.array(suball[ltin[ilnode][0]:ltin[ilnode][1], :])
                nbnodes = len(nodes)
                if ikle.max() != nbnodes - 1:
                    print('Error:' + ' REACH :' + lreachname[
                        reach_num] + "max(ikle)!= nbnodes TIN and Nodes number doesn't fit ")
                    return False, False
                ikle, nodes, sub = reduce_quadrangles_to_triangles(ikle, nodes, 1, bsub, sub)
                data_2d["mesh"]["tin"][reach_num].append(ikle)
                data_2d["mesh"]["i_whole_profile"][reach_num].append(ikle)
                if bsub:
                    data_2d["mesh"]["data"]["sub"][reach_num].append(sub)
                data_2d["node"]["xy"][reach_num].append(nodes[:, :2])
                data_2d["node"]["z"][reach_num].append(nodes[:, 2])
                data_2d["node"]["data"]["h"][reach_num].append(nodes[:, 3])
                data_2d["node"]["data"]["v"][reach_num].append(nodes[:, 4])

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
    if bfvm:
        data_description["hyd_equation_type"] = "FV"
    else:
        data_description["hyd_equation_type"] = "FE"
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


def reduce_quadrangles_to_triangles(ikle, nodes, nbunit, bsub, sub):
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
            manage_grid_mod.is_duplicates_mesh_and_point_on_one_unit(tin_array=ikle4,
                                                                     xyz_array=nodes[:, 0:2],
                                                                     unit_num=unit_num,
                                                                     case="before reduce quadrangles to triangles")
            # always obtain the sames ikle3new,xynew,znew only hnew,vnew are differents
            ikle3new, xynew, znew, hnew, vnew = \
                mesh_management_mod.quadrangles_to_triangles(ikle4, nodes[:, 0:2],
                                                             nodes[:, 2], nodes[:, 2 + unit_num * 2 + 1],
                                                             nodes[:, 2 + unit_num * 2 + 2])
            if unit_num == 0:
                newnodes = np.concatenate((xynew, znew, hnew, vnew), axis=1)
            else:
                newnodes = np.concatenate((newnodes, hnew, vnew), axis=1)

        ikle = np.append(ikle, ikle3new, axis=0)
        nodes = np.append(nodes, newnodes, axis=0)
        if bsub:
            for i in range(len(ikle4)):
                sub = np.append(sub, np.array([sub4[i, :], ] * 4), axis=0)
    return ikle, nodes, sub

