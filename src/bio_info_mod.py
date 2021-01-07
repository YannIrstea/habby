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
import sqlite3
from datetime import datetime
import numpy as np
from PyQt5.QtCore import QCoreApplication as qt_tr
from lxml import etree as ET
from multiprocessing import Value
from matplotlib import pyplot as plt
import matplotlib as mpl
import time

from src import hdf5_mod
from src.plot_mod import plot_suitability_curve, plot_suitability_curve_invertebrate, plot_suitability_curve_bivariate


def export_report(xmlfile, hab_animal_type, project_preferences):
    # plt.close()
    plt.rcParams['figure.figsize'] = 21, 29.7  # a4
    plt.rcParams['font.size'] = 24

    information_model_dict = get_biomodels_informations_for_database(xmlfile)

    # read additionnal info
    attributes = ['Description', 'Image', 'French_common_name',
                  'English_common_name', ]
    # careful: description is last data returned
    path_bio = os.path.dirname(xmlfile)
    path_im_bio = path_bio
    xmlfile = os.path.basename(xmlfile)
    data = load_xml_name(path_bio, attributes, [xmlfile])

    # create figure
    fake_value = Value("d", 0)

    if information_model_dict["ModelType"] != "bivariate suitability index models":
        # fish
        if hab_animal_type == "fish":
            # read pref
            h_all, vel_all, sub_all, sub_code, code_fish, name_fish, stages = \
                read_pref(xmlfile, hab_animal_type)
            # plot
            fig, axe_curve = plot_suitability_curve(fake_value,
                                                    h_all,
                                                    vel_all,
                                                    sub_all,
                                                    information_model_dict["CdBiologicalModel"],
                                                    name_fish,
                                                    stages,
                                                    information_model_dict["substrate_type"],
                                                    sub_code,
                                                    project_preferences,
                                                    True)
        # invertebrate
        else:
            # open the pref
            shear_stress_all, hem_all, hv_all, _, code_fish, name_fish, stages = \
                read_pref(xmlfile, hab_animal_type)
            # plot
            fig, axe_curve = plot_suitability_curve_invertebrate(fake_value,
                                                                 shear_stress_all, hem_all, hv_all,
                                                                 code_fish, name_fish,
                                                                 stages, project_preferences, True)
    else:
        # open the pref
        [h_all, vel_all, pref_values_all, _, code_fish, name_fish, stages] = read_pref(xmlfile,
                                                                                       hab_animal_type)
        state_fake = Value("d", 0)
        fig, axe_curve = plot_suitability_curve_bivariate(state_fake,
                                                          h_all,
                                                          vel_all,
                                                          pref_values_all,
                                                          code_fish,
                                                          name_fish,
                                                          stages,
                                                          project_preferences,
                                                          True)
    # get axe and fig
    # fig = plt.gcf()
    # axe_curve = plt.gca()

    # modification of the orginal preference fig
    # (0,0) is bottom left - 1 is the end of the page in x and y direction
    # plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.53])
    plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.53])
    # position for the image

    # HABBY and date
    plt.figtext(0.8, 0.97, 'HABBY - ' + time.strftime("%d %b %Y"))

    # REPORT title
    plt.figtext(0.1, 0.92, "REPORT - " + name_fish,
                fontsize=55,
                weight='bold',
                bbox={'facecolor': 'grey', 'alpha': 0.15, 'pad': 50})

    # Informations title
    list_of_title = [qt_tr.translate("hdf5_mod", "Latin name:"),
                     qt_tr.translate("hdf5_mod", "Common Name:"),
                     qt_tr.translate("hdf5_mod", "Code biological model:"),
                     qt_tr.translate("hdf5_mod", "ONEMA fish code:"),
                     qt_tr.translate("hdf5_mod", "Stage chosen:"),
                     qt_tr.translate("hdf5_mod", "Description:")]
    list_of_title_str = "\n\n".join(list_of_title)
    plt.figtext(0.1, 0.7,
                list_of_title_str,
                weight='bold',
                fontsize=32)

    # Informations text
    text_all = name_fish + '\n\n' + data[0][2] + '\n\n' + information_model_dict[
        "CdBiologicalModel"] + '\n\n' + code_fish + '\n\n'
    for idx, s in enumerate(stages):
        text_all += s + ', '
    text_all = text_all[:-2] + '\n\n'
    plt.figtext(0.4, 0.7, text_all, fontsize=32)

    # description
    newax = fig.add_axes([0.4, 0.55, 0.30, 0.16], anchor='C',
                         zorder=-1, frameon=False)
    newax.name = "description"
    newax.xaxis.set_ticks([])  # remove ticks
    newax.yaxis.set_ticks([])  # remove ticks
    if len(data[0][-1]) > 350:
        decription_str = data[0][-1][:350] + '...'
    else:
        decription_str = data[0][-1]
    newax.text(0.0, 1.0, decription_str,  # 0.4, 0.71,
               wrap=True,
               fontsize=32,
               # bbox={'facecolor': 'grey',
               #       'alpha': 0.15},
               va='top',
               ha="left")  #, transform=newax.transAxes

    # add a fish image
    if path_im_bio:
        fish_im_name = os.path.join(os.getcwd(), path_im_bio, data[0][0])
        if os.path.isfile(fish_im_name):
            im = plt.imread(mpl.cbook.get_sample_data(fish_im_name))
            newax = fig.add_axes([0.078, 0.55, 0.25, 0.13], anchor='C',
                                 zorder=-1)
            newax.imshow(im)
            newax.axis('off')

    # move suptitle
    fig.suptitle(qt_tr.translate("hdf5_mod", 'Habitat Suitability Index'),
                 x=0.5, y=0.54,
                 fontsize=32,
                 weight='bold')

    # filename
    filename = os.path.join(project_preferences['path_figure'], 'report_' + information_model_dict["CdBiologicalModel"] +
                            project_preferences["format"])

    # save
    try:
        plt.savefig(filename)
        plt.close(fig)
        plt.clf()
    except PermissionError:
        print(
            'Warning: ' + qt_tr.translate("hdf5_mod", 'Close ' + filename + ' to update fish information'))


def get_biomodels_informations_for_database(path_xml):
    """

    :param path_xml:
    :return:
    """
    # TODO:
    #  1 <CdAlternative ....>il faut absolument une info là monobloc</CdAlternative >
    #  2 <CdBiologicalModel>SIC01 il faut que l'on ait un idenfiant unique monobloc non partagé avec un autre xml! dans habby v appdata </CdBiologicalModel>
    #  3 checker la validité des  modeles de courbes unitSymbol
    #  #  new functionil se peut <Image></Image> pas d'image ou même pas les balises et il faut l'admettre // \\ format possible image jpg ou png
    #  4 codebiomodel and stage don't have to contain " " and "_"

    # open the file
    if os.path.split(path_xml)[0] == '':  # without path : get classic curves
        path_xml = os.path.join("biology", "models", path_xml)

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

    # CdBiologicalModel
    CdBiologicalModel = root.find('.//CdBiologicalModel').text

    # Country
    country = root.find(".//Country").text

    # MadeBy
    MadeBy = root.find('.//MadeBy').text

    # guild
    guild_element = root.find(".//Guild")
    if guild_element:
        guild = "@guild"
    else:
        guild = "mono"

    # CdAlternative
    if guild == "@guild":
        # get all fish guild code alternative
        CdAlternative = guild_element.getchildren()[0].text
        CdAlternativefishs = [guild_element.getchildren()[i].find("CdAlternative").text for i in
                              [1, len(guild_element.getchildren()) - 1]]
        CdAlternative = [CdAlternative + " (" + ", ".join(CdAlternativefishs) + ")"]
    else:
        CdAlternative = [root.find('.//CdAlternative').text]

    # aquatic_animal_type
    if root.find(".//Fish") is not None:
        aquatic_animal_type = "fish"
    elif root.find(".//Invertebrate") is not None:
        aquatic_animal_type = "invertebrate"
    else:
        print("Error: aquatic_animal_type not recognised. Please verify this xml file :", path_xml)
        return

    # ModelType
    ModelType = [model.attrib['Type'] for model in root.findall(".//ModelType")][0]

    # stage_and_size
    stage_and_size = [stage.attrib['Type'] for stage in root.findall(".//Stage")]
    # if "[" in stage_and_size[0]:
    #     stage_and_size = ["class_size"] * len(stage_and_size)

    # hydraulic_type
    hydraulic_type = []
    hydraulic_type_available = []
    for index_stage, stage in enumerate(root.findall(".//Stage")):
        if ModelType != 'bivariate suitability index models':
            hydraulic_type.append([])
            hydraulic_type_available.append([])
            height_presence = False
            velocity_presence = False
            shear_presence = False
            if stage.findall(".//HeightOfWaterValues"):
                height_presence = True
            if stage.findall(".//VelocityValues"):
                velocity_presence = True
            if stage.findall(".//PreferenceShearStress"):
                shear_presence = True
            # compile infor
            if height_presence and velocity_presence:
                hydraulic_type[index_stage] = qt_tr.translate("bio_info_mod", "HV")
            if height_presence and not velocity_presence:
                hydraulic_type[index_stage] = qt_tr.translate("bio_info_mod", "H")
            if not height_presence and velocity_presence:
                hydraulic_type[index_stage] = qt_tr.translate("bio_info_mod", "V")
            if shear_presence:
                hydraulic_type[index_stage] = qt_tr.translate("bio_info_mod", "HEM")
            if not height_presence and not velocity_presence and not shear_presence:
                hydraulic_type[index_stage] = qt_tr.translate("bio_info_mod",
                                                              "Neglect")  # 'Input' sera le nom de classe dans QLinguist et 'Neglect' le string à traduire.
            # available
            if height_presence and velocity_presence:
                hydraulic_type_available[index_stage].append(qt_tr.translate("bio_info_mod", "HV"))
            if height_presence:
                hydraulic_type_available[index_stage].append(qt_tr.translate("bio_info_mod", "H"))
            if velocity_presence:
                hydraulic_type_available[index_stage].append(qt_tr.translate("bio_info_mod", "V"))
            if shear_presence:
                hydraulic_type_available[index_stage].append(qt_tr.translate("bio_info_mod", "HEM"))
            hydraulic_type_available[index_stage].append(qt_tr.translate("bio_info_mod", "Neglect"))
        else:
            hydraulic_type.append([])
            hydraulic_type[index_stage] = qt_tr.translate("bio_info_mod", "HV")
            hydraulic_type_available.append([])
            hydraulic_type_available[index_stage].append(qt_tr.translate("bio_info_mod", "HV"))

    # substrate
    substrate_type = [stage.getchildren()[0].attrib["Variables"] for stage in root.findall(".//PreferenceSubstrate")]
    if substrate_type == []:
        substrate_type = [qt_tr.translate("bio_info_mod", "Neglect")] * len(stage_and_size)
        substrate_type_available = [[qt_tr.translate("bio_info_mod", "Neglect")]] * len(stage_and_size)
    else:
        substrate_type_available = [[qt_tr.translate("bio_info_mod", "Coarser-Dominant"),
                                     qt_tr.translate("bio_info_mod", 'Coarser'),
                                     qt_tr.translate("bio_info_mod", 'Dominant'),
                                     qt_tr.translate("bio_info_mod", 'Percentage'),
                                     qt_tr.translate("bio_info_mod", 'Neglect')]] * len(stage_and_size)

    # LatinName
    if guild == "@guild":
        LatinName = "@guild"
    else:
        LatinName = root.find(".//LatinName").text
        if "," in LatinName:
            LatinName = LatinName.replace(",", ".")

    # modification_date
    modification_date = str(datetime.fromtimestamp(os.path.getmtime(path_xml)))[:-7]

    # image file
    path_img_prov = root.find(".//Image").text
    if path_img_prov:
        path_img = os.path.join(os.path.dirname(path_xml), path_img_prov)
    else:
        path_img = None

    # to dict
    information_model_dict = dict(country=country,
                                  aquatic_animal_type=aquatic_animal_type,
                                  guild=guild,
                                  CdBiologicalModel=CdBiologicalModel,
                                  stage_and_size=stage_and_size,
                                  hydraulic_type=hydraulic_type,
                                  hydraulic_type_available=hydraulic_type_available,
                                  substrate_type=substrate_type,
                                  substrate_type_available=substrate_type_available,
                                  ModelType=ModelType,
                                  MadeBy=MadeBy,
                                  CdAlternative=CdAlternative,
                                  LatinName=LatinName,
                                  modification_date=modification_date,
                                  path_img=path_img)

    return information_model_dict


def get_name_stage_codebio_fromstr(item_str):
    name_fish, stage, code_bio_model = item_str.split(" - ")
    return name_fish, stage, code_bio_model


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
    import sys
    sys.stdout = sys.__stdout__
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
                                if bi.text:
                                    data[i] = bi.text.strip()
                                else:
                                    data[i] = "-"
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
                    # print("data[i]", preffile, data[i])
                    if data[i].text:
                        data[i] = data[i].text.strip()
                    else:
                        data[i] = "-"
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
    error_list = False, False, False
    # open the file
    try:
        try:
            docxml = ET.parse(xmlfile)
            root = docxml.getroot()
        except IOError:
            print("Warning: the xml file does not exist \n")
            return error_list
    except ET.ParseError:
        print("Warning: the xml file is not well-formed.\n")
        return error_list

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
                            return error_list
                    else:
                        print('Warning: no hydrosignature found in\
                            the xml file (1). \n')
                        return error_list
                else:
                    print('Warning: no hydrosignature found in\
                        the xml file (2). \n')
                    return error_list
            except KeyError:
                print('Warning: Unit no found in the hydrosignature \n')
                return error_list
        else:
            print('Warning: no hydrosignature found in the xml file (3). \n')
            return error_list
    else:
        # print('Warning: no hydrosignature found in the xml file (4). \n')
        return error_list

    # if data found, plot the image

    data = np.array(data)
    vclass = np.array(vclass)
    hclass = np.array(hclass)

    if len(data) != (len(vclass) - 1) * (len(hclass) - 1):
        print('Warning: the data for hydrosignature is not\
            of the right length.\n')
        return error_list

    data = data.reshape((len(vclass) - 1, len(hclass) - 1))
    return data, vclass, hclass


def read_pref(xmlfile, aquatic_animal_type="fish", desired_stages=None):
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
    failload = [-99], [-99], [-99], [-99], [-99], [-99], [-99]

    if os.path.split(xmlfile)[0] == '':  # without path : get classic curves
        xmlfile = os.path.join("biology", "models", xmlfile)

    xml_name = os.path.basename(xmlfile)

    h_all, vel_all, sub_all = [], [], []

    # load the file
    try:
        try:
            docxml = ET.parse(xmlfile)
            root = docxml.getroot()
        except IOError:
            print("Error: the xml file" + xml_name + " does not exist \n")
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
            code_fish = code_fish.text.strip()

    # get the latin name of the fish
    name_fish = root.find(".//LatinName")
    # None is null for python 3
    if name_fish is not None:
        name_fish = name_fish.text.strip()

    # ModelType
    ModelType = [model.attrib['Type'] for model in root.findall(".//ModelType")][0]

    # fish case
    if aquatic_animal_type == "fish":
        # velocity
        vel_all = []
        if ModelType != 'bivariate suitability index models':
            pref_vel = root.findall(".//PreferenceVelocity")
            for pref_vel_i in pref_vel:
                vel = [[], []]
                vel[0] = list(map(float, pref_vel_i.getchildren()[0].text.split(" ")))
                vel[1] = list(map(float, pref_vel_i.getchildren()[1].text.split(" ")))
                if not vel[0]:
                    print('Error: Velocity data was not found \n')
                    return failload

                # check increasing velocity
                if vel[0] != sorted(vel[0]):
                    print('Error: Velocity data is not sorted for the xml file '
                          + xml_name + '.\n')
                    return failload

                # manage units
                vel = change_unit(vel, pref_vel_i.getchildren()[0].attrib["Unit"])
                vel_all.append(vel)
        else:
            pref_vel = root.findall(".//VelocityValues")
            for pref_vel_i in pref_vel:
                vel_all.append(list(map(float, pref_vel_i.text.split(" "))))

        # height
        h_all = []
        if ModelType != 'bivariate suitability index models':
            pref_hei = root.findall(".//PreferenceHeightOfWater")
            for pref_hei_i in pref_hei:
                height = [[], []]
                height[0] = list(map(float, pref_hei_i.getchildren()[0].text.split(" ")))
                height[1] = list(map(float, pref_hei_i.getchildren()[1].text.split(" ")))

                if not height[0]:
                    print('Error: Height data was not found \n')
                    return failload

                # check increasing velocity
                if height[0] != sorted(height[0]):
                    print('Error: Height data is not sorted for the xml file '
                          + xml_name + '.\n')
                    return failload
                # manage units
                height = change_unit(height, pref_hei_i.getchildren()[0].attrib["Unit"])
                h_all.append(height)
        else:
            pref_hei = root.findall(".//HeightOfWaterValues")
            for pref_hei_i in pref_hei:
                h_all.append(list(map(float, pref_hei_i.text.split(" "))))

        # substrate
        sub_all = []
        sub_code = []
        if ModelType != 'bivariate suitability index models':
            pref_sub = root.findall(".//PreferenceSubstrate")
            if pref_sub:
                for pref_sub_i in pref_sub:
                    sub = [[], []]
                    sub[0] = list(map(float, [element[1:] for element in pref_sub_i.getchildren()[0].text.split(" ")]))
                    sub[1] = list(map(float, pref_sub_i.getchildren()[1].text.split(" ")))
                    sub = change_unit(sub, pref_sub_i.getchildren()[0].attrib['ClassificationName'])
                    if pref_sub_i.getchildren()[0].attrib['ClassificationName'] == "Code EVHA 2.0 (GINOT 1998)":
                        sub_code.append("Cemagref")
                    else:  # TODO : if another code
                        sub_code.append("Cemagref")
                    if not sub[0]:
                        # case without substrate
                        sub = [[0, 1], [1, 1]]
                    sub_all.append(sub)
            else:
                for i in range(len(stages)):
                    sub_all.append([[0, 1], [1, 1]])
        else:
            pref_sub = root.findall(".//PreferenceValues")
            for pref_sub_i in pref_sub:
                sub_all.append(list(map(float, pref_sub_i.text.split(" "))))

    # fish case
    if aquatic_animal_type == "invertebrate":
        sub_code = []
        # shear_stress_all, hem_all, hv_all
        h_all = []  # fake height (HEM)
        pref_hei = root.findall(".//PreferenceShearStress")
        for pref_hei_i in pref_hei:
            height = [[], [], []]
            height[0] = list(map(float, pref_hei_i.getchildren()[0].text.split(" ")))  # shear_stress_all
            height[1] = list(map(float, pref_hei_i.getchildren()[1].text.split(" ")))  # hem_all
            height[2] = list(map(float, pref_hei_i.getchildren()[2].text.split(" ")))  # hv_all

            if not height[0]:
                print('Error: Height data was not found \n')
                return failload

            # check increasing velocity
            if height[0] != sorted(height[0]):
                print('Error: Height data is not sorted for the xml file '
                      + xml_name + '.\n')
                return failload
            h_all.append(height[0])
            vel_all.append(height[1])
            sub_all.append(height[2])

    if desired_stages:
        desired_stage_index = stages.index(desired_stages)
        h_all = [h_all[desired_stage_index]]
        vel_all = [vel_all[desired_stage_index]]
        sub_all = [sub_all[desired_stage_index]]
        stages = [stages[desired_stage_index]]

    return h_all, vel_all, sub_all, sub_code, code_fish, name_fish, stages


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
    elif unit == "Meter" or unit == "MeterPerSecond" or unit == "Code EVHA 2.0 (GINOT 1998)":
        pass
    elif unit == "Millimeter":
        data[0] = [x / 1000 for x in data[0]]
    else:
        print('Warning: Unit not recognized \n')

    return data
