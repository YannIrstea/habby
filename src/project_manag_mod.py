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
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import shutil


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
    fname = os.path.join(path_prj, name_prj + '.xml')
    # save the name and the path in the xml .prj file
    if not os.path.isfile(fname):
        # print('Error: project is not found \n')
        return
    else:
        doc = ET.parse(fname)
        root = doc.getroot()
        child1 = root.find(".//Figure_Option")
        if child1 is not None:  # modify existing option
            langfig1 = root.find(".//LangFig")
            if langfig1 is None:
                langfig1 = ET.SubElement(child1, "LangFig")
            langfig1.text = str(nb_lang)
            doc.write(fname)


def load_project_preferences(path_prj, name_prj):
    """
    This function loads the figure option saved in the xml file and create a dictionnary will be given to the functions
    which create the figures to know the different options chosen by the user. If the options are not written, this
    function uses data by default which are in the fonction create_default_project_preferences().

    :param path_prj: the path to the xml project file
    :param name_prj: the name to this file
    :return: the dictionary containing the figure options

    """

    project_preferences = create_default_project_preferences()
    fname = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(fname) and name_prj != '':  # no project exists
        pass
    elif name_prj == '':
        pass
    elif not os.path.isfile(fname):  # the project is not found
        print('Warning: No project file (.xml) found.\n')
    else:
        doc = ET.parse(fname)
        root = doc.getroot()
        child1 = root.find(".//Figure_Option")
        if child1 is not None:  # modify existing option
            # other
            langfig1 = root.find(".//LangFig")

            # general
            CutMeshPartialyDry = root.find(".//CutMeshPartialyDry")
            hopt1 = root.find(".//MinHeight")
            erase1 = root.find(".//EraseId")

            # output
            mesh_whole_profile = root.find(".//mesh_whole_profile")
            point_whole_profile = root.find(".//point_whole_profile")
            mesh_units = root.find(".//mesh_units")
            point_units = root.find(".//point_units")
            vertical_exaggeration = root.find(".//vertical_exaggeration")
            elevation_whole_profile = root.find(".//elevation_whole_profile")
            variables_units = root.find(".//variables_units")
            detailled_text = root.find(".//detailled_text")
            fish_information = root.find(".//fish_information")

            # figures
            width1 = root.find(".//Width")
            height1 = root.find(".//Height")
            colormap1 = root.find(".//ColorMap1")
            colormap2 = root.find(".//ColorMap2")
            fontsize1 = root.find(".//FontSize")
            linewidth1 = root.find(".//LineWidth")
            grid1 = root.find(".//Grid")
            format1 = root.find(".//Format")
            marker1 = root.find(".//Marker")
            reso1 = root.find(".//Resolution")
            fish1 = root.find(".//FishNameType")

            try:
                # other
                if langfig1 is not None:
                    project_preferences['language'] = int(langfig1.text)

                # general
                if CutMeshPartialyDry is not None:
                    project_preferences['CutMeshPartialyDry'] = eval(CutMeshPartialyDry.text)
                if hopt1 is not None:
                    project_preferences['min_height_hyd'] = float(hopt1.text)
                if erase1 is not None:
                    project_preferences['erase_id'] = eval(erase1.text)

                # output
                if mesh_whole_profile is not None:
                    project_preferences['mesh_whole_profile'] = eval(mesh_whole_profile.text)
                if point_whole_profile is not None:
                    project_preferences['point_whole_profile'] = eval(point_whole_profile.text)
                if mesh_units is not None:
                    project_preferences['mesh_units'] = eval(mesh_units.text)
                if point_units is not None:
                    project_preferences['point_units'] = eval(point_units.text)
                if vertical_exaggeration is not None:
                    project_preferences['vertical_exaggeration'] = int(vertical_exaggeration.text)
                if elevation_whole_profile is not None:
                    project_preferences['elevation_whole_profile'] = eval(elevation_whole_profile.text)
                if variables_units is not None:
                    project_preferences['variables_units'] = eval(variables_units.text)
                if detailled_text is not None:
                    project_preferences['detailled_text'] = eval(detailled_text.text)
                if fish_information is not None:
                    project_preferences['fish_information'] = eval(fish_information.text)

                # figures
                if width1 is not None:
                    project_preferences['width'] = float(width1.text)
                if height1 is not None:
                    project_preferences['height'] = float(height1.text)
                if colormap1 is not None:
                    project_preferences['color_map1'] = colormap1.text
                if colormap2 is not None:
                    project_preferences['color_map2'] = colormap2.text
                if fontsize1 is not None:
                    project_preferences['font_size'] = int(fontsize1.text)
                if linewidth1 is not None:
                    project_preferences['line_width'] = int(linewidth1.text)
                if grid1 is not None:
                    project_preferences['grid'] = eval(grid1.text)
                if format1 is not None:
                    project_preferences['format'] = format1.text
                if reso1 is not None:
                    project_preferences['resolution'] = int(reso1.text)
                if fish1 is not None:
                    project_preferences['fish_name_type'] = fish1.text
                if marker1 is not None:
                    project_preferences['marker'] = eval(marker1.text)

            except ValueError:
                print('Error: Figure Options are not of the right type.\n')

    return project_preferences


def create_default_project_preferences():
    """
    This function creates the default dictionnary of project user preferences.
    """
    # init
    project_preferences = dict()

    # other
    project_preferences['language'] = 0  # 0 english, 1 french

    # general
    project_preferences['CutMeshPartialyDry'] = True  # cut of not mesh partialy wet
    project_preferences['min_height_hyd'] = 0.001  # node mesh minimum water height consider like dry
    project_preferences['erase_id'] = True  # erase file (hdf5, outputs) if exist. if not set date/hour in filename

    # output (first element list == for .hyd and second element list == for .hab)
    project_preferences['mesh_whole_profile'] = [False, False]  # shapefile mesh whole profile
    project_preferences['point_whole_profile'] = [False, False]  # shapefile point whole profile
    project_preferences['mesh_units'] = [False, False]  # shapefile mesh by unit
    project_preferences['point_units'] = [False, False]  # shapefile point by unit
    project_preferences['vertical_exaggeration'] = 10  # paraview vertical exageration
    project_preferences['elevation_whole_profile'] = [False, False]  # mesh .stl of topography whole profile (vertical_exaggeration)
    project_preferences['variables_units'] = [False, False]  # mesh .pvd and .vtu by unit (vertical_exaggeration)
    project_preferences['detailled_text'] = [False, False]  # .txt with detail values by mesh
    project_preferences['fish_information'] = [False, False]  # image of fish informations

    # figures
    project_preferences['height'] = 7
    project_preferences['width'] = 10
    project_preferences['color_map1'] = 'coolwarm'
    project_preferences['color_map2'] = 'jet'
    project_preferences['font_size'] = 12
    project_preferences['line_width'] = 1
    project_preferences['grid'] = False  # grid on plot
    project_preferences['format'] = 3  # png+pdf, png, jpeg, pdf, not saved
    project_preferences['resolution'] = 800  # dpi
    project_preferences['fish_name_type'] = 0  # latin_name, french, english, code_alternative
    project_preferences['marker'] = True  # Add point to line plot

    return project_preferences


def create_project_structure(path_prj, logon, version, username_prj, descri_prj, path_bio_default):
    # get name
    name_prj = os.path.basename(path_prj)
    # create the root <root> and general tab
    root_element = ET.Element("root")
    tree = ET.ElementTree(root_element)
    general_element = ET.SubElement(root_element, "General")
    # create all child
    child = ET.SubElement(general_element, "Project_Name")
    child.text = name_prj
    path_child = ET.SubElement(general_element, "Path_Project")
    path_child.text = path_prj
    path_last_file_loaded_child = ET.SubElement(general_element, "Path_last_file_loaded")
    path_last_file_loaded_child.text = path_prj
    # log
    log_element = ET.SubElement(general_element, "Log_Info")
    pathlog_child = ET.SubElement(log_element, "File_Log")
    pathlog_child.text = os.path.join(name_prj + '.log')
    pathlog_child = ET.SubElement(log_element, "File_Restart")
    pathlog_child.text = os.path.join('restart_' + name_prj + '.log')
    savelog_child = ET.SubElement(log_element, "Save_Log")
    savelog_child.text = str(logon)

    # create the log files by copying the existing "basic" log files (log0.txt and restart_log0.txt)
    if name_prj != '':
        shutil.copy(os.path.join('files_dep', 'log0.txt'), os.path.join(path_prj, name_prj + '.log'))
        shutil.copy(os.path.join('files_dep', 'restart_log0.txt'), os.path.join(path_prj,
                                                                              'restart_' + name_prj +
                                                                              '.log'))
    # more precise info
    user_child = ET.SubElement(general_element, "User_Name")
    user_child.text = username_prj
    des_child = ET.SubElement(general_element, "Description")
    des_child.text = descri_prj
    # we save here only the version number of when the project was saved the first time.
    # if a project is used in two version, it has the first version number to insure back-compatibility.
    # let say on version 1.5, we assure compatibility in version 1.4, but that we do assure compatibility
    # for version 1.4 in version 1.6. In this case, we should not have the version number 1.5 in the xml.
    ver_child = ET.SubElement(general_element, 'Version_HABBY')
    ver_child.text = str(version)

    # general paths
    path_element = ET.SubElement(general_element, "Paths")

    # path bio
    pathbio_child = ET.SubElement(path_element, "Path_Bio")
    pathbio_child.text = path_bio_default

    # path input
    path_input = os.path.join(path_prj, 'input')
    pathinput_child = ET.SubElement(path_element, "Path_Input")
    pathinput_child.text = 'input'

    # path hdf5
    path_hdf5 = os.path.join(path_prj, 'hdf5')
    pathhdf5_child = ET.SubElement(path_element, "Path_Hdf5")
    pathhdf5_child.text = 'hdf5'

    # path figures
    path_im = os.path.join(path_prj, 'output', 'figures')
    pathbio_child = ET.SubElement(path_element, "Path_Figure")
    pathbio_child.text = os.path.join("output", "figures")

    # path text output
    path_text = os.path.join(path_prj, 'output', 'text')
    pathtext_child = ET.SubElement(path_element, "Path_Text")
    pathtext_child.text = os.path.join("output", "text")

    # path shapefile
    path_shapefile = os.path.join(path_prj, 'output', 'GIS')
    pathother_child = ET.SubElement(path_element, "Path_Shape")
    pathother_child.text = os.path.join("output", "GIS")

    # path 3D
    path_para = os.path.join(path_prj, 'output', '3D')
    pathpara_child = ET.SubElement(path_element, "Path_Visualisation")
    pathpara_child.text = os.path.join("output", "3D")

    # save new xml file
    if name_prj != '':
        fname = os.path.join(path_prj, name_prj + '.xml')
        tree.write(fname)

    # create a default directory for the figures and the hdf5
    if not os.path.exists(path_input):
        os.makedirs(path_input)
    if not os.path.exists(path_hdf5):
        os.makedirs(path_hdf5)
    if not os.path.exists(os.path.join(path_prj, 'output')):
        os.makedirs(os.path.join(path_prj, 'output'))
    if not os.path.exists(path_im):
        os.makedirs(path_im)
    if not os.path.exists(path_text):
        os.makedirs(path_text)
    if not os.path.exists(path_shapefile):
        os.makedirs(path_shapefile)
    if not os.path.exists(path_para):
        os.makedirs(path_para)

    # create the concurrency file
    filenamec = os.path.join(os.path.join(path_prj, 'hdf5'), 'check_concurrency.txt')
    if os.path.isdir(os.path.join(path_prj, 'hdf5')):
        with open(filenamec, 'wt') as f:
            f.write('open')
    return path_last_file_loaded_child
