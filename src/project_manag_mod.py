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
from lxml import etree as ET
import shutil


def create_project_structure(path_prj, file_log, version_habby, user_name, description, mode="GUI"):
    # create_default_project_preferences_dict
    project_preferences = create_default_project_preferences_dict()

    # check if folder exist
    if not os.path.exists(path_prj):
        os.makedirs(path_prj)

    # get name
    name_prj = os.path.basename(path_prj)

    # update dict
    project_preferences["name_prj"] = name_prj
    project_preferences["path_prj"] = path_prj
    project_preferences["file_log"] = file_log
    project_preferences["version_habby"] = version_habby
    project_preferences["user_name"] = user_name
    project_preferences["description"] = description
    project_preferences["mode"] = mode
    project_preferences["path_input"] = os.path.join(path_prj, project_preferences['path_input'])  # path input
    project_preferences["path_hdf5"] = os.path.join(path_prj, project_preferences['path_hdf5'])  # path hdf5
    project_preferences["path_figure"] = os.path.join(path_prj, project_preferences['path_figure'])  # path figures
    project_preferences["path_text"] = os.path.join(path_prj, project_preferences['path_text'])  # path text output
    project_preferences["path_gis"] = os.path.join(path_prj, project_preferences['path_gis'])  # path_gis
    project_preferences["path_3d"] = os.path.join(path_prj, project_preferences['path_3d'])  # path_3d

    # create .habby project file
    create_or_update_project_preferences_file(path_prj, project_preferences)

    # create the log files by copying the existing "basic" log files (log0.txt and restart_log0.txt)
    if name_prj != '':
        shutil.copy(os.path.join('files_dep', 'log0.txt'), os.path.join(path_prj, name_prj + '.log'))
        shutil.copy(os.path.join('files_dep', 'restart_log0.txt'), os.path.join(path_prj,
                                                                              'restart_' + name_prj +
                                                                              '.log'))

    # create a default directory for the figures and the hdf5
    if not os.path.exists(project_preferences["path_input"]):
        os.makedirs(project_preferences["path_input"])
    if not os.path.exists(project_preferences["path_hdf5"]):
        os.makedirs(project_preferences["path_hdf5"])
    if not os.path.exists(os.path.join(path_prj, 'output')):
        os.makedirs(os.path.join(path_prj, 'output'))
    if not os.path.exists(project_preferences["path_figure"]):
        os.makedirs(project_preferences["path_figure"])
    if not os.path.exists(project_preferences["path_text"]):
        os.makedirs(project_preferences["path_text"])
    if not os.path.exists(project_preferences["path_gis"]):
        os.makedirs(project_preferences["path_gis"])
    if not os.path.exists(project_preferences["path_3d"]):
        os.makedirs(project_preferences["path_3d"])

    # create the concurrency file
    filenamec = os.path.join(os.path.join(path_prj, 'hdf5'), 'check_concurrency.txt')
    if os.path.isdir(os.path.join(path_prj, 'hdf5')):
        with open(filenamec, 'wt') as f:
            f.write('open')


def create_default_project_preferences_dict(all_export_enabled=False):
    """
    This function creates the default dictionnary of project user preferences.
    """
    # init
    project_preferences = dict()

    # general
    project_preferences['name_prj'] = ""
    project_preferences['path_prj'] = ""
    project_preferences['path_last_file_loaded'] = ""
    project_preferences['file_log'] = ""
    project_preferences['file_restart'] = ""
    project_preferences['save_log'] = True
    project_preferences['user_name'] = ""
    project_preferences['description'] = ""
    project_preferences['version_habby'] = ""
    project_preferences['path_bio'] = os.path.join("biology", "models")
    project_preferences['path_input'] = 'input'
    project_preferences['path_hdf5'] = 'hdf5'
    project_preferences['path_figure'] = os.path.join('output', 'figures')
    project_preferences['path_text'] = os.path.join('output', 'text')
    project_preferences['path_gis'] = os.path.join('output', 'GIS')
    project_preferences['path_3d'] = os.path.join('output', '3D')
    project_preferences['physic_tabs'] = False
    project_preferences['stat_tabs'] = False
    project_preferences['language'] = 0  # 0 english, 1 french
    project_preferences['copy_input_files'] = True
    project_preferences['cut_mesh_partialy_dry'] = True  # cut of not mesh partialy wet
    project_preferences['min_height_hyd'] = 0.001  # node mesh minimum water height consider like dry
    project_preferences['erase_id'] = True  # erase file (hdf5, outputs) if exist. if not set date/hour in filename

    # output (first element list == for .hyd and second element list == for .hab)
    project_preferences['mesh_whole_profile'] = [all_export_enabled, all_export_enabled]  # shapefile mesh whole profile
    project_preferences['point_whole_profile'] = [all_export_enabled, all_export_enabled]  # shapefile point whole profile
    project_preferences['mesh_units'] = [all_export_enabled, all_export_enabled]  # shapefile mesh by unit
    project_preferences['point_units'] = [all_export_enabled, all_export_enabled]  # shapefile point by unit
    project_preferences['elevation_whole_profile'] = [all_export_enabled, all_export_enabled]  # mesh .stl of topography whole profile (vertical_exaggeration)
    project_preferences['variables_units'] = [all_export_enabled, all_export_enabled]  # mesh .pvd and .vtu by unit (vertical_exaggeration)
    project_preferences['habitat_text'] = [False, True]  # .txt with detail values by mesh
    project_preferences['detailled_text'] = [all_export_enabled, all_export_enabled]  # .txt with detail values by mesh
    project_preferences['fish_information'] = [all_export_enabled, all_export_enabled]  # image of fish informations
    project_preferences['vertical_exaggeration'] = 10  # paraview vertical exageration
    project_preferences['pvd_variable_z'] = "water_level"

    # figures
    project_preferences['height'] = 7.0
    project_preferences['width'] = 10.0
    project_preferences['color_map1'] = 'coolwarm'
    project_preferences['color_map2'] = 'jet'
    project_preferences['font_size'] = 12
    project_preferences['line_width'] = 1
    project_preferences['grid'] = False  # grid on plot
    project_preferences['format'] = ".png"  # png, pdf, jpg
    project_preferences['resolution'] = 300  # dpi
    project_preferences['fish_name_type'] = 0  # latin_name, french, english, code_alternative
    project_preferences['marker'] = True  # Add point to line plot

    return project_preferences


def create_or_update_project_preferences_file(path_prj, project_preferences):
    name_prj = os.path.basename(path_prj)

    # create the root <root> and general tab
    root_element = ET.Element("root")
    tree = ET.ElementTree(root_element)

    # general
    general_element = ET.SubElement(root_element, "general")
    child = ET.SubElement(general_element, "name_prj")  # name_prj
    child.text = name_prj
    path_child = ET.SubElement(general_element, "path_prj")  # path_prj
    path_child.text = path_prj
    path_last_file_loaded_child = ET.SubElement(general_element, "path_last_file_loaded")  # path_last_file_loaded
    path_last_file_loaded_child.text = path_prj
    log_element = ET.SubElement(general_element, "log_info")
    pathlog_child = ET.SubElement(log_element, "file_log")  # file_log
    pathlog_child.text = os.path.join(name_prj + '.log')
    pathlog_child = ET.SubElement(log_element, "file_restart")  # file_restart
    pathlog_child.text = os.path.join('restart_' + name_prj + '.log')
    savelog_child = ET.SubElement(log_element, "save_log")  # save_log
    savelog_child.text = str(project_preferences["save_log"])
    user_child = ET.SubElement(general_element, "user_name")  # user_name
    user_child.text = project_preferences["user_name"]
    des_child = ET.SubElement(general_element, "description")  # description
    des_child.text = project_preferences["description"]
    ver_child = ET.SubElement(general_element, 'version_habby')  # version_habby
    ver_child.text = str(project_preferences["version_habby"])
    path_element = ET.SubElement(general_element, "paths")
    path_bio_child = ET.SubElement(path_element, "path_bio")
    path_bio_child.text = project_preferences['path_bio']
    path_input_child = ET.SubElement(path_element, "path_input")
    path_input_child.text = project_preferences['path_input']
    path_hdf5_child = ET.SubElement(path_element, "path_hdf5")
    path_hdf5_child.text = project_preferences['path_hdf5']
    path_figure_child = ET.SubElement(path_element, "path_figure")
    path_figure_child.text = project_preferences['path_figure']
    path_text_child = ET.SubElement(path_element, "path_text")
    path_text_child.text = project_preferences['path_text']
    path_gis_child = ET.SubElement(path_element, "path_gis")
    path_gis_child.text = project_preferences['path_gis']
    path_3d_child = ET.SubElement(path_element, "path_3d")
    path_3d_child.text = project_preferences['path_3d']
    min_height_hyd_child = ET.SubElement(general_element, "min_height_hyd")  # min_height
    min_height_hyd_child.text = str(project_preferences['min_height_hyd'])
    cut_mesh_partialy_dry_child = ET.SubElement(general_element, "cut_mesh_partialy_dry")  # cut_mesh_partialy_dry
    cut_mesh_partialy_dry_child.text = str(project_preferences['cut_mesh_partialy_dry'])
    erase_id_child = ET.SubElement(general_element, "erase_id")  # erase_id
    erase_id_child.text = str(project_preferences['erase_id'])
    copy_input_files_child = ET.SubElement(general_element, "copy_input_files")  # copy_input_files
    copy_input_files_child.text = str(project_preferences['copy_input_files'])
    copy_input_files_child = ET.SubElement(general_element, "mode")  # mode
    copy_input_files_child.text = str(project_preferences['mode'])
    langfig1 = ET.SubElement(general_element, "language")  # LangFig
    langfig1.text = str(project_preferences['language'])

    # export
    export_list = ['point_units', 'detailled_text', 'fish_information', 'point_whole_profile', 'mesh_units', 'mesh_whole_profile',
     'variables_units', 'elevation_whole_profile']
    export_element = ET.SubElement(root_element, "export")
    for checkbox_name in export_list:
        locals()[checkbox_name] = ET.SubElement(export_element, checkbox_name)  # checkbox_name
    for checkbox_name in export_list:
        locals()[checkbox_name].text = str(project_preferences[checkbox_name])
    vertical_exaggeration1 = ET.SubElement(export_element, "vertical_exaggeration")  # vertical_exaggeration
    vertical_exaggeration1.text = str(project_preferences["vertical_exaggeration"])
    pvd_variable_z = ET.SubElement(export_element, "pvd_variable_z")  # pvd_variable_z
    pvd_variable_z.text = str(project_preferences["pvd_variable_z"])

    # FIGURE
    figure_element = ET.SubElement(root_element, "figure")
    width1 = ET.SubElement(figure_element, 'width')  # width
    width1.text = str(project_preferences['width'])
    height1 = ET.SubElement(figure_element, 'height')  # Height
    height1.text = str(project_preferences['height'])
    colormap1 = ET.SubElement(figure_element, 'color_map1')  # color_map1
    colormap1.text = project_preferences['color_map1']
    colormap2 = ET.SubElement(figure_element, 'color_map2')  # color_map2
    colormap2.text = project_preferences['color_map2']
    fontsize1 = ET.SubElement(figure_element, 'font_size')  # font_size
    fontsize1.text = str(project_preferences['font_size'])
    linewidth1 = ET.SubElement(figure_element, 'line_width')  # LineWidth
    linewidth1.text = str(project_preferences['line_width'])
    grid1 = ET.SubElement(figure_element, 'grid')  # Grid
    grid1.text = str(project_preferences['grid'])
    format1 = ET.SubElement(figure_element, "format")  # Format
    format1.text = str(project_preferences['format'])
    reso1 = ET.SubElement(figure_element, "resolution")  # Resolution
    reso1.text = str(project_preferences['resolution'])
    fish1 = ET.SubElement(figure_element, "fish_name_type")  # FishNameType
    fish1.text = str(project_preferences['fish_name_type'])
    marker1 = ET.SubElement(figure_element, "marker")  # Marker
    marker1.text = str(project_preferences['marker'])

    # save new xml file
    if name_prj != '':
        fname = os.path.join(path_prj, name_prj + '.habby')
        tree.write(fname, pretty_print=True)


def load_project_preferences(path_prj, name_prj):
    """
    This function loads the figure option saved in the xml file and create a dictionnary will be given to the functions
    which create the figures to know the different options chosen by the user. If the options are not written, this
    function uses data by default which are in the fonction create_default_project_preferences_dict().

    :param path_prj: the path to the xml project file
    :param name_prj: the name to this file
    :return: the dictionary containing the figure options

    """
    # init
    project_preferences = dict()

    # save path and project name
    project_preferences["name_prj"] = name_prj
    project_preferences["path_prj"] = path_prj


    fname = os.path.join(path_prj, name_prj + '.habby')
    if not os.path.isfile(fname) and name_prj != '':  # no project exists
        pass
    elif name_prj == '':
        pass
    elif not os.path.isfile(fname):  # the project is not found
        print('Warning: No project file (.habby) found.\n')
    else:
        parser = ET.XMLParser(remove_blank_text=True)
        doc = ET.parse(fname, parser)
        root = doc.getroot()

        # general
        project_preferences['path_last_file_loaded'] = root.find(".//path_last_file_loaded").text
        project_preferences['file_log'] = root.find(".//file_log").text
        project_preferences['file_restart'] = root.find(".//file_restart").text
        project_preferences['save_log'] = root.find(".//save_log").text
        project_preferences['user_name'] = root.find(".//user_name").text
        project_preferences['description'] = root.find(".//description").text
        project_preferences['version_habby'] = root.find(".//version_habby").text
        project_preferences['path_bio'] = root.find(".//path_bio").text
        project_preferences['path_input'] = root.find(".//path_input").text
        project_preferences['path_hdf5'] = root.find(".//path_hdf5").text
        project_preferences['path_figure'] = root.find(".//path_figure").text
        project_preferences['path_text'] = root.find(".//path_text").text
        project_preferences['path_gis'] = root.find(".//path_gis").text
        project_preferences['path_3d'] = root.find(".//path_3d").text
        project_preferences['physic_tabs'] = eval(root.find(".//physic_tabs").text)
        project_preferences['stat_tabs'] = eval(root.find(".//stat_tabs").text)
        project_preferences['language'] = int(root.find(".//language").text)
        project_preferences['copy_input_files'] = eval(root.find(".//copy_input_files").text)
        project_preferences['cut_mesh_partialy_dry'] = eval(root.find(".//cut_mesh_partialy_dry").text)
        project_preferences['min_height_hyd'] = float(root.find(".//min_height_hyd").text)
        project_preferences['erase_id'] = eval(root.find(".//erase_id").text)

        # output (first element list == for .hyd and second element list == for .hab)
        project_preferences['mesh_whole_profile'] = eval(root.find(".//mesh_whole_profile").text)
        project_preferences['point_whole_profile'] = eval(root.find(".//point_whole_profile").text)
        project_preferences['mesh_units'] = eval(root.find(".//mesh_units").text)
        project_preferences['point_units'] = eval(root.find(".//point_units").text)
        project_preferences['elevation_whole_profile'] = eval(root.find(".//elevation_whole_profile").text)
        project_preferences['variables_units'] = eval(root.find(".//variables_units").text)
        #project_preferences['habitat_text'] = eval(root.find(".//habitat_text").text)  # always True
        project_preferences['detailled_text'] = eval(root.find(".//detailled_text").text)
        project_preferences['fish_information'] = eval(root.find(".//fish_information").text)
        project_preferences['vertical_exaggeration'] = int(root.find(".//vertical_exaggeration").text)
        project_preferences['pvd_variable_z'] = root.find(".//pvd_variable_z").text

        # figures
        project_preferences['height'] = float(root.find(".//height").text)
        project_preferences['width'] = float(root.find(".//width").text)
        project_preferences['color_map1'] = root.find(".//color_map1").text
        project_preferences['color_map2'] = root.find(".//color_map2").text
        project_preferences['font_size'] = int(root.find(".//font_size").text)
        project_preferences['line_width'] = int(root.find(".//line_width").text)
        project_preferences['grid'] = eval(root.find(".//grid").text)
        project_preferences['format'] = root.find(".//format").text
        project_preferences['resolution'] = int(root.find(".//resolution").text)
        project_preferences['fish_name_type'] = root.find(".//fish_name_type").text
        project_preferences['marker'] = eval(root.find(".//marker").text)

    return project_preferences


def set_lang_fig(nb_lang, path_prj, name_prj):
    """
    This function write in the xml file in which langugage the figures should be done. This is kept in the
    group of attribute in the Figure_Option
    :param lang: An int indicating the langugage (0 for english, 1 for french,...)
    :param path_prj: the path to the project
    :param name_prj: the name of the project
    """

    # save the data in the xml file
    # open the xml project file
    fname = os.path.join(path_prj, name_prj + '.habby')
    # save the name and the path in the xml .prj file
    if not os.path.isfile(fname):
        # print('Error: project is not found \n')
        return
    else:
        parser = ET.XMLParser(remove_blank_text=True)
        doc = ET.parse(fname, parser)
        root = doc.getroot()
        child1 = root.find(".//general")
        if child1 is not None:  # modify existing option
            langfig1 = root.find(".//lauguage")
            if langfig1 is None:
                langfig1 = ET.SubElement(child1, "lauguage")
            langfig1.text = str(nb_lang)
            doc.write(fname, pretty_print=True)


def set_project_type(physical, statistical, path_prj, name_prj):
    """
    This function write in the xml file in which langugage the figures should be done. This is kept in the
    group of attribute in the Figure_Option
    :param lang: An int indicating the langugage (0 for english, 1 for french,...)
    :param path_prj: the path to the project
    :param name_prj: the name of the project
    """
    # open the xml project file
    fname = os.path.join(path_prj, name_prj + '.habby')
    # save the name and the path in the xml .prj file
    if not os.path.isfile(fname):
        # print('Error: project is not found \n')
        return
    else:
        # project_type
        parser = ET.XMLParser(remove_blank_text=True)
        doc = ET.parse(fname, parser)
        root = doc.getroot()
        general_element = root.find('.//general')
        physic_tabs_element = general_element.find('physic_tabs')
        if physic_tabs_element is None:
            physic_tabs_element = ET.SubElement(general_element, 'physic_tabs')
            physic_tabs_element.text = str(physical)
        else:
            physic_tabs_element.text = str(physical)
        stat_tabs_element = general_element.find('stat_tabs')
        if stat_tabs_element is None:
            stat_tabs_element = ET.SubElement(general_element, 'stat_tabs')
            stat_tabs_element.text = str(statistical)
        else:
            stat_tabs_element.text = str(statistical)
        doc.write(fname, pretty_print=True)
