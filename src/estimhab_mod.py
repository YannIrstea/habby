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
import time
from shutil import copy as sh_copy
from PyQt5.QtCore import QLocale

from src.dev_tools_mod import frange, txt_file_convert_dot_to_comma
from src.tools_mod import read_chronicle_from_text_file
from src.project_properties_mod import load_specific_properties


nbclaq =100  # number of discharge point where the data have to be calculate


def estimhab_process(project_properties, export=True, progress_value=None):
    # TODO: reactivate translation
    # load
    estimhab_dict = load_specific_properties(project_properties['path_prj'],
                                                      ["Estimhab"])[0]

    # compute
    q_all, h_all, w_all, vel_all, OSI, WUA = estimhab(estimhab_dict)

    # add in dict
    estimhab_dict["q_all"] = q_all
    estimhab_dict["h_all"] = h_all
    estimhab_dict["w_all"] = w_all
    estimhab_dict["vel_all"] = vel_all
    estimhab_dict["OSI"] = OSI
    estimhab_dict["WUA"] = WUA
    estimhab_dict["fish_list"] = read_fishname(estimhab_dict["xml_list"])

    # export
    if export:
        export_estimhab_txt(estimhab_dict, project_properties)

    if progress_value is not None:
        progress_value.value = 100

    return estimhab_dict


def estimhab(estimhab_dict):
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
    :return: habitat value and useful surface (OSI and WUA) as a function of discharge

    **Technical comments and walk-through**

    First, we get all the discharges on which we want to calculate the WUA (surface ponderée utile),
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

    Then, we calculate the habitat values (OSI and WUA). Finally, we plot the results in a figure and we save it as
    a text file.
    """
    qmes = estimhab_dict["q"]
    width = estimhab_dict["w"]
    height = estimhab_dict["h"]
    q50 = estimhab_dict["q50"]
    qrange = estimhab_dict["qrange"]
    substrat = estimhab_dict["substrate"]
    path_bio = estimhab_dict["path_bio"]
    fish_xml = estimhab_dict["xml_list"]
    fish_name = read_fishname(estimhab_dict["xml_list"])

    # Q
    # nb_q = 100  # number of calculated q
    # if qrange[1] > qrange[0]:
    #     if qrange[0] == 0:
    #         qrange[0] = 10 ** -10  # if exactly zero, you cannot divide anymore
    #     q_all = np.geomspace(start=qrange[0],
    #                         stop=qrange[1],
    #                         num=nb_q,
    #                          endpoint=True)
    # else:
    #     print('Error: ' + 'The mininum discharge is higher or equal than the maximum.')
    #     return [-99], [-99], [-99], [-99], [-99], [-99]

    if type(qrange) == str:  # chronicle
        chronicle_from_file, types_from_file = read_chronicle_from_text_file(qrange)
        q_all = chronicle_from_file["units"]
    else:  # seq
        # generate nbclaq values of discharges spaced evenly on a log scale
        q_all = np.geomspace(start=qrange[0], stop=qrange[1], num=nbclaq, endpoint=True)
        #q_all = np.array(list(frange(qrange[0], qrange[1], qrange[2])))  # from to by
        # np.exp(np.log(qrange[0] + (qind + 0.5) * (np.log(qrange[1] - np.log(qrange[0])) / nbclaq)))

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
    OSI = []
    WUA = []
    for f in range(0, len(fish_xml)):
        # load xml file
        filename = fish_xml[f]
        if os.path.isfile(filename):
            parser = ET.XMLParser()
            doc = ET.parse(filename, parser)
            root = doc.getroot()
        else:
            print('Error: The xml file for the file ' + filename + " does not exist.")
            return [-99], [-99], [-99], [-99], [-99], [-99]

        # get data
        try:
            coeff_q = pass_to_float_estimhab(".//coeff_q", root)
            func_q = pass_to_float_estimhab(".//func_q", root)
            coeff_const = pass_to_float_estimhab(".//coeff_const", root)
            var_const = pass_to_float_estimhab(".//var_const", root)
        except ValueError:
            print('Error: ' + 'Some data can not be read or are not number. Check the xml file of ' +
                  fish_name[f] + fish_xml[f])
            return [-99], [-99], [-99], [-99], [-99], [-99], [-99]

        # calculate OSI
        if func_q[0] == 0.:
            part_q = re ** coeff_q[0] * np.exp(coeff_q[1] * re)
        elif func_q[0] == 1.:
            part_q = 1 + coeff_q[0] * np.exp(coeff_q[1] * re)
        else:
            print('Error: ' + 'No function defined for Q')
        const = coeff_const[0]
        for i in range(0, len(var_const)):
            const += coeff_const[i + 1] * np.log(q50_data[int(var_const[i])])
        if const < 0:
            const = 0
        OSI_f = const * part_q
        WUA_f = OSI_f * w_all * 100

        OSI.append(OSI_f)
        WUA.append(WUA_f)

    OSI = np.array(OSI)
    WUA = np.array(WUA)

    return q_all, h_all, w_all, vel, OSI, WUA


def read_fishname(all_xmlfile):
    fish_names = []
    for f in all_xmlfile:
        # open xml
        try:
            try:
                docxml = ET.parse(f)
                root = docxml.getroot()
            except IOError:
                print("Warning: " + "The file " + f + " could not be open.\n")
                return
        except ET.ParseError:
            print("Warning: " + "The file " + f + " is not well-formed.\n")
            return

        # find fish name
        fish_name = root.find(".//LatinName")
        # None is null for python 3
        if fish_name is not None:
            fish_name = fish_name.text.strip()

        # find fish stage
        stage = root.find(".//estimhab/stage")
        # None is null for python 3
        if stage is not None:
            stage = stage.text.strip()
        if stage != 'all_stage':
            fish_name += ' ' + stage
        fish_names.append(fish_name)

    return fish_names

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


def export_estimhab_txt(estimhab_dict, project_properties):
    q_all = estimhab_dict["q_all"]
    h_all = estimhab_dict["h_all"]
    w_all = estimhab_dict["w_all"]
    vel_all = estimhab_dict["vel_all"]
    qmes = estimhab_dict["q"]
    width = estimhab_dict["w"]
    height = estimhab_dict["h"]
    q50 = estimhab_dict["q50"]
    substrat = estimhab_dict["substrate"]
    qrange = estimhab_dict["qrange"]
    OSI = estimhab_dict["OSI"]
    WUA = estimhab_dict["WUA"]
    fish_list = estimhab_dict["fish_list"]
    path_txt = project_properties["path_text"]
    path_input = project_properties["path_input"]
    output_filename = "Estimhab"
    intput_filename = "Estimhab_input"

    # header
    date_all = None
    txt_header = 'Discharge\tHeight\tWidth\tVelocity'
    if type(qrange) == str:  # chronicle
        chronicle_from_file, types_from_file = read_chronicle_from_text_file(qrange)
        if "date" in types_from_file.keys():
            txt_header = 'Date\tDischarge\tHeight\tWidth\tVelocity'
            date_all = chronicle_from_file["date"]

    # check if exist and erase
    if os.path.exists(os.path.join(path_txt, output_filename + '.txt')):
        if not project_properties["erase_id"]:
            output_filename = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")

    # prep data
    if date_all is None:
        all_data = np.vstack((q_all, h_all, w_all, vel_all))
    else:
        all_data = np.vstack((date_all, q_all, h_all, w_all, vel_all))

    for f in range(0, len(fish_list)):
        txt_header += '\tOSI_' + fish_list[f] + '\tWUA_' + fish_list[f]
        all_data = np.vstack((all_data, OSI[f]))
        all_data = np.vstack((all_data, WUA[f]))

    # headers
    if date_all is None:
        txt_header += '\n[m3/s]\t[m]\t[m]\t[m/s]'
    else:
        txt_header += '\n[]\t[m3/s]\t[m]\t[m]\t[m/s]'
    for f in range(0, len(fish_list)):
        txt_header += '\t[-]\t[m2/100m]'

    # export estimhab output
    try:
        np.savetxt(os.path.join(path_txt, output_filename + '.txt'),
                   all_data.T,
                   header=txt_header,
                   fmt="%s",
                   delimiter='\t')  # , newline=os.linesep
    except PermissionError:
        output_filename = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
        intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
        np.savetxt(os.path.join(path_txt, output_filename + '.txt'),
                   all_data.T,
                   header=txt_header,
                   fmt='%s',
                   delimiter='\t')  # , newline=os.linesep

    # change decimal point
    locale = QLocale()
    if locale.decimalPoint() == ",":
        txt_file_convert_dot_to_comma(os.path.join(path_txt, output_filename + '.txt'))

    # export estimhab input
    txtin = 'Discharge [m3/sec]:\t' + str(qmes[0]) + '\t' + str(qmes[1]) + '\n'
    txtin += 'Width [m]:\t' + str(width[0]) + '\t' + str(width[1]) + '\n'
    txtin += 'Height [m]:\t' + str(height[0]) + '\t' + str(height[1]) + '\n'
    txtin += 'Median discharge [m3/sec]:\t' + str(q50) + '\n'
    txtin += 'Mean substrate size [m]:\t' + str(substrat) + '\n'
    if type(qrange) == str:
        txtin += 'Chronicle discharge file path:\t' + qrange + '\n'
    else:
        txtin += 'Sequence from to [m3/sec]:\t' + str(qrange[0]) + '\t' + str(qrange[1]) + '\n'
    txtin += 'Fish chosen:\t'
    for n in fish_list:
        txtin += n + '\t'
    txtin = txtin[:-1]
    txtin += '\n'
    txtin += 'Output file:\t' + output_filename + '.txt\n'

    # create input_estimhab dir if not exist
    if not os.path.exists(os.path.join(path_input, "input_estimhab")):
        os.makedirs(os.path.join(path_input, "input_estimhab"))

    # write file
    try:
        with open(os.path.join(path_input, "input_estimhab", intput_filename + '.txt'), 'wt') as f:
            f.write(txtin)
    except PermissionError:
        intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
        with open(os.path.join(path_input, "input_estimhab", intput_filename + '.txt'), 'wt') as f:
            f.write(txtin)
    locale = QLocale()
    if locale.decimalPoint() == ",":
        txt_file_convert_dot_to_comma(os.path.join(path_input, "input_estimhab", intput_filename + '.txt'))

    # copy chronible file
    if type(qrange) == str:
        sh_copy(qrange, os.path.join(path_input, "input_estimhab", os.path.basename(qrange)))


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

    [OSI, WUA] = estimhab(q, w, h, q50, qrange, substrat, path, fish, True, True)


if __name__ == '__main__':
    main()
