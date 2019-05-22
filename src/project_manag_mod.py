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
        shutil.copy(os.path.join('src_GUI', 'log0.txt'), os.path.join(path_prj, name_prj + '.log'))
        shutil.copy(os.path.join('src_GUI', 'restart_log0.txt'), os.path.join(path_prj,
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
    path_shapefile = os.path.join(path_prj, 'output', 'shapefiles')
    pathother_child = ET.SubElement(path_element, "Path_Shape")
    pathother_child.text = os.path.join("output", "shapefiles")

    # path visualisation
    path_para = os.path.join(path_prj, 'output', 'visualisation')
    pathpara_child = ET.SubElement(path_element, "Path_Visualisation")
    pathpara_child.text = os.path.join("output", "visualisation")

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