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
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import sqlite3
import time
from datetime import datetime
from multiprocessing import Value

from src import hdf5_mod
from src import plot_mod
from src_GUI import preferences_GUI

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def load_evha_curve(filename, path):
    """
    This function is used to load the preference curve in the EVHA form .
    It will be useful to create xml preference
    file, but it is not used direclty by HABBY.
    This function does not have much control on user input as it is planned
    to be used only by people working on HABBY. The order of the data in the
    file must be height, velocity, substrate

    :param filename: the name of file containing the preference curve for EVHA
    :param path: the path to this file
    :return: preference for height, vel, sub in a list of list form, name
     of the fish, code, stade and description
    """

    # load text file
    filename_path = os.path.join(path, filename)
    with open(filename_path, 'rt') as f:
        data = f.read()

    # general info
    exp_reg1 = "\s*(\w\w\w?)\s+(.+)\n"
    re_res = re.findall(exp_reg1, data)[0]
    code_fish = re_res[0]
    name_fish = re_res[1]

    exp_reg2 = "\n(.+)\$(\d)(.+)"
    re_res = re.findall(exp_reg2, data, re.DOTALL)[0]
    descri = re_res[0]
    descri = descri.replace('\n\n\n', '\n')
    descri = descri.replace('\n\n', '\n')
    nb_stade = int(re_res[1])
    data_num = re_res[2]
    data_num = data_num.split('\n')

    # name of stade (ADU, JUV, etc)
    stade = data_num[0]
    stade = stade.strip()
    stade = stade.split()
    if len(stade) != nb_stade:
        print('Error: number of stade are not coherent')
        return

    # height, velocity, substrate
    height = []
    vel = []
    sub = []
    first_point = True
    data_num = data_num[1:]
    new_data1old = -1
    pref_here = []
    for s in range(0, nb_stade):
        ind_hvs = 0
        for l in range(0, len(data_num)):
            data_l = data_num[l]
            data_l = data_l.strip()
            data_l = data_l.split()
            if len(data_l) > 1:  # empty lines
                try:
                    new_data1 = np.float(data_l[2 * s])
                    new_data2 = np.float(data_l[2 * s + 1])
                except ValueError:
                    print('not a float')
                    return
                # pass from centimeter to meter
                if ind_hvs == 0 or ind_hvs == 1:
                    new_data1 /= 100  # this is just a division
                if new_data1old <= new_data1:
                    new_data1old = new_data1
                    if first_point:
                        pref_here = [[new_data1], [new_data2]]
                        first_point = False
                    else:
                        pref_here[0].extend([new_data1])
                        pref_here[1].extend([new_data2])
                else:  # go from height to velocity
                    if ind_hvs == 0:
                        height.append(pref_here)
                    if ind_hvs == 1:
                        vel.append(pref_here)
                    ind_hvs += 1
                    pref_here = [[], []]
                    first_point = True
                    new_data1old = -1
        # go from velcoity to substrate
        new_data1old = -1
        sub.append(pref_here)
        first_point = True
        pref_here = [[], []]

    return height, vel, sub, code_fish, name_fish, stade, descri


def test_evah_xml_pref(path_xml, path_evha):
    """
    This function is used to visually compared the evha (.PRF) curve and
     the xml curve based on the evah curve.
    Obviously the xml file should contain the same data than the evha curve
     (when the xml file are based on the evah curve). An important assumption
     of this function is that the data in the xml file is in the order: fry,
     juvenile, adult.

    :param path_xml: the path to the folder which contains the xml files
    :param path_evha: the path to the evha folder which contains the PRF files

    """

    # get filename evha
    filenames = hdf5_mod.get_all_filename(path_evha, '.PRF')
    filenames2 = hdf5_mod.get_all_filename(path_evha, '.prf')
    filenames.extend(filenames2)
    # load evha
    h_evha = []
    v_evha = []
    sub_evha = []
    code_fish_evha = []
    name_fish_evha = []
    stage_evha = []
    for i in range(0, len(filenames)):
        [height, vel, sub, code_fish, name_fish, stages, blob] = \
            load_evha_curve(filenames[i], path_evha)
        h_evha.append(height)
        v_evha.append(vel)
        sub_evha.append(sub)
        code_fish_evha.append(code_fish)
        name_fish_evha.append(name_fish)
        stage_evha.append(stages)

    # get filename xml
    filenames = hdf5_mod.get_all_filename(path_xml, '.xml')
    for i in range(0, len(filenames)):
        filename = os.path.join(path_xml, filenames[i])
        print(filename)
        [height, vel, sub, code_fish, name_fish, stages] = read_pref(filename)

        # find which fish data to use in evha
        j = 0
        for n in code_fish_evha:
            # some ONEMA code have changed between the years
            # the PRF use the old code, the xml file the new code
            if n == 'SAS':
                n = 'SAT'
            if n == 'Tox':
                n = 'TOX'
            if n == 'VAS':
                n = 'VAI'
            if n == 'OMB':
                n = 'OBR'
            if n == code_fish:
                break
            else:
                j += 1
        # last one
        if j > len(code_fish_evha) - 1:
            j = len(code_fish_evha) - 1

        # pass from stades in evha to stages in xml
        if len(stages) != len(stage_evha[j]):
            print('Error: the number of stages is not coherent\
             in evha and xml files \n')
            return
        # important assumption here: the data in the xml file is in the order:
        # fry, juvenile, adult
        # and the name are fry, juvenile, adult
        stage_corr_evha = []
        if len(stages) > 1:
            for s in stage_evha[j]:
                if s == 'FRA':
                    stage_corr_evha.append(0)
                elif s == 'ALE':
                    stage_corr_evha.append(1)
                elif s == 'JUV':
                    stage_corr_evha.append(2)
                elif s == 'ADU':
                    stage_corr_evha.append(3)
                else:
                    print('Warning: stages not found \n')
            # we might have less than four stages
            stage_corr_evha = np.array(stage_corr_evha) - min(stage_corr_evha)

        # plot xml
        fake_value = Value("i", 0)
        [f, axarr] = plot_mod.plot_suitability_curve(fake_value, height, vel, sub, code_fish, name_fish,
                                 stages, True)

        # plt evha data
        plt.suptitle('Comparision of preference curve of ' + code_fish
                     + '\n (xml as straight line, .PRF as triangle)')
        if len(stages) > 1:  # if you take this out, the commande axarr[x,x]
            # does not work as axarr is only 1D
            # f, axarr = plt.subplots(len(stage_evha[j]), 3, sharey='row')
            for s2 in range(0, len(stage_evha[j])):
                s = stage_corr_evha[s2]
                axarr[s, 0].plot(h_evha[j][s2][0], h_evha[j][s2][1], '^b')
                axarr[s, 1].plot(v_evha[j][s2][0], v_evha[j][s2][1], '^r')
                axarr[s, 2].plot(sub_evha[j][s2][0], sub_evha[j][s2][1], '^k')
        else:
            axarr[0].plot(h_evha[j][0][0], h_evha[j][0][1], '^b')
            axarr[1].plot(v_evha[j][0][0], v_evha[j][0][1], '^r')
            axarr[2].plot(sub_evha[j][0][0], sub_evha[j][0][1], '^k')
    plt.show()


def create_and_fill_database(path_bio, name_database, attribute):
    """
    This function create a new database when Habby starts.
    The goal of creating a database is to avoid freezing the GUI
    when info on the preference curve are asked. So it is possible to select
    one curve and have information without
    seeing too much of a delay.

    This is not used anymore by HABBY as the xml file is really small.
    It could however be useful if the xml file becomes too big.
    In this case, this function could be
    called if modification are found in the pref_file folder and would create
    a database.

    The attribute can be modified, but they should all be of text type.
    It is also important to keep stage at the first
    attribute. The modified attribute should reflect the attribute
    of the xml file. If it not possible, lines should
    be added in the "special case" attributes".
    The main table with the data is called pref_bio.

    :param path_bio: the path to the biological information (usually ./biology)
    :param name_database: the name of the database (string) without the path
    :param attribute: the attribute in the database (only text type)
    :return: a boolean (True if everthing ok, False otherwise)
    """

    # test first attribute
    if attribute[0] != 'Stage':
        print("Correct first attribute to 'Stage' in bio_info_Gui.py. \n")

    lob, ext = os.path.splitext(name_database)
    if ext != ".db":
        print('Warning: the name of the database should have\
                a .db extension \n')

    pathname_database = os.path.join(path_bio, name_database)

    # erase database (to be done at the beginning because rename database
    # at the end is annoying)
    if os.path.isfile(pathname_database):
        os.remove(pathname_database)

    # create database and table if not exist
    request_create = 'CREATE TABLE pref_bio(fish_id INTEGER PRIMARY KEY, '
    for a in attribute:
        request_create += a + ' text,'
    request_create = request_create[:-1]  # get rid of the last comma
    request_create += ')'

    conn = sqlite3.connect(pathname_database)
    cursor = conn.cursor()
    cursor.execute(request_create)
    conn.commit()
    conn.close()

    # preapre insertion into databse
    rea0 = "INSERT INTO pref_bio(fish_id, "
    for att in attribute:
        rea0 += att + ','
    rea0 = rea0[:-1]  # last comma
    rea0 += ") values("

    # get all xml name
    preffiles = hdf5_mod.get_all_filename(path_bio, '.xml')
    if len(preffiles) < 1:
        print('Error: no xml preference file found.\
                Please check the biology folder. \n')
        return

    # for all xml file
    found_one = False
    j = 0
    for preffile in preffiles:
        data = [None] * (len(attribute) - 1)

        # load the file
        try:
            try:
                docxml = ET.parse(os.path.join(path_bio, preffile))
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file " + preffile + " does not exist \n")
                break
        except ET.ParseError:
            print("Warning: the xml file " + preffile + "is not well-formed.\n")
            break

        # get the data
        i = -1
        for att in attribute:
            # special attribute
            if att == 'Stage':  # this should be the first attribute as i ==-1
                stages = root.findall(".//stage")
                if len(stages) == 0:
                    print('no stage found in ' + preffile + "\n")
                else:
                    stages = [s.attrib['type'] for s in stages]
            elif att == 'French_common_name':
                b = root.findall('.//comname')
                if b is not None:
                    for bi in b:
                        if bi.attrib['language'] == 'French':
                            data[i] = bi.text
            elif att == 'English_common_name':
                b = root.findall('.//comname')
                if b is not None:
                    for bi in b:
                        if bi.attrib['language'] == 'English':
                            data[i] = bi.text
            elif att == 'Code_ONEMA':
                org = root.find('.//OrgCdAlternative')
                if org is not None:
                    if org.text == 'ONEMA':
                        data[i] = root.find('.//CdAlternative')
                        if data[i] is not None:
                            data[i] = data[i].text
            elif att == 'Code_Sandre':
                data[i] = \
                    root.find('.//CdAppelTaxon[@schemeAgencyID="SANDRE"]')
                if data[i] is not None:
                    data[i] = data[i].text
            elif att == 'XML_filename':
                data[i] = preffile
            elif att == 'XML_data':
                data[i] = ET.tostring(root).decode()
                if data[i] is None:
                    print('No xml data found for a file \n')
                    break
            elif att == 'creation_year':
                data[i] = root.find('.//creation-year')
                if data[i] is not None:
                    data[i] = data[i].text

            # normal attributes
            # the tag figure_hydrosignature is None (Null) by default
            else:
                data[i] = root.find(".//" + att)
                # None is null for python 3
                if data[i] is not None:
                    data[i] = data[i].text
            i += 1

        # fill the database
        if stages is None or len(stages) == 0:
            break
        else:
            for s in stages:
                rea = rea0
                rea += "'" + str(j) + "', "  # the primary key
                rea += "'" + str(s) + "', "  # the stage
                for d in data:
                    if d is not None:
                        d = d.replace("'", " ")
                        rea += "'" + str(d) + "', "
                    else:
                        rea += "NULL,"
                rea = rea[:-2]
                rea += ")"
                conn = sqlite3.connect(pathname_database)
                cursor = conn.cursor()
                cursor.execute(rea)
                conn.commit()
                conn.close()
                j += 1

        found_one = True

    if not found_one:
        print('Error: No preference file could be read.\
            Please check the biology folder.\n')


def get_biomodels_informations_for_database(path_xml):
    # open the file
    try:
        try:
            docxml = ET.parse(path_xml)
            root = docxml.getroot()
        except IOError:
            print("Warning: the xml file does not exist \n")
            return
    except ET.ParseError:
        print("Warning: the xml file is not well-formed.\n")
        return

    # stage_and_size
    stage_and_size = [stage.attrib['Type'] for stage in root.findall(".//Stage")]
    # ModelType
    ModelType = [model.attrib['Type'] for model in root.findall(".//ModelType")][0]
    # MadeBy
    MadeBy = root.find('.//MadeBy').text
    # CdAlternative
    CdAlternative = root.find('.//CdAlternative').text
    # LatinName
    LatinName = root.find(".//LatinName").text
    # modification_date
    modification_date = str(datetime.fromtimestamp(os.path.getmtime(path_xml)))[:-7]
    # to dict
    information_model_dict = dict(stage_and_size=stage_and_size,
                                  ModelType=ModelType,
                                  MadeBy=MadeBy,
                                  CdAlternative=CdAlternative,
                                  LatinName=LatinName,
                                  modification_date=modification_date)

    return information_model_dict


def execute_request(path_bio, name_database, request):
    """
    This function execute the SQL request given in the string called request.
    it saves the found data in a variable.
    The idea is to use this function for SELELCT X FROM X WHERE ... ,
    not really to handle all possible request.
    It also opens and close the database name_database to do this.
    This is not used anymore by HABBY as we do not use
    a database. It could however be useful if the xml file becomes too big.

    :param path_bio: the path to the biological information (usually ./biology)
    :param name_database: the name of the database (string) without the path
    :param request: the SQL request in a string form
    :return: the result
    """

    blob, ext = os.path.splitext(name_database)
    if ext != ".db":
        print('Warning:\
            the name of the database should have a .db extension \n')
    pathname_database = os.path.join(path_bio, name_database)

    if os.path.isfile(pathname_database):
        conn = sqlite3.connect(pathname_database)
        cursor = conn.cursor()
        cursor.execute(request)
        res = cursor.fetchall()
        conn.close()
    else:
        print('Error: Database not found.\n')
        return

    return res


def load_xml_name(path_bio, attributes, preffiles=[]):
    """
    This function looks for all preference curves found in the path_bio folder.
    It extract the fish name and the stage.
    to be corrected if more than one language. The name of attribute_acc
    should be coherent with the one from the xml
    file apart from the common name which should be in
    the form language_common_name (so we can wirte something in the
    GUI to get all langugage if we get something else than English or French).

    If one use the argument preffiles, only part of the xml file are loaded.
    Otherwise all xml file are loaded.

    Careful, the first attribute is relgated at the last place of
    the list return. This is confusing but it is really
    useful for the GUI.

    :param path_bio: the path to the biological function
    :param attributes: the list of attribute which should be possible to search
        from the GUI or, more generally
        which should be in data-fish which is returned.
    :param preffiles: If there is a list of string there,
        it only read this files
    :return: the list of stage/fish species with the info from [name for GUi,
        s, xmlfilename, attribute_acc without s]
    """
    stages = []

    if not preffiles:
        # get all xml name
        preffiles = hdf5_mod.get_all_filename(path_bio, '.xml')
        if len(preffiles) < 1:
            print('Error: no xml preference file found.\
                Please check the biology folder. \n')
            return

    # for all xml file
    found_one = False

    data_fish = []
    for preffile in preffiles:
        data = [None] * len(attributes)
        # load the file
        try:
            try:
                docxml = ET.parse(os.path.join(path_bio, preffile))
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file " + preffile
                      + " does not exist \n")
                break
        except ET.ParseError:
            print("Warning: the xml file " + preffile
                  + " is not well-formed.\n")
            break

        i = -1
        all_ok = True
        for att in attributes:
            att_langue = att.split('_')
            # special attribute
            if att == 'Stage':  # this should be the first attribute as i ==-1
                stages = root.findall(".//Stage")
                if len(stages) == 0:
                    print('no stage found in ' + preffile + "\n")
                    all_ok = False
                    break
                else:
                    try:
                        stages = [s.attrib['Type'] for s in stages]
                    except KeyError:
                        print('no stage found in ' + preffile + "\n")
                        all_ok = False
                        break
            elif len(att_langue) == 3 and att_langue[1] == 'common' and \
                    att_langue[2] == 'name':
                b = root.findall('.//ComName')
                if b is not None:
                    for bi in b:
                        try:
                            if bi.attrib['Language'] == att_langue[0]:
                                data[i] = bi.text.strip()
                        except KeyError:
                            all_ok = False
                            break
            elif att == 'Code_ONEMA':
                data[i] = root.find('.//CdAlternative')
                if data[i] is not None:
                    if data[i].attrib['OrgCdAlternative']:
                        if data[i].attrib['OrgCdAlternative'] == 'ONEMA':
                            data[i] = data[i].text.strip()
            elif att == 'Code_Sandre':
                data[i] = root.find('.//CdAppelTaxon')
                if data[i] is not None:
                    data[i] = data[i].text.strip()
            # normal attributes
            # the tag figure_hydrosignature is None (Null) by default
            else:
                data[i] = root.find(".//" + att)
                # None is null for python 3
                if data[i] is not None:
                    data[i] = data[i].text.strip()
            i += 1
        if not all_ok:
            break

        # put data in the new list
        if stages:
            for s in stages:
                # careful the char :
                # is necessary for the function  show_info_fish()
                # from bio_info_GUI
                data_s = [data[4] + ': ' + s + ' - '
                          + data[5], s, preffile]
                #  order mattter HERE! (ind: +3)
                data_s.extend(data)
                data_fish.append(data_s)
        else:
            data_fish.append(data)
        found_one = True

    if not found_one:
        print('Error: No preference file could be read.\
            Please check the biology folder.\n')

    data_fish = np.array(data_fish)

    preffiles = []  # mutable arg.
    return data_fish


def get_stage(names_bio, path_bio):
    """
    This function loads all the stages present in a list o
    xml preference files (JUV, ADU, etc) and the latin name of
    the fish species. All the files should be in the same folder indicated by
    path_bio. It is mainly used by habby_cmd
    but it can be useful in other cases also.

    :param names_bio: A list of xml biological preference file
    :param path_bio: the path to the xml preference files (usually './biology')
    :return: the stages in a list of string

    """
    stages_all = []
    latin_all = []

    for n in names_bio:

        # load the file
        try:
            try:
                docxml = ET.parse(os.path.join(path_bio, n))
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file " + n + " does not exist \n")
                break
        except ET.ParseError:
            print("Warning: the xml file " + n + "is not well-formed.\n")
            break

        # get the stage
        stages = root.findall(".//Stage")
        if len(stages) == 0:
            print('no stage found in ' + n + "\n")
            break
        else:
            try:
                stages = [s.attrib['Type'] for s in stages]
            except KeyError:
                print('no stage found in ' + n + "\n")
                break
        stages_all.append(stages)

        # get latin name
        data = root.find(".//LatinName")
        # None is null for python 3
        if data is not None:
            latin = data.text.strip()
        latin_all.append(latin)

    return latin_all, stages_all


def get_hydrosignature(xmlfile):
    """
    This function plots the hydrosignature in the vclass and hclass given
    in the xml file.
    It does only work if: units are SI (meter and m/s) and if the order of data
     is 'velocity increasing
    and then height of water increasing".

    :param xmlfile: the path and name of the xmlfile
    """

    # open the file
    try:
        try:
            docxml = ET.parse(xmlfile)
            root = docxml.getroot()
        except IOError:
            print("Warning: the xml file does not exist \n")
            return
    except ET.ParseError:
        print("Warning: the xml file is not well-formed.\n")
        return

    # get the hydro signature data
    hs = root.find('HydrosignatureOfTheSamplingData')
    if hs is not None:
        hclass = hs.find('HeightOfWaterClasses')
        vclass = hs.find('VelocityClasses')
        data = hs.find('HydrosignatureValues')
        if vclass is not None and hclass is not None and data is not None:
            try:
                if hclass.attrib['Unit'] == 'Meter' \
                        and vclass.attrib['Unit'] == 'MeterPerSecond':
                    if data.attrib['DescriptionMode'] == \
                            'VelocityIncreasingAndThenHeightOfWaterIncreasing':
                        vclass = vclass.text.split()
                        hclass = hclass.text.split()
                        data = data.text.split()
                        try:
                            vclass = list(map(float, vclass))
                            hclass = list(map(float, hclass))
                            data = list(map(float, data))
                        except ValueError:
                            print('Warning: hydrosignature data could not be\
                                transformed to float')
                            return
                    else:
                        print('Warning: no hydrosignature found in\
                            the xml file (1). \n')
                        return
                else:
                    print('Warning: no hydrosignature found in\
                        the xml file (2). \n')
                    return
            except KeyError:
                print('Warning: Unit no found in the hydrosignature \n')
                return
        else:
            print('Warning: no hydrosignature found in the xml file (3). \n')
            return
    else:
        print('Warning: no hydrosignature found in the xml file (4). \n')
        return

    # if data found, plot the image

    data = np.array(data)
    vclass = np.array(vclass)
    hclass = np.array(hclass)

    if len(data) != (len(vclass) - 1) * (len(hclass) - 1):
        print('Warning: the data for hydrosignature is not\
            of the right length.\n')
        return

    data = data.reshape((len(vclass) - 1, len(hclass) - 1))
    return data


def read_pref(xmlfile):
    """
    This function reads the preference curve from the xml file and
     get the subtrate, height and velocity data.
    It return the data in meter. Unit for space can be in centimeter,
     milimeter or meter. Unit for time should be in
    second .The unit attribute of the xml files should be
     coherent with the data.

    :param xmlfile: the path and name to the xml file (string)
    :return: height, vel, sub, code_fish, name_fish, stade

    """
    failload = [-99], [-99], [-99], [-99], '-99', [-99]
    xml_name = os.path.basename(xmlfile)

    # load the file
    try:
        try:
            docxml = ET.parse(xmlfile)
            root = docxml.getroot()
        except IOError:
            print("Error: the xml file" + xml_name + "does not exist \n")
            return failload
    except ET.ParseError:
        print("Error: the xml file " + xml_name + " is not well-formed.\n")
        return failload

    # get all stage
    stages = []
    stages_data = root.findall(".//Stage")
    if stages_data is not None:
        for s in stages_data:
            stages.append(s.attrib["Type"])
    else:
        print('Error: No stage found in ' + xml_name + ' \n')

    # get the code of the fish
    code_fish = root.find('.//CdAlternative')
    if code_fish is not None:
        if code_fish.attrib['OrgCdAlternative']:
            if code_fish.attrib['OrgCdAlternative'] == 'ONEMA':
                code_fish = code_fish.text.strip()

    # get the latin name of the fish
    name_fish = root.find(".//LatinName")
    # None is null for python 3
    if name_fish is not None:
        name_fish = name_fish.text.strip()

    # velocity
    vel_all = []
    for s in stages:
        vel = [[], []]
        rea = ".//Stage[@Type='" + s + "']/PreferenceVelocity/Value"
        vel_data = root.findall(rea)
        if vel_data is not None:
            for v in vel_data:
                try:
                    data2 = float(v.attrib['p'])
                    data1 = float(v.attrib['v'])
                except ValueError:
                    print('Error: Value cannot be converted to float\
                                    in the velocity data of the xml file'
                          + xml_name + '\n')
                    return failload
                vel[0].extend([data1])
                vel[1].extend([data2])
        else:
            print('Error: Velocity data was not found \n')
            return failload

        # check increasing velocity
        if vel[0] != sorted(vel[0]):
            print('Error: Velocity data is not sorted for the xml file '
                  + xml_name + '.\n')
            return failload

        # manage units
        unit = root.find(".//PreferenceVelocity")
        vel = change_unit(vel, unit.attrib["Unit"])

        vel_all.append(vel)

    # height
    h_all = []
    for s in stages:
        height = [[], []]
        rea = ".//Stage[@Type='" + s + "']/PreferenceHeightOfWater/Value"
        h_data = root.findall(rea)
        if h_data is not None:
            for v in h_data:
                try:
                    data2 = float(v.attrib['p'])
                    data1 = float(v.attrib['hw'])
                except ValueError:
                    print('Error: Value cannot be converted to float\
                     in the height data of the xml file'
                          + xml_name + '\n')
                    return failload
                height[0].extend([data1])
                height[1].extend([data2])
        else:
            print('Error: Height data was not found \n')
            return failload

        # check increasing velocity
        if height[0] != sorted(height[0]):
            print('Error: Height data is not sorted for the xml file '
                  + xml_name + '.\n')
            return failload
        # manage units
        unit = root.find(".//PreferenceHeightOfWater")
        height = change_unit(height, unit.attrib["Unit"])
        h_all.append(height)

    # substrate
    sub_all = []
    for s in stages:
        sub = [[], []]
        rea = ".//Stage[@Type='" + s + "']/PreferenceSubstrate/Value"
        s_data = root.findall(rea)
        if len(s_data) > 0:
            for v in s_data:
                try:
                    data2 = float(v.attrib['p'])  # get rif of the s
                    data1 = float(v.attrib['s'][1:])
                except ValueError:
                    print('Error: Value cannot be converted to float\
                     in the substrate data of the xml file '
                          + xml_name + '\n')
                    return failload
                sub[0].extend([data1])
                sub[1].extend([data2])
            unit = root.find(".//PreferenceSubstrate")
            sub = change_unit(sub, unit.attrib['ClassificationName'])
            sub_all.append(sub)
        else:
            # case without substrate
            sub = [[0, 1], [1, 1]]
            sub_all.append(sub)

    return h_all, vel_all, sub_all, code_fish, name_fish, stages


def change_unit(data, unit):
    """
    This function modify the unit of the data to SI unit.
    Currently it accept the following unit :
    Centimeter, Meter, CentimeterPerSecond, MeterPerSecond, Millimeter,
     "Code EVHA 2.0 (GINOT 1998)"

    :param data: the data which has to be change to SI unti
    :param unit: the unit code
    """

    if unit == 'Centimeter' or unit == "CentimeterPerSecond":
        data[0] = [x / 100 for x in data[0]]
    elif unit == "Meter" or unit == "MeterPerSecond" \
            or unit == "Code EVHA 2.0 (GINOT 1998)":
        pass
    elif unit == "Millimeter":
        data[0] = [x / 1000 for x in data[0]]
    else:
        print('Warning: Unit not recognized \n')

    return data


def create_pdf(xmlfiles, stages_chosen, path_bio, path_im_bio, path_out,
               fig_opt):
    """
    This functionc create a pdf with information about the fish.
    It tries to follow the chosen language, but
    the stage name are not translated and the decription are usually
    only given in French.

    :param xmlfiles: the name of the xmlfile (without the path!)
    :param stages_chosen: the stage chosen (might not be all stages)
    :param path_bio: the path with the biological xml file
    :param path_im_bio: the path with the images of the fish
    :param path_out: the path where to save the .pdf file
        (usually other_outputs)
    :param fig_opt: the figure options (contain the chosen language)
    """
    plt.close()
    plt.rcParams['figure.figsize'] = 21, 29.7  # a4
    plt.rcParams['font.size'] = 24

    # get the stage chosen for each species and get rid of repetition
    stage_chosen2 = []
    stage_here = []
    xmlold = 'sdfsdfs'
    xmlfiles2 = []
    for idx, f in enumerate(xmlfiles):
        if xmlold != f:
            xmlfiles2.append(f)
            if stage_here:
                stage_chosen2.append(stage_here)
            stage_here = []
        stage_here.append(stages_chosen[idx])
        xmlold = f
    if stage_here:
        stage_chosen2.append(stage_here)
    xmlfiles = xmlfiles2

    # create the pdf
    for idx, f in enumerate(xmlfiles):

        # read pref
        xmlfile = os.path.join(path_bio, f)
        [h_all, vel_all, sub_all, code_fish, name_fish, stages] = \
            read_pref(xmlfile)

        # read additionnal info
        attributes = ['Description', 'Image', 'French_common_name',
                      'English_common_name', ]
        # careful: description is last data returned
        data = load_xml_name(path_bio, attributes, [f])

        # create figure
        fake_value = Value("i", 0)
        [f, axarr] = plot_mod.plot_suitability_curve(fake_value, h_all, vel_all, sub_all, code_fish, name_fish,
                                 stages, True, fig_opt)

        # modification of the orginal preference fig
        # (0,0) is bottom left - 1 is the end of the page in x and y direction
        plt.tight_layout(rect=[0.05, 0.05, 0.95, 0.53])
        # position for the image

        # add a fish image
        if path_im_bio:
            fish_im_name = os.path.join(path_im_bio, data[0][0])
            if os.path.isfile(fish_im_name):
                im = plt.imread(mpl.cbook.get_sample_data(fish_im_name))
                newax = f.add_axes([0.1, 0.4, 0.25, 0.25], anchor='NE',
                                   zorder=-1)
                newax.imshow(im)
                newax.axis('off')

        # move suptitle
        if fig_opt['language'] == 0:
            f.suptitle('Suitability curve', x=0.5, y=0.55, fontsize=32,
                       weight='bold')
        elif fig_opt['language'] == 1:
            f.suptitle('Courbe de préférence', x=0.5, y=0.55, fontsize=32,
                       weight='bold')
        else:
            f.suptitle('Suitability curve', x=0.5, y=0.55, fontsize=32,
                       weight='bold')
        # general info
        if fig_opt['language'] == 0:
            plt.figtext(0.1, 0.7, "Latin name:\n\nCommon Name:\n\nONEMA fish code:\n\nStage chosen:\n\nDescription:",
                        weight='bold', fontsize=32)
            text_all = name_fish + '\n\n' + data[0][2] \
                       + '\n\n' + code_fish + '\n\n'
        elif fig_opt['language'] == 1:
            plt.figtext(0.1, 0.7, "Nom latin :\n\nNom commun :\n\nCode ONEMA:\n\nStade choisi :\n\nDescription :",
                        weight='bold', fontsize=32)
            text_all = name_fish + '\n\n' + data[0][1] + '\n\n' \
                       + code_fish + '\n\n'
        else:
            plt.figtext(0.1, 0.7, "Latin name:\n\nCommon Name:\n\nONEMA fish code:\n\nStage chosen:\n\nDescription:",
                        weight='bold', fontsize=32)
            text_all = name_fish + '\n\n' + data[0][2] \
                       + '\n\n' + code_fish + '\n\n'
        for idx, s in enumerate(stage_chosen2[idx]):
            text_all += s + ', '
        text_all = text_all[:-2] + '\n\n'
        plt.figtext(0.4, 0.7, text_all, fontsize=32)
        # bbox={'facecolor':'grey', 'alpha':0.07, 'pad':50}

        # descirption
        if len(data[0][-1]) > 250:
            plt.figtext(0.4, 0.61, data[0][-1][:250] + '...', wrap=True,
                        fontsize=32)
        else:
            plt.figtext(0.4, 0.61, data[0][-1], wrap=True, fontsize=32)

        # title of the page
        plt.figtext(0.1, 0.9, "REPORT - " + name_fish, fontsize=55,
                    weight='bold',
                    bbox={'facecolor': 'grey', 'alpha': 0.15, 'pad': 50})

        # day
        plt.figtext(0.8, 0.95, 'HABBY - ' + time.strftime("%d %b %Y"))

        # save
        filename = os.path.join(path_out, 'report_' + code_fish + '.pdf')
        try:
            plt.savefig(filename)
        except PermissionError:
            print('Warning: Close .pdf to update fish information')


def main():
    """
    Used to test the module on the biological preference
    """

    # test to load the pref from PRF
    # path = \
    #   r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF-part1-Multispe1998'
    # path = \
    # r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF-part2-Lamourouxetal1999'
    # filenames = load_hdf5.get_all_filename(path, '.PRF')
    # for i in range(0, len(filenames)):
    #     [height, vel, sub, code_fish, name_fish, stade, descri] = \
    #       load_evha_curve(filenames[i], path)
    #     figure_pref(height, vel, sub, code_fish, name_fish, stade)
    # plt.show()

    # test to load the pref from xml
    # path = r'C:\Users\diane.von-gunten\HABBY\biology'
    # filenames = load_hdf5.get_all_filename(path, '.xml')
    # for i in range(0,len(filenames)):
    #     filename = os.path.join(path, filenames[i])
    #     [height, vel, sub, code_fish, name_fish, stages] = \
    #       read_pref(filename)
    #     figure_pref(height, vel, sub, code_fish, name_fish, stages)
    # plt.show()

    # test comparison
    # path_xml = r'C:\Users\diane.von-gunten\HABBY\biology'
    # path_evha = r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF_ALL'
    # test_evah_xml_pref(path_xml, path_evha)

    # test for pdf report
    path_bio = r'C:\Users\diane.von-gunten\HABBY\biology'
    path_bio_im = r"C:\Users\diane.von-gunten\HABBY\biology\figure_pref"
    path_out = r'C:\Users\diane.von-gunten\HABBY\biology'
    xmlfiles = ['ABL01.xml', 'ABL01.xml', 'BAM01.xml']
    stages = ['adult', 'juvenile', 'fry']
    fig_opt = preferences_GUI.create_default_figoption()
    fig_opt['language'] = 1
    create_pdf(xmlfiles, stages, path_bio, '', path_out, fig_opt)


if __name__ == '__main__':
    main()
