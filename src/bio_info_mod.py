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
import re


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
            print("Error: " + path_xml + " file not exist.")
            return
    except ET.ParseError:
        print("Error: the xml file is not well-formed.")
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

    # Description
    description = root.find(".//Description").text.strip()
    description = re.sub("\s\s+", "\n", description)

    # Common_name
    common_name_el_list = root.findall('.//ComName')
    common_name_list = []
    for common_name in common_name_el_list:
        common_name_list.append(common_name.text)

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
                                  path_img=path_img,
                                  description=description,
                                  common_name_dict=common_name_list)

    return information_model_dict


def check_if_habitat_variable_is_valid(pref_file, stage, hyd_opt, sub_opt):
    # valid
    valid = True
    hyd_opt_valid = ("HV", "H", "V", "Neglect")
    sub_opt_valid = ("Coarser-Dominant", "Coarser", "Dominant", "Neglect")

    # warning
    if hyd_opt == "Neglect" and sub_opt == "Neglect":
        print('Error: ' + pref_file + "_" + stage + " model options are Neglect and Neglect for hydraulic and "
                                                      "substrate options.")
        valid = False

    # pref_file exist ?
    information_model_dict = get_biomodels_informations_for_database(pref_file)
    if information_model_dict is None:  # file not exist
        valid = False
    else:
        # stage exist ?
        if stage not in information_model_dict["stage_and_size"]:
            print("Error: " + stage + " not exist in existing stages : " + ", ".join(information_model_dict["stage_and_size"]))
            valid = False

    # hyd_opt exist ?
    if hyd_opt not in hyd_opt_valid:
        print("Error: " + hyd_opt + " not exist in hydraulic options : " + ", ".join(hyd_opt_valid))
        valid = False

    # sub_opt exist ?
    if sub_opt not in sub_opt_valid:
        print("Error: " + sub_opt + " not exist in substrate options : " + ", ".join(sub_opt_valid))
        valid = False

    return valid


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
            print("Error: the xml file does not exist \n")
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
                    if pref_sub_i.getchildren()[0].attrib['ClassificationName'] in ("Code EVHA 2.0 (GINOT 1998)",
                                                                                    "Code Cemagref (Malavoi 1989)"):
                        sub_code.append("Cemagref")
                    elif pref_sub_i.getchildren()[0].attrib['ClassificationName'] in ("Code Sandre (Malavoi et Souchon 1989)"):
                        sub_code.append("Sandre")
                    else:  # TODO : if another code
                        print("Error: Substrate ClassificationName not recognized :", pref_sub_i.getchildren()[0].attrib['ClassificationName'])
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

    # invertebrate sub_all
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
    elif unit == "Meter" or unit == "MeterPerSecond" or unit == "Code EVHA 2.0 (GINOT 1998)" or unit == "Code Sandre (Malavoi et Souchon 1989)":
        pass
    elif unit == "Millimeter":
        data[0] = [x / 1000 for x in data[0]]
    else:
        print('Warning: Unit not recognized')

    return data
