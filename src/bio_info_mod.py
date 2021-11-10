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
from lxml import etree as ET
import re

from src.dev_tools_mod import copy_files
from src.variable_unit_mod import HydraulicVariableUnitManagement


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
            return "Error: " + path_xml + " file not exist."
    except ET.ParseError:
        print("Error: " + path_xml + " file is not well-formed.")
        return "Error: " + path_xml + " file is not well-formed."

    # CdBiologicalModel
    code_biological_model = root.find('.//CdBiologicalModel').text  # habby curve name database

    # Country
    country = root.find(".//Country").text

    # MadeBy
    made_by = root.find('.//MadeBy').text

    # guild
    guild_element = root.find(".//Guild")
    if guild_element:
        guild = "@guild"
    else:
        guild = "mono"

    # CdAlternative  # ONEMA, .. curve name database
    if guild == "@guild":
        # get all fish guild code alternative
        code_alternative = guild_element.getchildren()[0].text
        CdAlternativefishs = [guild_element.getchildren()[i].find("CdAlternative").text for i in
                              [1, len(guild_element.getchildren()) - 1]]
        code_alternative = [code_alternative + " (" + ", ".join(CdAlternativefishs) + ")"]
    else:
        code_alternative = [root.find('.//CdAlternative').text]

    # aquatic_animal_type
    if root.find(".//Fish") is not None:
        aquatic_animal_type = "fish"
    elif root.find(".//Invertebrate") is not None:
        aquatic_animal_type = "invertebrate"
    elif root.find(".//Crustacean") is not None:
        aquatic_animal_type = "crustacean"
    else:
        print("Error: aquatic_animal_type not recognised. Please verify this xml file :", path_xml)
        return "Error: aquatic_animal_type not recognised. Please verify this xml file :" + path_xml

    # model_type
    model_type = [model.attrib['Type'] for model in root.findall(".//ModelType")][0]
    if model_type not in ("univariate suitability index curves", "bivariate suitability index models"):
        print("Error: ModelType not recognised. Please verify this xml file :", path_xml)
        return "Error: ModelType not recognised. Please verify this xml file :" + path_xml

    # stage_and_size
    stage_and_size = [stage.attrib['Type'] for stage in root.findall(".//Stage")]

    # LatinName
    if guild == "@guild":
        latin_name = "@guild"
    else:
        latin_name = root.find(".//LatinName").text
        if "," in latin_name:
            latin_name = latin_name.replace(",", ".")

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
        if common_name.text:
            common_name_list.append(common_name.text)
        else:
            common_name_list.append("")

    # hvum
    hvum = HydraulicVariableUnitManagement()

    h_not_valid = None
    v_not_valid = None
    shearstress_not_valid = None
    sub_not_valid = None
    hv_not_valid = None

    # model varaible by stage
    for index_stage, stage in enumerate(root.findall(".//Stage")):

        # hvum_stage
        hvum_stage = HydraulicVariableUnitManagement()

        # stage_name
        stage_name = stage_and_size[index_stage]

        # data = list of values
        if model_type == "univariate suitability index curves":
            hvum.h.software_attributes_list = ["PreferenceHeightOfWater"]
            pref_element = stage.findall(".//" + hvum.h.software_attributes_list[0])
            if pref_element:
                hvum.h.original_unit = pref_element[0].findall(".//HeightOfWaterValues")[0].attrib["Unit"]
                hvum_stage.software_detected_list.append(hvum.h)
                h_data = [list(map(float, pref_element[0].findall(".//HeightOfWaterValues")[0].text.split(" "))),
                        list(map(float, pref_element[0].findall(".//PreferenceValues")[0].text.split(" ")))]
                h_not_valid = check_if_data_model_has_error(h_data[0], "HeightOfWaterValues", increasing=True)
                hv_not_valid = check_if_data_model_has_error(h_data[1], "PreferenceValues", increasing=False)
                if len(h_data[0]) != len(h_data[1]):
                    return "Error: HeightOfWaterValues and PreferenceValues are not the same length in " + path_xml

            hvum.v.software_attributes_list = ["PreferenceVelocity"]
            pref_element = stage.findall(".//" + hvum.v.software_attributes_list[0])
            if pref_element:
                hvum.v.original_unit = pref_element[0].findall(".//VelocityValues")[0].attrib["Unit"]
                hvum_stage.software_detected_list.append(hvum.v)
                v_data = [list(map(float, pref_element[0].findall(".//VelocityValues")[0].text.split(" "))),
                        list(map(float, pref_element[0].findall(".//PreferenceValues")[0].text.split(" ")))]
                v_not_valid = check_if_data_model_has_error(v_data[0], "VelocityValues", increasing=True)
                hv_not_valid = check_if_data_model_has_error(v_data[1], "PreferenceValues", increasing=False)
                if len(v_data[0]) != len(v_data[1]):
                    return "Error: VelocityValues and PreferenceValues are not the same length in " + path_xml

            hvum.shear_stress.software_attributes_list = ["PreferenceShearStress"]
            pref_element = stage.findall(".//" + hvum.shear_stress.software_attributes_list[0])
            if pref_element:
                hvum.shear_stress.original_unit = pref_element[0].findall(".//MinimumBottomShearStressCausingTheMovementOfAGivenFSTHemisphereNumberValues")[0].attrib["Unit"]
                hvum_stage.software_detected_list.append(hvum.shear_stress)
                shearstress_data = [list(map(float, pref_element[0].findall(".//MinimumBottomShearStressCausingTheMovementOfAGivenFSTHemisphereNumberValues")[0].text.split(" "))),
                                  list(map(float, pref_element[0].findall(".//HemisphereNumber")[0].text.split(" "))),
                                  list(map(float, pref_element[0].findall(".//PreferenceValues")[0].text.split(" ")))]
                shearstress_not_valid = all((check_if_data_model_has_error(shearstress_data[0], "MinimumBottomShearStressCausingTheMovementOfAGivenFSTHemisphereNumberValues", increasing=True),
                                         check_if_data_model_has_error(shearstress_data[1], "HemisphereNumber", increasing=True)))
                hv_not_valid = check_if_data_model_has_error(shearstress_data[2], "PreferenceValues", increasing=False)
                if len(shearstress_data[0]) != len(shearstress_data[1]) != len(shearstress_data[2]):
                    return "Error: MinimumBottomShearStressCausingTheMovementOfAGivenFSTHemisphereNumberValues and HemisphereNumber and PreferenceValues are not the same length in " + path_xml

            pref_element = stage.findall(".//PreferenceSubstrate")
            if pref_element:
                substrate_original_unit = pref_element[0].findall(".//SubstrateValues")[0].attrib["ClassificationName"]
                if substrate_original_unit in ("Code EVHA 2.0 (GINOT 1998)", "Code Cemagref (Malavoi 1989)"):
                    substrate_unit = "Cemagref"
                elif substrate_original_unit in ("Code Sandre (Malavoi et Souchon 1989)"):
                    substrate_unit = "Sandre"
                else:  # TODO : if another code
                    return "Error: Substrate classification code not recognized :" + substrate_original_unit + " in " + path_xml
                substrate_type = pref_element[0].findall(".//SubstrateValues")[0].attrib["Variables"]
                if substrate_type == 'Coarser':
                    hvum.sub_coarser.software_attributes_list = ["PreferenceSubstrate"]
                    hvum.sub_coarser.original_unit = substrate_original_unit
                    hvum.sub_coarser.unit = substrate_unit
                    hvum_stage.software_detected_list.append(hvum.sub_coarser)
                elif substrate_type == 'Dominant':
                    hvum.sub_dom.software_attributes_list = ["PreferenceSubstrate"]
                    hvum.sub_dom.original_unit = substrate_original_unit
                    hvum.sub_dom.unit = substrate_unit
                    hvum_stage.software_detected_list.append(hvum.sub_dom)
                elif substrate_type == 'Percentages':
                    hvum.sub_percentage.software_attributes_list = ["PreferenceSubstrate"]
                    hvum.sub_percentage.original_unit = substrate_original_unit
                    hvum.sub_percentage.unit = substrate_unit
                    hvum_stage.software_detected_list.append(hvum.sub_percentage)
                else:
                    return "Error: Substrate classification method not recognized : " + substrate_type + " in " + path_xml

                sub_data = [list(map(float, [element[1:] for element in pref_element[0].findall(".//SubstrateValues")[0].text.split(" ")])),
                                  list(map(float, pref_element[0].findall(".//PreferenceValues")[0].text.split(" ")))]
                sub_not_valid = check_if_data_model_has_error(sub_data[0], "SubstrateValues", increasing=True)
                hv_not_valid = check_if_data_model_has_error(sub_data[1], "PreferenceValues", increasing=False)
                if len(sub_data[0]) != len(sub_data[1]):
                    return "Error: SubstrateValues and PreferenceValues are not the same length in " + path_xml
        elif model_type == "bivariate suitability index models":
            pref_element = stage.findall(".//HeightOfWaterValues")
            hvum.h.software_attributes_list = ["HeightOfWaterValues"]
            if pref_element:
                hvum.h.original_unit = pref_element[0].attrib["Unit"]
                hvum_stage.software_detected_list.append(hvum.h)
                h_data = list(map(float, pref_element[0].text.split(" ")))
                h_not_valid = check_if_data_model_has_error(h_data, "HeightOfWaterValues", increasing=True)
            else:
                return "Error: HeightOfWaterValues not recognised for bivariate suitability index models. Please verify this xml file :" + path_xml

            pref_element = stage.findall(".//VelocityValues")
            hvum.v.software_attributes_list = ["VelocityValues"]
            if pref_element:
                hvum.v.original_unit = pref_element[0].attrib["Unit"]
                hvum_stage.software_detected_list.append(hvum.v)
                v_data = list(map(float, pref_element[0].text.split(" ")))
                v_not_valid = check_if_data_model_has_error(v_data, "VelocityValues", increasing=True)
            else:
                print("Error: VelocityValues not recognised for bivariate suitability index models. Please verify this xml file :", path_xml)
                return "Error: VelocityValues not recognised for bivariate suitability index models. Please verify this xml file :" + path_xml

            pref_element = stage.findall(".//PreferenceValues")
            if pref_element:
                if "DescriptionMode" in pref_element[0].attrib.keys():
                    if not pref_element[0].attrib["DescriptionMode"] == 'VelocityIncreasingAndThenHeightOfWaterIncreasing':
                        print("Error: DescriptionMode is not 'VelocityIncreasingAndThenHeightOfWaterIncreasing' for bivariate suitability index models. Please verify this xml file :",
                            path_xml)
                        return "Error: DescriptionMode is not 'VelocityIncreasingAndThenHeightOfWaterIncreasing' for bivariate suitability index models. Please verify this xml file :" + path_xml
                    else:
                        hv_data = list(map(float, pref_element[0].text.split(" ")))
                        hv_not_valid = check_if_data_model_has_error(hv_data, "PreferenceValues", increasing=False)
                else:
                    print("Error: DescriptionMode not recognised in PreferenceValues for bivariate suitability index models. Please verify this xml file :",
                        path_xml)
                    return "Error: DescriptionMode not recognised in PreferenceValues for bivariate suitability index models. Please verify this xml file :" + path_xml
            else:
                print("Error: PreferenceValues not recognised for bivariate suitability index models. Please verify this xml file :", path_xml)
                return "Error: PreferenceValues not recognised for bivariate suitability index models. Please verify this xml file :" + path_xml
            if len(h_data) * len(v_data) != len(hv_data):
                return "Error: HeightOfWaterValues * VelocityValues length different from PreferenceValues length in " + path_xml

        # compile infor
        detect_name_list = hvum_stage.software_detected_list.names()
        height_presence = hvum.h.name in detect_name_list
        velocity_presence = hvum.v.name in detect_name_list
        shear_presence = hvum.shear_stress.name in detect_name_list
        sub_presence = hvum.sub_coarser.name in detect_name_list or hvum.sub_dom.name in detect_name_list

        # always hv_presence
        if hv_not_valid:
            return hv_not_valid
        # model data is valid ?
        for presence, not_valid in zip([height_presence, velocity_presence, shear_presence, sub_presence],
                                    [h_not_valid, v_not_valid, shearstress_not_valid, sub_not_valid]):
            if presence:
                if not_valid:
                    return not_valid + " Please verify this xml file :" + path_xml

        # hyd_opt
        if height_presence and velocity_presence:
            hyd_opt = "HV"
        elif height_presence and not velocity_presence:
            hyd_opt = "H"
        elif not height_presence and velocity_presence:
            hyd_opt = "V"
        elif shear_presence:
            hyd_opt = "HEM"
        elif not height_presence and not velocity_presence and not shear_presence:
            hyd_opt = "Neglect"
        else:
            print("Error: hyd_opt not recognised. Please verify this xml file :", path_xml)
            return "Error: hyd_opt not recognised. Please verify this xml file :", path_xml

        # hyd_opt_available
        hyd_opt_available = []
        if height_presence and velocity_presence:
            hyd_opt_available.append("HV")
        if model_type == "univariate suitability index curves":
            # can be separated
            if height_presence:
                hyd_opt_available.append("H")
            if velocity_presence:
                hyd_opt_available.append("V")
            if shear_presence:
                hyd_opt_available.append("HEM")
        hyd_opt_available.append("Neglect")

        # sub_opt
        if not sub_presence:
            sub_opt = "Neglect"
        else:
            sub_opt = substrate_type

        # sub_opt_available
        if not sub_presence:
            sub_opt_available = ["Neglect"]
        else:
            sub_opt_available = ["Coarser-Dominant",
                                        'Coarser',
                                        'Dominant',
                                        'Percentage',
                                        'Neglect']

        # append_new_habitat_variable
        hvum.software_detected_list.append_new_habitat_variable(code_bio_model=code_biological_model,
                                                                stage=stage_name,
                                                                hyd_opt=hyd_opt,
                                                                hyd_opt_available=hyd_opt_available,
                                                                sub_opt=sub_opt,
                                                                sub_opt_available=sub_opt_available,
                                                                aquatic_animal_type=aquatic_animal_type,
                                                                model_type=model_type,
                                                                pref_file=path_xml,
                                                                path_img=path_img,
                                                                variable_list=hvum_stage.software_detected_list)

    # to dict
    information_model_dict = dict(country=country,
                                  aquatic_animal_type=aquatic_animal_type,
                                  guild=guild,
                                  code_biological_model=code_biological_model,
                                  stage_and_size=stage_and_size,
                                  hydraulic_type=[hab_var.hyd_opt for hab_var in hvum.software_detected_list],
                                  hydraulic_type_available=[hab_var.hyd_opt_available for hab_var in hvum.software_detected_list],
                                  substrate_type=[hab_var.sub_opt for hab_var in hvum.software_detected_list],
                                  substrate_type_available=[hab_var.sub_opt_available for hab_var in hvum.software_detected_list],
                                  model_type=model_type,
                                  made_by=made_by,
                                  code_alternative=code_alternative,
                                  latin_name=latin_name,
                                  modification_date=modification_date,
                                  path_img=path_img,
                                  description=description,
                                  common_name_dict=common_name_list,
                                  hab_variable_list=hvum.software_detected_list)

    return information_model_dict


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
    failload = None
    if os.path.split(xmlfile)[0] == '':  # without path : get classic curves
        xmlfile = os.path.join("biology", "models", xmlfile)

    xml_name = os.path.basename(xmlfile)

    information_model_dict = get_biomodels_informations_for_database(xmlfile)

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

    for hab_index, hab_var in enumerate(information_model_dict["hab_variable_list"]):  # each stage
        for model_var in hab_var.variable_list:
            attr = model_var.software_attributes_list[0]
            model_el_list = root.findall(".//" + attr)
            if information_model_dict["model_type"] == "univariate suitability index curves":
                if information_model_dict["hydraulic_type"][hab_index] == 'HEM':
                    # data = list of 3 elements (shear_stress, HEM, pref)
                    data_el = model_el_list[hab_index].getchildren()[0]
                    model_var.data = [list(map(float, data_el.text.split(" "))),
                                      list(map(float, model_el_list[hab_index].getchildren()[1].text.split(" "))),
                                        list(map(float, model_el_list[hab_index].getchildren()[2].text.split(" ")))]
                else:
                    # data = list of 2 elements (data, pref)
                    data_el = model_el_list[hab_index].getchildren()[0]
                    if model_var.sub:
                        model_var.data = [list(map(float, [element[1:] for element in data_el.text.split(" ")])),
                                          list(map(float, model_el_list[hab_index].getchildren()[1].text.split(" ")))]
                    else:
                        model_var.data = [list(map(float, data_el.text.split(" "))),
                                            list(map(float, model_el_list[hab_index].getchildren()[1].text.split(" ")))]
            elif information_model_dict["model_type"] == "bivariate suitability index models":
                # data = list of values
                data_el = model_el_list[hab_index]
                model_var.data = list(map(float, data_el.text.split(" ")))
            else:
                print('Error: model_type not recogized: ' + information_model_dict["model_type"] + " in "
                      + xml_name + '.\n')
                return failload

            # change_unit
            model_var.data = change_unit(model_var.data, model_var.original_unit)

        if information_model_dict["model_type"] == "bivariate suitability index models":
            # get pref
            hab_var.hv = list(map(float, root.findall(".//PreferenceValues")[hab_index].text.split(" ")))

    return information_model_dict


def check_if_data_model_has_error(data_list, balise_name, increasing=True):
    # is data
    if not data_list:
        return 'Error: ' + balise_name + ' data was not found.'
    # if h or v or shearstress or sub: check increasing
    elif increasing:
        if data_list != sorted(data_list):
            return 'Error: ' + balise_name + ' data is not sorted.'
    return ""


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


def change_unit(data, unit):
    """
    This function modify the unit of the data to SI unit.
    Currently it accept the following unit :
    Centimeter, Meter, CentimeterPerSecond, MeterPerSecond, Millimeter,
     "Code EVHA 2.0 (GINOT 1998)"

    :param data: the data which has to be change to SI unti
    :param unit: the unit code
    """
    sub_units_available_list = ("Sandre", "Cemagref", "Code EVHA 2.0 (GINOT 1998)", "Code Cemagref (Malavoi 1989)", "Code Sandre (Malavoi et Souchon 1989)")
    if unit == 'Centimeter' or unit == "CentimeterPerSecond":
        data[0] = [x / 100 for x in data[0]]
    elif unit == "Meter" or unit == "MeterPerSecond" or unit == "pascal" or unit in sub_units_available_list:
        pass
    elif unit == "Millimeter":
        data[0] = [x / 1000 for x in data[0]]
    else:
        print('Warning: Unit not recognized : ' + unit)

    return data


def copy_or_not_user_pref_curve_to_input_folder(animal, project_preferences):
    # copy xml curves to input project folder
    if "INRAE_EDF_OFB" in os.path.dirname(animal.pref_file):  # user case
        name_xml = os.path.basename(animal.pref_file)
        path = os.path.dirname(animal.pref_file)
        if not os.path.exists(os.path.join(project_preferences["path_input"], "user_models")):
            os.makedirs(os.path.join(project_preferences["path_input"], "user_models"))
        copy_files([name_xml], [path], os.path.join(project_preferences["path_input"], "user_models"))