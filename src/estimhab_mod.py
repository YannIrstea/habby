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
import numpy as np
import xml.etree.ElementTree as ET
import os
from src import hdf5_mod
from src.translator_mod import get_translator


def estimhab_process(estimhab_dict, project_properties, path_prj, progress_value):
    qt_tr = get_translator(project_properties['path_prj'])

    # compute
    q_all, h_all, w_all, vel_all, VH, SPU, qtarg_dict = estimhab(estimhab_dict, qt_tr)

    # save in dict
    estimhab_dict["q_all"] = q_all
    estimhab_dict["h_all"] = h_all
    estimhab_dict["w_all"] = w_all
    estimhab_dict["vel_all"] = vel_all
    estimhab_dict["VH"] = VH
    estimhab_dict["SPU"] = SPU
    estimhab_dict["qtarg_dict"] = qtarg_dict

    # name hdf5
    name_prj = os.path.basename(path_prj)
    filename = name_prj + '_ESTIMHAB' + '.hab'

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(path_prj, filename, new=True)
    hdf5.create_hdf5_estimhab(estimhab_dict, project_properties)

    # load
    hdf5 = hdf5_mod.Hdf5Management(path_prj, filename, new=False)
    hdf5.load_hdf5_estimhab()

    # export
    hdf5.export_estimhab_txt()

    progress_value.value = 100.0


def estimhab(estimhab_dict, qt_tr):
    """
    This the function which forms the Estimhab model in HABBY. It is a reproduction in python of the excel file which
    forms the original Estimhab model.. Unit in meter amd m^3/sec

    :param qmes: the two measured discharge
    :param width: the two measured width
    :param height: the two measured height
    :param q50: the natural median discharge
    :param qrange: the range of discharge
    :param substrat: mean height of substrat
    :param path_im: the path where the image should be saved
    :param path_bio: the path to the xml file with the information on the fishes
    :param fish_xml: the name of the xml file to be analyzed
    :param pict: if true the figure is shown. If false, the figure is not shown
    :param project_properties: a dictionnary with the figure option
    :param path_txt: the path where to send the text data
    :param fish_name: the name fo the fish to be analysed (if not there, use the xml name)
    :return: habitat value and useful surface (VH and SPU) as a function of discharge

    **Technical comments and walk-through**

    First, we get all the discharges on which we want to calculate the SPU (surface ponderée utile),
    using the inputs from the user.

    Next we use hydrological rating curves (info on google if needed) to get the height and the width of the river for
    all discharge. The calculation is based on the width and height of the river measured at two discharges (given by the
    user).

    Next, we get other parameters which are used in the preference curves such as the froude_number number of
    the mean discharge or the Reynolds number.

    Next, we load the fish data contains in the xml files in the biology folder. Careful, this is not the xml project
    file. This are the xml files described above in the “Class EstimhabW” section. There are one xml file per fish and
    they described the preference curves. For the argumentation on the form of the relationship, report yourself to the
    documentation of Estimhab (one pdf file should in the folder “doc “ in HABBY).

    Then, we calculate the habitat values (VH and SPU). Finally, we plot the results in a figure and we save it as
    a text file.
    """
    estimhab_dict["qtarg"].sort()
    qmes = estimhab_dict["q"]
    width = estimhab_dict["w"]
    height = estimhab_dict["h"]
    q50 = estimhab_dict["q50"]
    qrange = estimhab_dict["qrange"]
    qtarg = estimhab_dict["qtarg"]
    substrat = estimhab_dict["substrate"]
    path_bio = estimhab_dict["path_bio"]
    fish_xml = estimhab_dict["xml_list"]
    fish_name = estimhab_dict["fish_list"]

    # Q
    nb_q = 100  # number of calculated q
    if qrange[1] > qrange[0]:
        if qrange[0] == 0:
            qrange[0] = 10 ** -10  # if exactly zero, you cannot divide anymore
        q_all = np.geomspace(start=qrange[0],
                            stop=qrange[1],
                            num=nb_q,
                             endpoint=True)
        if qtarg:
            q_all = np.insert(arr=q_all,
                      obj=np.searchsorted(a=q_all, v=qtarg),
                      values=qtarg)
    else:
        print('Error: ' + qt_tr.translate("estimhab_mod", 'The mininum discharge is higher or equal than the maximum.'))
        return [-99], [-99], [-99], [-99], [-99], [-99]

    # height
    slope = (np.log(height[1]) - np.log(height[0])) / (np.log(qmes[1]) - np.log(qmes[0]))
    exp_cte = np.exp(np.log(height[0]) - slope * np.log(qmes[0]))
    h_all = exp_cte * q_all ** slope
    h50 = exp_cte * q50 ** slope

    # width
    slope = (np.log(width[1]) - np.log(width[0])) / (np.log(qmes[1]) - np.log(qmes[0]))
    exp_cte = np.exp(np.log(width[0]) - slope * np.log(qmes[0]))
    w_all = exp_cte * q_all ** slope
    l50 = exp_cte * q50 ** slope

    # velocity
    vel = (q_all / h_all) / w_all
    v50 = (q50 / h50) / l50
    re = q_all / (10 * w_all)
    re50 = q50 / (10 * l50)

    # TODO: add column data : h_all, w_all, vel

    # extra-data related to q50
    fr50 = q50 / (9.81 ** 0.5 * h50 ** 1.5 * l50)
    dh50 = substrat / h50
    q50_data = [q50, h50, l50, v50, re50, fr50, dh50, np.exp(dh50)]

    # get fish data
    VH = []
    SPU = []
    for f in range(0, len(fish_xml)):
        # load xml file
        filename = os.path.join(path_bio, fish_xml[f])
        if os.path.isfile(filename):
            parser = ET.XMLParser()
            doc = ET.parse(filename, parser)
            root = doc.getroot()
        else:
            print('Error: ' + qt_tr.translate("estimhab_mod", 'The xml file for the file ') + filename +
                  qt_tr.translate("estimhab_mod", " does not exist."))
            return [-99], [-99], [-99], [-99], [-99], [-99]

        # get data
        try:
            coeff_q = pass_to_float_estimhab(".//coeff_q", root)
            func_q = pass_to_float_estimhab(".//func_q", root)
            coeff_const = pass_to_float_estimhab(".//coeff_const", root)
            var_const = pass_to_float_estimhab(".//var_const", root)
        except ValueError:
            print('Error: ' + qt_tr.translate("estimhab_mod",
                                              'Some data can not be read or are not number. Check the xml file of ') +
                  fish_name[f] + fish_xml[f])
            return [-99], [-99], [-99], [-99], [-99], [-99], [-99]

        # calculate VH
        if func_q[0] == 0.:
            part_q = re ** coeff_q[0] * np.exp(coeff_q[1] * re)
        elif func_q[0] == 1.:
            part_q = 1 + coeff_q[0] * np.exp(coeff_q[1] * re)
        else:
            print('Error: ' + qt_tr.translate("estimhab_mod",
                                              'No function defined for Q'))
        const = coeff_const[0]
        for i in range(0, len(var_const)):
            const += coeff_const[i + 1] * np.log(q50_data[int(var_const[i])])
        if const < 0:
            const = 0
        VH_f = const * part_q
        SPU_f = VH_f * w_all * 100

        VH.append(VH_f)
        SPU.append(SPU_f)

    VH = np.array(VH)
    SPU = np.array(SPU)

    # remove qtarget values to separate them
    qtarg_dict = dict(q_all=[],
                      h_all=[],
                      w_all=[],
                      vel_all=[],
                      VH=np.empty((SPU.shape[0], len(qtarg))),
                      SPU=np.empty((SPU.shape[0], len(qtarg))))
    if qtarg:
        for qtarg_indice, qtarg_value in enumerate(qtarg):
            indice = np.where(q_all == qtarg_value)[0][0]
            qtarg_dict["q_all"].append(q_all[indice])
            qtarg_dict["h_all"].append(h_all[indice])
            qtarg_dict["w_all"].append(w_all[indice])
            qtarg_dict["vel_all"].append(vel[indice])
            qtarg_dict["VH"][:, qtarg_indice] = VH[:, indice]
            qtarg_dict["SPU"][:, qtarg_indice] = SPU[:, indice]

    return q_all, h_all, w_all, vel, VH, SPU, qtarg_dict


def pass_to_float_estimhab(var_name, root):
    """
    This is a function to pass from an xml element to a float

    :param root: the root of the open xml file
    :param var_name: the name of the attribute in the xml file
    :return: the float data
    """
    coeff_qe = root.findall(var_name)
    coeff_str = coeff_qe[0].text
    if not coeff_str:
        coeff = []
    else:
        coeff = coeff_str.split()
        coeff = list(map(float, coeff))

    return coeff


def main():
    """
    Used to test this module.
    """

    # data from the estimahab2008.xls found in http://www.irstea.fr/en/estimhab
    q = [2, 60]
    w = [29, 45]
    h = [0.21, 1.12]
    q50 = 25
    qrange = [1, 38]
    substrat = 0.25
    fish = ['TRF_ADU', 'TRF_JUV', 'BAF', 'CHA', 'GOU']
    path = os.path.join('.', 'biology')

    [VH, SPU] = estimhab(q, w, h, q50, qrange, substrat, path, fish, True, True)


if __name__ == '__main__':
    main()
