"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import xml.etree.ElementTree as Etree
import os
import re
import numpy as np
import bisect
from io import StringIO
import sys
import time
from matplotlib.pyplot import axis, plot, step, figure, xlim, ylim, xlabel, ylabel, title, figure, text, legend, \
    show, subplot, fill_between, rcParams, savefig, close, rcParams,suptitle
import matplotlib as mpl
from src import manage_grid_8
from src import load_hdf5
from src_GUI import output_fig_GUI


def open_hec_hec_ras_and_create_grid(name_hdf5, path_hdf5, name_prj, path_prj, model_type, namefile, pathfile,
                                     interpo_choice, path_im, save_fig1d, pro_add=1, q=[], print_cmd=False, fig_opt=[]):
    """
    This function open the hec_ras data and creates the 2D grid from the 1.5 data. It is called by the class HEC_RAS1D
    in a second thread to not freeze the GUI.

    :param name_hdf5: the name of the hdf5 to be created (string)
    :param path_hdf5: the path to the hdf5 to be created (string)
    :param model_type: the name of the model (hec_ras in most case, but given as argument in case we change
           the form of the name)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param namefile: the name of the geo file and the data file, which contains respectively geographical data and
           the ouput data (see open_hec_ras() for more precision) -> list of string
    :param pathfile: the absolute path to the file chosen into namefile
    :param interpo_choice: the interpolation type (int: 0,1,2 or 3). See grid_and_interpo() for mroe details.
    :param path_im: the path to where to save the image
    :param save_fig1d: create and save the figure related to the loading of the data (profile and so on)
    :param pro_add: the number of addictional profile (one used for interpolation_choice 1 and 2)
    :param q: used in the second thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param fig_opt: the options to crete the figure if save_fig1d is True

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line. We make the switch here.

    """
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    # load the hec-ra data (the function is just below)
    [coord_pro, vh_pro, nb_pro_reach, sim_name] = open_hecras(namefile[0], namefile[1], pathfile[0], pathfile[1], path_im,
                                                    save_fig1d, fig_opt)
    # manager error
    if save_fig1d:  # to avoid problem with matplotlib
        close()
    if coord_pro == [-99] or len(vh_pro) <1:
        print('Error: HEC-RAS data not loaded')
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # create the grid
    [ikle_all_t, point_all_t, point_c_all_t, inter_vel_all_t, inter_h_all_t] \
        = manage_grid_8.grid_and_interpo(vh_pro, coord_pro, nb_pro_reach, interpo_choice, pro_add)

    # manage error
    if ikle_all_t == [-99]:
        print('Error: HEC-RAS data could not be tranfred to the grid. \n')
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # save the hdf5 file
    load_hdf5.save_hdf5(name_hdf5, name_prj, path_prj, model_type, 1.5, path_hdf5, ikle_all_t, point_all_t,
                        point_c_all_t, inter_vel_all_t, inter_h_all_t, [], coord_pro, vh_pro, nb_pro_reach,
                        sim_name=sim_name)

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def open_hecras(geo_file, res_file, path_geo, path_res, path_im, save_fig=False, fig_opt =[]):
    """
    This function will open HEC-RAS outputs, i.e. the .geo file and the outputs (either .XML, .sdf or .rep) from HEC-RAS.
    All arguments from this function are string.

    :param geo_file: the name of .goX (example .go3) file which is an output from hec-ras containg the profile data
    :param res_file: the name of O0X.xml file for the name of the .sdf file  or the name of the .rep file (output data)
    :param path_res: path to the result file
    :param path_geo: path to the geo file
    :param path_im: the path to the folder where the images should be saved
    :param save_fig: if True image is saved
    :param fig_opt: the figure option is save_fig is True
    :return: coord_pro (for each profile, x,y,elev, dist along the profile), vh_pro
            (for each profile, dist along the profile, water height, velocity). Both variable are a list of numpy array.

    **How to obtain the input files**

    To obtain the xml file in HEC-RAS version 4:

    *  open the project in HEC-RAS.
    *   click on File , then export geometry and result (RAS Mapper), then OK

    To obtain the sdf file in HEC-RAS version 5 which should be used if the model is georeferenced:

    *    click on File, then Export GIS data
    *    Export all reaches (select Reaches to export -. Full List -> Ok)
    *    Export all needed profile (select Profile to export -> Select all -> ok)

    To obtain the report file .rep in HEC-RAS version which should be used if the model is NOT geo-referenced

    *   click on File, generate report
    *   Select Flow data and Geometry data in input data and, in Specific Table, select Flow distribution and
        Cross section Table

    **Technical comments**

    This is function which loads the hec_ras inputs in 1D for the version 4 and 5 of HEC-RAS. It accepts different type
    of hec-ras output as input and calls the appropriate sub-function for each input file.  The geometrical data is
    always given in the geo file (with the extension g01, G01, g02, G02, g03, etc.). The output data can be in an xml
    file for the hec-ras in the version 4, an sdf file for hec-ras in version 5 or a .rep file in the version 5 if the
    model is not georeferenced. The xml file is the format which has been tested the most.

    First, it loads the geometrical data. Then it select the function to load the output data and loads it. Then, it
    transforms the loaded data in a (x,y) coordinates system. Indeed, most of the data in hec-ras is given by indicating
    a profile (which crossed the modelled river) and the distance along this profile. For HABBY, it is better to get
    (x,y) coordinates. Then it create figure if asked by the switch “save_fig”. Finally, it updates the forms of the
    output to be coherent with the dist_velocity_hecras function.  This way, in HABBY, the output from mascaret and
    rubar after the velocity distribution have the same form than the output from hec-ras, which is useful afterwards
    to save all these data in the hdf5 file.

    """
    xy_h = [-99]
    zone_v = [-99]
    sim_name = []

    # load the geometry file which contains info on the profile and the geometry
    [data_profile, coord_pro_old, coord_r, reach_name, data_bank, nb_pro_reach] = open_geofile(geo_file, path_geo)
    # test if data could be extracted
    if data_profile == [-99]:
        return [-99], [-99], [-99], [-99]

    # load the xml, rep, or sdf file to get velocity and wse
    blob, ext = os.path.splitext(res_file)
    if ext == ".xml":
         [vel, wse, riv_name, nb_sim, sim_name] = open_xmlfile(res_file, reach_name, path_res)
    elif ext == ".sdf":
        try:
            [vel, wse, riv_name, nb_sim, sim_name] = open_sdffile(res_file, reach_name, path_res)
        except ValueError:
            print("Error: Cannot open .sdf file. Is the model georeferenced? If not, use the .rep file.\n")
            return [-99], [-99], [-99], [-99]

    elif ext == ".rep":
        [vel, wse, riv_name, nb_sim, sim_name] = open_repfile(res_file, reach_name, path_res, data_profile, data_bank)
    else:
        print("Warning: The file containing the results is not "
              "in XML, rep or sdf format. HABBY try to read it as XML file.\n")
        [vel, wse, riv_name, nb_sim, sim_name] = open_xmlfile(res_file, reach_name, path_res)
    # if data could not be extracted
    if vel == [-99]:
        return  [-99], [-99], [-99], [-99]
    # get water height in the (x,y coordinate) and get the velocity in the (x,y) coordinates
    # velocity is by zone (between 2 points) and height is on the node
    # maximum distance between two velocity point: yTO BE DEFINED
    try:
        [xy_h, zone_v] = find_coord_height_velocity(coord_pro_old, data_profile, vel, wse, nb_sim, 1000)
    except IndexError:
        print('Error: The number of time steps might not be not coherent between geo and output files.')
        return [-99], [-99], [-99], [-99]
    if xy_h == [-99]:
        return [-99], [-99], [-99], [-99]
    # plot and check
    if save_fig:
        if fig_opt['time_step'][0] == -99:
            tfig = range(0, len(zone_v))
        else:
            tfig = fig_opt['time_step']
            if not isinstance(tfig, (list, tuple)):
                tfig = tfig.split(',')
            try:
                tfig = list(map(int, tfig))
            except ValueError:
                print('Error: Time step was not recognized. \n')
                return
        pro = [0, 1, 2]
        for t in tfig:
            t = int(t)
            if t < len(xy_h):
                figure_xml(data_profile, coord_pro_old, coord_r, xy_h, zone_v, pro, path_im, fig_opt,  t, riv_name)

    # update the form of the vector to be coherent with rubar and mascaret
    [coord_pro, vh_pro, nb_pro_reach] = update_output(zone_v, coord_pro_old, data_profile, xy_h, nb_pro_reach)

    return coord_pro, vh_pro, nb_pro_reach, sim_name


def open_xmlfile(xml_file, reach_name, path):
    """
    This function open the xml file from HEC-RAS v4 to get the velocity and water surface elevation. To know how to
    obtain this xml file, read the doc of open_hecras.

    :param xml_file: the name of O0X.xml file from HEC-RAS. (string)
    :param reach_name: a list of string containing the name of the reaches/rivers in the order of the geo file
           which might not be the one of the xml file.
    :param path: path to the xml file (string)
    :return: velocity and the water surface elevation for each river profiles (list of np.array),
            the number of simulation(int) and the name of the river profile (list of string)

    **Technical comments**

    To load the xml file, we first call the load_xml function. It is a function which check that the xml file is well
    formed and which return the “root” part fo the xml. With this “root”, it is possible to load other part of the xml
    file using the Etree module.

    Then, we load the velocity and water height data from the xml file. We also load the name of the profiles and of
    the reach names.  Next, we pass the data into float. For each velocity of height point, we get its position along
    the profile (see below for format) and the value at this point.

    Finally, we re-order the data as in the geo file. Indeed, it is possible to have different order between the reaches
    in the geo file and in the xml file. The last part of this function is there to order all the data as in the geo
    file. There is a function reorder_reach which does something similar, but could not be used by the output from the
    xml file (it is slighty different). However the reorder_reach function and this part of the open_xml function is
    very similar.
    """

    # load the xml file
    root = load_xml(xml_file, path)
    if root == [-99]:  # if error arised
        print("Error: the XML file could not be read.\n")
        return [-99], [-99], [-99], [-99]

    # find the velocity in the XML file
    # .// all child ./ only first child
    try:  # check that the data is not empty
        vel = root.findall(".//Velocity")
    except AttributeError:
        print("Error: Velocity data cannot be read from the XML file.\n")
        return [-99], [-99], [-99], [-99]
    if len(vel) == 0:
        print('Warning: Velocity data from XML is empty.\n')

    # find where all water suface elevation are
    try:
        wse = root.findall(".//WSE")
    except AttributeError:
        print("Error: water surface elevation cannot be read from the XML file.\n")
        return [-99], [-99], [-99], [-99]
    if len(wse) == 0:
        print('Warning: Height data from XML is empty.\n')

    # find profile name and if there is more than one profile
    try:
        sim_name = root.findall(".//ProfileNames")
        sim_name = str(sim_name[0].text)
        sim_name = sim_name[1:-1] # erase firt and last " sign
        sim_name = sim_name.split('" "')
        nb_sim = len(sim_name)
        for si in range(0, nb_sim):
            sim_name[si] = sim_name[si].replace(':', '_')
    except AttributeError:
        print("Warning: the number and name of the simulation cannot be read from the XML file.\n")
        nb_sim = 1

    # find the name of the river station
    try:
        riv_name_xml = root.findall(".//RiverStation")
        riv_name = []
        for i in range(0, len(riv_name_xml)):
            for s in range(0, nb_sim):
                riv_name_i = str(riv_name_xml[i].text)
                riv_name.append(riv_name_i)
    except AttributeError:
        print("Warning: the name of the river station cannot be read from the XML file.\n")
        riv_name = []

    # transform the Element data into float
    if len(vel) == len(wse):
        nbstat = len(vel)  # number of profiles
    else:
        nbstat = min(len(vel), len(wse))
        print('Warning: the length of height data and velocity data do not match.\n')
    data_vel = []  # liste of profiles
    data_wse = []
    try:
        for i in range(0, nbstat):
            vel_str = str(vel[i].text)  # cannot convert to float directly
            xvel = vel_str.split()  # get a list of str containing (xi,v)
            nb_pro = len(xvel)  # might change between one profile and the next

            wse_str = str(wse[i].text)  # WSE
            wse_sep = wse_str.split(',')  # separating xi and v
            data_wse.append(float(wse_sep[1]))

            data_vel_pro = np.zeros((nb_pro, 2))
            for j in range(0, nb_pro):
                xvel_sep = xvel[j].split(',')  # separating xi and v
                # finally filled the float array
                data_vel_pro[j, 0] = float(xvel_sep[0])
                data_vel_pro[j, 1] = float(xvel_sep[1])

            data_vel.append(data_vel_pro)
    except TypeError:
        print('Error: The velocity or height data could not be extracted. Format of the XML file should be checked.\n')
        return [-99], [-99], [-99], [-99]

    # re-oder the reaches and river as in the .geo file
    if len(reach_name) > 1:
        data_vel2 = np.copy(data_vel)
        data_wse2 = np.copy(data_wse)
        riv_name2 = np.copy(riv_name)
        # reach order in the xml file
        name_reach_xml = []
        river_xml = root.findall(".//River")
        reach_xml = root.findall(".//Reach")
        for p in range(0, nbstat):
            reach_xml_p = str(reach_xml[int(np.floor(p/nb_sim))].text)
            river_xml_p = str(river_xml[int(np.floor(p/nb_sim))].text)
            name_reach_p = river_xml_p+','+reach_xml_p
            name_reach_xml.append(name_reach_p)
        name_reach_xml = np.array(name_reach_xml)
        m = 0
        for r in range(0, len(reach_name)):
            f_reach = np.where(name_reach_xml == reach_name[r])
            f_reach = np.squeeze(f_reach)
            for i in range(0, len(f_reach)): # list in this case cannot be changed to numpy.array
                data_wse[m+i] = data_wse2[f_reach[i]]
                data_vel[m+i] = data_vel2[f_reach[i]]
                riv_name[m+i] = riv_name2[f_reach[i]]

            m += len(f_reach)
        if m == 0:
            print('Warning: The reach and rivers names of the .geo file could not be found in the xml file.\n')

    riv_name = riv_name[::nb_sim]  # get the name only once

    return data_vel, data_wse, riv_name, nb_sim, sim_name


def load_xml(xml_file, path):
    """
    This is a function used by openxml_file and opengml_file to load an xml file.

    :param xml_file: the name of an xml file (string)
    :param path: the path where the xml file is (string)
    :return: the loaded data from the XML file in the form of the root of the xml file.
    """
    # check that the xml file has the right extension
    blob, ext_xml = os.path.splitext(xml_file)
    if ext_xml == '.xml' or ext_xml == '.gml' or ext_xml == '.xcas':
        pass
    else:
        print("Warning: File should be of type XML or GML \n")

    # load the XML file
    try:
        try:
            docxml = Etree.parse(os.path.join(path, xml_file))
            root = docxml.getroot()
        except IOError:
            print("Error: the file "+xml_file+" does not exist\n")
            return [-99]
    except Etree.ParseError:
        print('Error: the XML is not well-formed.\n')
        return [-99]

    return root


def open_geofile(geo_file, path):
    """
    This function opens the geometry file (.g0X) from Hecr-rad. It extracts the (x,z) from each profile
    and the (x,y) if georeferenced,

    :param geo_file: the name of the Hec-Ras geometry file (string)
    :param path: the path to the geo file (string)
    :return: A list with each river profile (each profile is represented by a numpy array with the x and the altitude
             of each point in the profile), the coordinate of the profile (list of np.array),
             the coordinate of the river and the name of the reaches/ river in the file order (list of string)

    **Technical comments**

    The geofile is a text file with contains the geographical information. Because it is written to be read by human,
    it is complicated to load and regular expression are needed. It is written profile by profile.

    Generally, to give a position, hec-ras indicates the profile number and the distance along this profile. In addition,
    data can be georeferenced or not. If it is geo-referenced we have some data in an (x,y) form. Otherwise, we only
    have geometrical data in the form (profile, dist).

    First, for each profile, we get the elevation of the points forming each profile in the form (dist, elevation).
    The list of elevation for each profile starts with the keyword “Sta/Elev”. The data found in the text file is in a
    string format. We use the function pass_in_float_from_geo to pass it in float. It is usually done using the function
    float. However, there are cases where there are no space between two number. However, in this case, the number of
    character per number is constant. In this case, we separate the number first.

    Then, we get the coordinate of the river. If no coordinate are available the river is assumed to be straight. Next,
    we get the bank limit (even if we do not really used afterwards), and the name of the reach. It is also important
    to save the order in which the names of the reach are given. Indeed, we want this order to be the same in all
    functions, but they can be different between the geo file and the data output.

    Next, we want to get the position (x,y) of each profile. If it is georeferenced, we will be able to get this
    position directly from the file and put it in the data_dist_str variable. We will then pass it to float. If not,
    we will use the function coord_profil_non_georeferenced to estimate the position of the profile (see below).

    If the profile is not georeferenced, it is important to have the distance between two profile, so we extract the
    information from the geo file in all cases (georeferenced or not). The last profile of a reach does not have a
    distance to the next (not existing) profile. However, if a profile does not have a distance to the next profile
    and is not the last profile, we ignore this profile. It is usually not a problem because this profile is usually
    not a “real” profile, but the representation of a bridge or a culvert.
    """

    failload = [-99],[-99], [-99], '-99', [-99], [-99]
    # check that the geo file has the right extension (.goX)
    blob, ext_geo = os.path.splitext(geo_file)
    if ext_geo[:3] == '.G0':
        print("Warning: File of G0X type.\n")
    elif ext_geo[:3] != '.g0':
        print("Warning: File should be of type .g0X such as .g01 ou .g02.\n")

    # open the geo file
    try:
        with open(os.path.join(path, geo_file), 'rt') as f:
            data_geo = f.read()
    except IOError or UnicodeDecodeError:
        print("Error: the file "+geo_file+" does not exist.\n")
        return failload

    # find the (x,z) data related to the profiles.
        # HEC_RAS manual p5-4: the geometry file is for-the-most-part self explanotary.
        # Unfortunately not for me. :-(
        # look for all Stat/Elev, then get rid of everything until next line
        # then save all data until not a digit (or white space) arrive

    exp_reg1 = "Sta/Elev=\s+\d+\s*\n([\s+\d+\.-]+)"
    data_profile_str = re.findall(exp_reg1, data_geo, re.DOTALL)
    if not data_profile_str:
        print("Error: no profile found, the geometry file might not be in the right format.\n")
        return failload
    data_profile = []
    try:
        for i in range(0, len(data_profile_str)):
                xz = pass_in_float_from_geo(data_profile_str[i], 8)
                data_profile.append(xz)  # fill a list with an array (x,z) for each profile
    except ValueError:
        print('Error: The profile data could be extracted from the geometry file. The format should be checked. \n')
        return failload

    # load the coordinate of the river
    exp_reg2 = 'Reach\s+XY=\s+\d+\s*\n([\s+\d+\.-]+)'
    data_river_str = re.findall(exp_reg2, data_geo, re.DOTALL)
    # case of a straight river
    if not data_river_str:
        exp_reg21 = 'Rch X Y Up \& X Y Dn=([\s+\d+\.-]+,[\s+\d+\.-]+,[\s+\d+\.-]+,[\s+\d+\.-]+)'
        data_river_str = re.findall(exp_reg21, data_geo, re.DOTALL)
        data_river_str[0] = data_river_str[0].replace(',', ' ')
        if data_river_str:
            print('Warning: The river is assumed to be straight.\n')
    if not data_river_str:
        print('Warning: no river found, the geometry file might not be in the right format.\n')
    try:
        data_river = []
        for i in range(0, len(data_river_str)):
            data_river.append(pass_in_float_from_geo(data_river_str[i], 16))
    except ValueError:
        print('Error: The river data could not be extracted from the geometry file. The format should be checked.\n')
        return failload

    # load the bank limit (where is the limit of the river without a flood)
    try:
        exp_reg22 = "Bank\sSta=([\s/+\d+\.-]+),([\s+\d+\.-]+)\n"
        data_bank_str = re.findall(exp_reg22, data_geo, re.DOTALL)
        data_bank_str = np.array(data_bank_str)
        data_bank_left = list(map(float, data_bank_str[:, 0]))
        data_bank_right = list(map(float, data_bank_str[:, 1]))
        data_bank = np.column_stack((data_bank_left, data_bank_right))
    except ValueError:
        print('Error: The location of the bank stations on the profile could not be extracted from the geometry file.\n')
        return failload

    # load the order of the reaches and rivers in .geo file
    # It might be different in the XML file unfortunately!
    # is not the order in the User Specified order neither
    # if only one reach, it is might no be given
    exp_reg23 = "[\n\t]River Reach=(.+)\n"
    reach_name_ini = re.findall(exp_reg23, data_geo)
    reach_name = []
    for i in range(0, len(reach_name_ini)):
        reach_name_i = reach_name_ini[i].replace('  ', '')
        reach_name_i = reach_name_i.replace(' ,', ',')
        if reach_name_i[-1] == ' ':
            reach_name_i = reach_name_i[:-1]
        reach_name.append(reach_name_i)

    # count the number of profile by reach
    # necessary if more than one reach and not georeferenced
    nb_pro_reach = np.zeros(len(reach_name))
    if len(reach_name) > 1:
        for i in range(0, len(reach_name)-1):
            a = data_geo.find('River Reach='+reach_name_ini[i])
            b = data_geo.find('River Reach='+reach_name_ini[i+1])
            reach_nb_str = data_geo[a:b]
            nb_pro_reach[i] = int(reach_nb_str.count('#Sta/Elev='))
        reach_nb_str = data_geo[b:]
        nb_pro_reach[i+1] = int(reach_nb_str.count('#Sta/Elev='))
        check_nb_pro_reach = len(data_profile_str) - np.sum(nb_pro_reach)
        if check_nb_pro_reach > 1:
            print("Warning: The number of profile by reach might not be right.\n")
    else:
        nb_pro_reach = [int(len(data_profile_str))]

    # load the coordinates of the profile
    # there is a georeferenced case with the coordinates of the profile
    # or non-georeferenced which is harder
    exp_reg3 = 'XS\s+GIS\s+Cut\s+Line\s*=\d+\s*\n([\s+\d+\.-]+)'
    data_xy_pro_str = re.findall(exp_reg3, data_geo, re.DOTALL)

    # load the distance from one profile to the other
    try:
        exp_reg33 = 'Type\sRM\sLength\sL\sCh\sR\s*=\s*[\s+\d+\.-]*,[\s+\d+\.\*]*,([\s+\d+\.]*,[\s+\d+\.]*,[\s+\d+\.]*)'
        data_dist_str = re.findall(exp_reg33, data_geo, re.DOTALL)
        data_dist = []

        for i in range(0, len(data_dist_str)):
            erase = False
            data_dist_str_i = data_dist_str[i]

            # Manage the cases where no distance is given in the .geo file
            if ",," in data_dist_str_i:
                # if we are on the last profile, let it pass
                if i == len(data_dist_str)-1:
                    data_dist_str_i = '-99,0,-99'
                else:  # erase (it is probably a bridge or culvert or other)
                    print('Warning: At least one distance between profile is not found. Distance data erased.\
                     Might be a bridge or a culvert.\n')
                    erase = True
                    data_dist_str_i = '-99,0,-99'
            if data_dist_str_i[0] == ',':
                data_dist_str_i = '-99'+data_dist_str_i
                print('Warning: One distance between left overbanks is not found.\n')
            if data_dist_str_i[-1] == ',':
                data_dist_str_i += '-99'
                print('Warning: One distance between right overbanks is not found.\n')

            data_dist_i = np.array(list(map(float, data_dist_str_i.split(','))))
            if not erase:
                data_dist.append(data_dist_i)

    except ValueError:
        print('Error: The location of the bank stations could not be extracted from the geometry file.\n')
        return failload

    if data_xy_pro_str:  # if georeferenced
        coord_p = []
        for i in range(0, len(data_xy_pro_str)):
            data_xy_i_str = data_xy_pro_str[i]
            data_xy_i_str = data_xy_i_str.replace('\n', '')
            data_xy_i_str = [data_xy_i_str[i:i+16] for i in range(0, len(data_xy_i_str), 16)]
            data_pro_x = np.array(list(map(float,data_xy_i_str[0::2])))
            data_pro_y = np.array(list(map(float,data_xy_i_str[1::2])))
            xy = np.column_stack((data_pro_x, data_pro_y))  # or xy
            coord_p.append(xy)
    else:
        print('Warning: The river profiles are not georeferenced. HYP: straight profiles. CHECK NECESSARY. \n')
        coord_p = coord_profile_non_georeferenced(data_bank, data_dist, data_river, data_profile, nb_pro_reach)

    return data_profile, coord_p, data_river, reach_name, data_bank, nb_pro_reach


def coord_profile_non_georeferenced(data_bank_all, data_dist_all, data_river_all, data_profile_all, nb_pro_reach):
    """
    This is a function to create the coordinates of the profile in the non-georeferenced case.
    This function is called by open geo_file(). Hypothesis: The profile are straight and perpendicular to the river.
    The last profile is at the end of the river.

    :param data_bank_all: distance along the profile of bank station
    :param data_dist_all: the distance between the profile (left, center channel, right)
    :param data_river_all: the coordinate of the river
    :param data_profile_all: the (d,z) data of the profile
    :param nb_pro_reach: the number of profile by reach
    :return: the coordinates of the profile

    **Technical comments**

    For each profile, we create an array composed of five points: Start of profile, left bank, intersection between
    river and profile, right bank and end of profile. The intersection with the river is directly given as input to
    the function. Then we find the vector perpendicular to this river and we get the four other points on the same line.

    To get the distance for these four other point, we must be careful to pass from the distance given in meter and the
    distance in the model coordinates (scaled between [0, 1] usually). The way to go from one coordinate system to
    another is to use the “alpha” variable.  We only need to correct distance, no problem with a system of coordinate
    which would not be in the same direction (as the data is given along a profile). The river passes in the middle of
    the right and left bank, so we can find where is left and right bank is. Because we know the total length of the
    profile, we can also find the beginning and end of the profile.


    """
    nb_pro = len(data_profile_all)
    coord_p = np.zeros((nb_pro, 5, 2))
    ar = 0
    ap = 0
    # for all the reaches
    for r in range(0, len(data_river_all)):
        # get the data for this reach
        data_river = data_river_all[r]
        data_bank = data_bank_all[ap:ap+int(nb_pro_reach[r])]
        data_dist = data_dist_all[ap:ap+int(nb_pro_reach[r])]
        data_profile = data_profile_all[ap:ap+int(nb_pro_reach[r])]
        data_dist[-1] = [0, 0, 0]  # HYP: last profile at the end of the profile
        ap += int(nb_pro_reach[r])
        # find the relationship between distance in (x,y) and distance in m or feet
        data_profile_0 = data_profile[0]
        dist_xy = np.linalg.norm(data_river[:-1, :] - data_river[1:, :], axis=1)  # dist between two points
        dist_tot = np.sum(dist_xy)
        data_dist = np.array(data_dist)
        dist_sta = np.sum(data_dist[:, 1])
        alpha = dist_tot / dist_sta
        dist_riv = np.zeros((len(data_dist), 1))
        for i in range(0, len(data_profile)):
            dist_riv[i] = np.sum(data_dist[:i, 1]) * alpha
        # find the coordinates of the first profile
        # HYPOTHESIS: it is a straight profile
        # for each profile 5 points with 2 coordinates
        # end profile, left bank, river, right bank, end profile
        coord_p_0 = np.zeros((5, 2))
        # central point is easy
        coord_p_0[2, :] = data_river[0, :]
        #  find the vector perpendicular to river (= profile)
        vec_pro = [data_river[1, 1] - data_river[0, 1], data_river[0, 0] - data_river[1, 0]]
        vec_pro_n1 = vec_pro / np.sqrt(vec_pro[0]**2+vec_pro[1]**2)
        # HYPOTHESIS: the river pass in the middle of the left and right bank station
        dist_left_pro = (data_bank[0, 0] - data_profile_0[0, 0]) * alpha + 0.5 * (data_bank[0, 1] - data_bank[0, 0]) * alpha
        dist_right_pro = (data_profile_0[-1, 0] - data_profile_0[0, 0]) * alpha - dist_left_pro
        # find the right and left end coordinates
        coord_p_0[4, :] = vec_pro_n1 * dist_right_pro + coord_p_0[2, :]
        coord_p_0[0, :] = -vec_pro_n1 * dist_left_pro + coord_p_0[2, :]
        # find the left and right river bank
        coord_p_0[3, :] = vec_pro_n1 * (data_bank[0, 0] - data_profile_0[0, 0])*alpha + coord_p_0[0, :]
        coord_p_0[1, :] = vec_pro_n1 * (data_bank[0, 1] - data_profile_0[0, 0])*alpha + coord_p_0[0, :]
        coord_p[ar, :, :] = coord_p_0

        dact = 0.0
        m = 1
        # find the profiles
        for i in range(0, len(data_river)-1):
            # find the coord of the points on the river where the profiles are
            ri = dist_riv[(dist_riv > dact) & (dist_riv <= dact + dist_xy[i])]
            alpha_r = (ri-dact) / dist_xy[i]
            # coordinates crossing between profile and river
            coord_p[ar+m:ar+m+len(ri), 2, 0] = data_river[i, 0] + alpha_r * (data_river[i+1, 0] - data_river[i, 0])
            coord_p[ar+m:ar+m+len(ri), 2, 1] = data_river[i, 1] + alpha_r * (data_river[i+1, 1] - data_river[i, 1])
            # find the coord of the two points where are the river banks
            # vec_r = data_river[i+1 ,:] - data_river[i, :]
            vec_pro = [data_river[i+1, 1] - data_river[i, 1], - data_river[i+1, 0] + data_river[i, 0]]
            vec_pro_n1 = vec_pro / np.sqrt(vec_pro[0]**2+vec_pro[1]**2)
            dist_bank = alpha * (data_bank[m:m+len(ri), 1] - data_bank[m:m+len(ri), 0]) / 2
            coord_p[ar+m:ar+m+len(ri), 3, 0] = dist_bank * vec_pro_n1[0] + coord_p[ar+m:ar+m+len(ri), 2, 0]
            coord_p[ar+m:ar+m+len(ri), 3, 1] = dist_bank * vec_pro_n1[1] + coord_p[ar+m:ar+m+len(ri), 2, 1]
            coord_p[ar+m:ar+m+len(ri), 1, 0] = - dist_bank * vec_pro_n1[0] + coord_p[ar+m:ar+m+len(ri), 2, 0]
            coord_p[ar+m:ar+m+len(ri), 1, 1] = - dist_bank * vec_pro_n1[1] + coord_p[ar+m:ar+m+len(ri), 2, 1]
            # find the end of the profile
            # HYPOTHESIS: Straight profile
            for j in range(0, len(ri)):
                data_profile_j = data_profile[m+j]
                dist_left_pro = (data_bank[m+j, 0] - data_profile_j[0, 0]) * alpha + 0.5 * (data_bank[m+j, 1] - data_bank[m+j, 0]) * alpha
                dist_right_pro = (data_profile_j[-1, 0] - data_profile_j[0, 0]) * alpha - dist_left_pro
                coord_p[ar+m+j, 4, :] = vec_pro_n1 * dist_right_pro + coord_p[ar+m+j, 2, :]
                coord_p[ar+m+j, 0, :] = -vec_pro_n1 * dist_left_pro + coord_p[ar+m+j, 2, :]
            #just in case
            dact += dist_xy[i]
            m += len(ri)

        ar += len(data_profile)

    # really should not be needded !!!!!
    for p in range(0, len(coord_p)):
        inx = coord_p[p, :, 0].argsort()
        coord_p[p] = coord_p[p, inx, :]
    return coord_p


def open_sdffile(sdf_file, reach_name, path):
    """
    This is a function to load .sdf file from HEC-RAS v5 used if the model is georeferenced. To find how to obtain the
    sdf file, read the doc of open_hecras.

    :param sdf_file: the name of the sdf file (string)
    :param reach_name: a list of string containing the name of the reaches/rivers in the order of the geo file
           which might not be the one of the sdf file. Output from open_geofile.
    :param path: the path where the file is stored (string)
    :return: velocity, water height, river_name, number of  time step (nb_sim)

    **Technical comments**

    To strat loading the sdf file, we open the sdf file. It is mostly a text file. Then we find velocity data and we
    pass this velocity data from string to float. The process is a bit similar to the one used in the function
    open_geofile with a healthy dose of regular expressions. We do this again for height data.

    We also extract the name of the river, reaches and profile. The number of simulation (nb_sim) is a bit confusing
    for a variable name. In fact, it is the number of time step. Hec-Ras considers that one simulation is the simulation
    for one time step. Hence, nb_sim is more or less nb_timestep.

    As in the xml file, we finally re-order the data as in the geo file. Indeed, it is possible to have different order
    between the reaches in the geo file and in the sdf file. Here, we use the function reorder_reach for this.
    """

    # check that the sdf file has the right extension (.sdf)
    # we might so the test two times, but so we are sure it is here
    blob, ext_sdf = os.path.splitext(sdf_file)
    if ext_sdf != '.sdf':
        print("Warning: File should be of .sdf type.\n")

    # open the sdf file
    try:
        with open(os.path.join(path, sdf_file), 'rt') as f:
            data_sdf = f.read()
    except IOError:
        print("Error: the file "+sdf_file+" does not exist.\n")
        return [-99], [-99], '-99', -99

    # get the velocity data
    exp_reg1 = "VELOCITIES:\s*\n([\s+\d+\,\.-]+)"
    vel_str = re.findall(exp_reg1, data_sdf, re.DOTALL)

    if not vel_str:
        print("Error: no velocity data found, the .sdf file might not be in the right format or the model is not"
              " geo-referenced. In the last case, use a .rep file. \n")
        return [-99], [-99], '-99', -99
    vel = []
    try:
        for i in range(0, len(vel_str)):
                vel_str[i] = vel_str[i].replace(',', ' ')
                vel_i = pass_in_float_from_geo(vel_str[i], -99)  # HYP: No data given without space -> -99
                vel.append(vel_i)
    except ValueError:
        print('Error: The velocity data could not be extracted from the sdf file.\n')
        return [-99], [-99], '-99', -99

    # get the height data
    exp_reg2 = "WATER ELEVATION:\s*([\s+\d+\,\.-]+)"
    wse_str = re.findall(exp_reg2, data_sdf, re.DOTALL)
    if not wse_str:
        print("Error: no height data found, the .sdf file might not be in the right format.\n")
        return [-99], [-99], '-99', -99
    wse = []
    try:
        for i in range(0, len(wse_str)):
                wse_str[i] = wse_str[i].replace(',', ' ')
                sep_str = wse_str[i].split()
                wse_i = list(map(float, sep_str))
                for j in range(0, len(wse_i)):
                    wse.append(wse_i[j])
    except ValueError:
        print('Error: The water height data could not be extracted from the sdf file.\n')
        return [-99], [-99], '-99', -99

    # get the reach and river name
    exp_reg_extra = "BEGIN CROSS-SECTIONS:(.+)END CROSS-SECTION"
    data_sdf2 = re.findall(exp_reg_extra, data_sdf, re.DOTALL)
    if not data_sdf2:
        print('Error: No data on cross section found. \n')
        return [-99], [-99], '-99', -99
    exp_reg3 = "STREAM ID:\s*(.+)\n"
    stream_str = re.findall(exp_reg3, data_sdf2[0])
    exp_reg4 = "REACH ID:\s*(.+)\n"
    reach_str = re.findall(exp_reg4, data_sdf2[0])
    if not stream_str:
        print("Warning: Stream names could not be extracted from the .sdf file.\n")
    if not reach_str:
        print("Warning: Reach names could not be extracted from the .sdf file.\n")
    stream_str = get_rid_of_white_space(stream_str)
    reach_str = get_rid_of_white_space(reach_str)

    # get the number of simulation
    exp_reg6 = "NUMBER OF PROFILES:\s*([\s*\d+]+)"
    nb_sim_str = re.findall(exp_reg6, data_sdf, re.DOTALL)

    if not nb_sim_str:
        print("Warning: the number of simulations is not found in the .sdf file.\n")
        return [-99], [-99], '-99', -99
    try:
        nb_sim = int(float(nb_sim_str[0]))
    except ValueError:
        print('Error: The number of simulation could not be extracted from the .sdf file.\n')
        return [-99], [-99], '-99', -99

    # get the simulation name or the name of the time steps
    exp_reg_n = "PROFILE ID:(.+)\n|$" # $ to avoid problem if no match is found
    sim_name_all = re.findall(exp_reg_n, data_sdf2[0])
    sim_name = []
    for s in sim_name_all:
        if s not in sim_name:
            sim_name.append(s)
        else:
            # the sim_name are ordered, so we get all the simulation name in the first cross-section
            break
    if not sim_name:
        print('Warning: the names of the time steps could not be extracted from the sdf file. \n')

    # get the name of the profile (riv_name)
    exp_reg5 = "STATION:\s*(.+)\n"
    riv_name_a = re.findall(exp_reg5, data_sdf)
    riv_name = []
    for i in range(0, len(riv_name_a)):  # could be coded better
        for s in range(0, nb_sim):
            riv_name.append(riv_name_a[i])
    if not riv_name:
        print('Warning: Profile name could not be extracted from the sdf file.\n')

    [wse, vel, riv_name] = reorder_reach(wse, vel,riv_name, reach_name, reach_str, stream_str, nb_sim)

    riv_name = riv_name[::nb_sim]  # get the name only once
    return vel, wse, riv_name, nb_sim, sim_name


def reorder_reach(wse, vel, riv_name, reach_name, reach_str, stream_str, nb_sim):
    """
    The order of the reach in HABBY is in the order given in the geo file. However, it can be given in any order
    in the other file. (xml, sdf, rep,...). This function re-order the reaches based on their name.

    :param wse: water height data (list of np.array for each profile)
    :param vel: velocity data (list of np.array for each profile)
    :param riv_name: the name of the profile (yeah I know it is not really logical as a name)
    :param reach_name: the name of the reach and stream (stream,reach) in the geo file order
    :param reach_str: the name of the reach in the anaylsed file order
    :param stream_str: the name of the stream in the anaylsed file order
    :param nb_sim: the number of simulation
    :return: wse, vel, riv_name all re-ordered

    **Technical comments**

    The reach name should not have white space at the end/start but can have white space into them.

    """

    # order the profile as in the geo file
    if len(reach_name) > 1:
        vel2 = np.copy(vel)
        wse2 = np.copy(wse)
        riv_name2 = np.copy(riv_name)
        name_reach_sdf = []
        for p in range(0, len(vel)):
            reach_p = reach_str[int(np.floor(p/nb_sim))]
            river_p = stream_str[int(np.floor(p/nb_sim))]
            name_reach_p = river_p+','+reach_p
            name_reach_sdf.append(name_reach_p)
        name_reach_sdf = np.array(name_reach_sdf)
        m = 0

        out_print = True
        for r in range(0, len(reach_name)):
            f_reach = np.where(name_reach_sdf == reach_name[r])
            f_reach = np.squeeze(f_reach)
            for i in range(0, len(f_reach)):  # list in this case cannot be changed to numpy.array
                wse[m+i] = wse2[f_reach[i]]
                vel[m+i] = vel2[f_reach[i]]
                try:
                    riv_name[m+i] = riv_name2[f_reach[i]]
                except IndexError:
                    if out_print:
                        print("Error: Some reaches are possibly missing. It is necessary to export all reaches.\n")
                        print("Error: Click on Select Reach to Export in GIS export of HEC-RAS 5.\n")
                        out_print = False

            m += len(f_reach)
        if m == 0:
            print('Warning: The reach and rivers names of the .geo file could not be found in the .sdf file.\n')

    return wse, vel, riv_name


def get_rid_of_white_space(stream_str):
    """
    This is a small fonction to get rid of white space at the end of name which could contain white space. Not used
    anymore as str.strip() functions well. But, as it was done already, we let it here.

    :param stream_str: the name of the string
    :return: the same name without white space.
   """
    # get rid of space (but not all the space!)
    for i in range(0, len(stream_str)):
        stream_str[i] = stream_str[i].strip()

    return stream_str


def open_repfile(report_file, reach_name, path, data_profile, data_bank):
    """
    A function to open the report file (.rep) from HEC-RAS. To obtain the report file, see the doc of the function
    open_hecras.

    :param report_file: a string with the name of the report file (.rep)
    :param reach_name: a list of string containing the name of the reaches/rivers in the order of the geo file,
           which might not be the order of the sdf file.
    :param path: the path where the report file is stored (string)
    :param data_profile: the data from each profile from the geofile (output from the open_geofile function)
    :param data_bank: the position of the bank limit (output from the open_geofile function)
    :return: velocity and the water surface elevation for each river profiles in a list of np.array,
            the number of simulation (int) and the name of the river profile (list of string)

    **Technical comments and walk-through**

    This function is used to open output from models which were not geo-referenced in hec-ras v5. It cannot be used if
    the model was georeferenced (or at least one should make some tests before).

    First, we obtain the water height. Then, we obtain the number of time step (which is called the number of
    simulation by hec-ras). To get the number of time step, we count each outputs given (one by profiles) and we
    divided it by the number of profile in the river. It is a bit indirect, but I did not find a simpler solution.

    We get the name of each profile and reach. Then, we get the velocity data. We have in a case which is not
    geo-referenced. By consequence, there are only three velocities: one the left bank, one in the main river channel
    and one the right bank.  Next we get the distance along the profile for these three velocities. Finally, we use
    the function reoder_reach for the same reason than in open_sdffile and open_xml.
    """
    # check that the report file has the right extension
    # we might so the test two times, but so we are sure it is here
    blob, ext_sdf = os.path.splitext(report_file)
    if ext_sdf != '.rep':
        print("Warning: File should be of .rep type.\n")

    # open the rep file
    try:
        with open(os.path.join(path, report_file), 'rt') as f:
            data_rep = f.read()
    except IOError:
        print("Error: the file "+report_file+" does not exist.\n")
        return [-99],[-99], -99, '-99'

    # obtain WSE data
    exp_reg = "W.S. Elev\s*\(\D+\)\s*([\d\.-]+)\D"
    wse_str = re.findall(exp_reg, data_rep)
    if not wse_str:
        print("Warning: Water level is empty.\n")
    try:
        wse = list(map(float, wse_str))
    except ValueError:
        print("Error:The water level height could not be extracted from the rep file.\n")
        return [-99], [-99], -99, '-99'

    # obtain the number of simulation
    # it is not really given so we we could the number of cross section output
    exp_reg1 = 'CROSS SECTION OUTPUT'
    cros_sec_o = re.findall(exp_reg1, data_rep)
    nb_sim = len(cros_sec_o)/len(data_profile)
    if np.floor(nb_sim) != nb_sim:
        print("Warning: The number of simulation does not seems right. It should be an integer.\n")
    nb_sim = int(nb_sim)

    # obtain the name of the reaches and the name of the profile
    exp_reg = "CROSS SECTION\s*\n+(.*\n.*\n)"
    name_str = re.findall(exp_reg, data_rep)
    if not name_str:
        print("Warning: The profile name could be extracted from the .rep file.\n")
    reach_str = []
    pro_str = []
    stream_str = []
    for i in range(0,len(name_str)):
        exp_reg1 = "RIVER:\s*(.+)\n"
        exp_reg2 = "RS:\s*(.+)\n"
        exp_reg3 = "REACH:\s*(.+)\n"
        stream_str_i = re.findall(exp_reg1, name_str[i])
        pro_str_i = re.findall(exp_reg2, name_str[i])
        reach_str_i = re.findall(exp_reg3, name_str[i])
        reach_str_i = reach_str_i[0]
        reach_str_i = reach_str_i[:len(reach_str_i) - len(pro_str_i[0]) - 4]   # -4 because RS:
        reach_str.append(reach_str_i)
        pro_str.append(pro_str_i[0])
        stream_str.append(stream_str_i[0])
    reach_str = get_rid_of_white_space(reach_str)
    pro_str = get_rid_of_white_space(pro_str)
    stream_str = get_rid_of_white_space(stream_str)
    riv_name = pro_str # just to kkep the same variable name

    # obtain the name of the time steps
    exp_reg4 = 'Profile #(.+)'
    sim_name_all = re.findall(exp_reg4, data_rep)
    if not sim_name_all:
        print('Warning: the name of the time steps was not found. \n')
    sim_name = []
    for s in sim_name_all:
        if s not in sim_name:
            sim_name.append(s)
        else:
            # simulation name are all given in the first cross section
            break

    # obtain velocity data
    # if not georeferenced only 3 velocity by channel, other wise all velocity
    exp_reg = "Avg. Vel.\s*\(\D+\)([\d\.\s]+)\n"
    vel_av_str = re.findall(exp_reg, data_rep)
    if not vel_av_str:
        print("Warning: the velocity data is empty (.rep file).\n")

    # pass the velocity data in float
    m = []
    vel_av = []
    try:
        for i in range(0, len(vel_av_str)):
            vel_av_str_i = vel_av_str[i].split()
            # the three velocities are not always present. Find which velocity is present
            if len(vel_av_str_i) == 1:  # it will be the center velocity in this case
                    m.append([1])
            if len(vel_av_str_i) == 2:
                vel_av_str_i_whole = vel_av_str[i]
                if not vel_av_str_i_whole[-8:].split():  #if empty
                    m.append([0, 1])  # velocity is on Left OB in this case
                else:
                    m.append([1, 2])  # velocity is on Right Ob
            if len(vel_av_str_i) == 3:  # all velocity are there
                m.append([0, 1, 2])
            vel_av_i = list(map(float, vel_av_str_i))
            vel_av.append(vel_av_i)
    except ValueError:
        print("Error: the velocity could not be extracted from the .rep file (non-georeferenced case).\n")
        return [-99], [-99], -99, '-99'

    # obtain the x coordinate from data bank and data profile
    x_av = []
    try:
        for i in range(0, len(data_profile)):
            data_profile_i = data_profile[i]
            data_bank_i = data_bank[i] - data_profile_i[0,0]
            len_pro = data_profile_i[-1, 0] - data_profile_i[0, 0]
            vel_x_i = np.array([0, data_bank_i[0], data_bank_i[1] ])/len_pro
            for j in range(0, nb_sim):
                x_av.append(vel_x_i)
    except ValueError:
        print("Error: the coordinate of the velocity could not be extracted from the .rep file (non-georeferenced case).\n")
        return [-99], [-99], -99, '-99'

    # put the (x and v) data together
    vel = []
    for i in range(0, len(vel_av)):
        x_av_i = x_av[i]
        vel_i = np.column_stack((x_av_i[m[i]], vel_av[i]))
        vel.append(vel_i)

    [wse, vel, riv_name] = reorder_reach(wse, vel, riv_name, reach_name, reach_str, stream_str, nb_sim)

    return vel, wse, riv_name, nb_sim, sim_name


def pass_in_float_from_geo(data_str, len_number):
    """
    This is a function to pass the string data into float for open_geofile() and open_sdffile(). It is in a function
    because it is possible that two number are not separated by a space in the input data.

    :param data_str: the data in a string form
    :param len_number: the number of digit for one number (int)
    :return: a np.array of float with 2 columns  (x,y) or (x,z)
    """

    sep_str = data_str.split()
    try:
        data_i = list(map(float, sep_str))
        # separe x and z
        data_profile_x = data_i[0::2]  # choose every 2 float
        data_profile_z = data_i[1::2]
        xz = np.column_stack((data_profile_x, data_profile_z))  # or xy
    except ValueError:
        data_i = []
        # manage the case where number are together such as 0.234290.23323
        try:
            l = 0
            data_str = data_str.replace('\n', '')  #windows vs Linux?
            while l < len(data_str):

                data_i.append(float(data_str[l:l+len_number]))
                l += len_number

            # separe x and z
            data_profile_x = data_i[0::2]  # choose every 2 float
            data_profile_z = data_i[1::2]
            xz = np.column_stack((data_profile_x, data_profile_z))  # or xy
            # print("Warning: Two coordinates were not separated by space. HYP: Number of digit is 8 or 16.\n")
        except ValueError:
            print("Error: Data are not number.\n")
    return xz


def find_coord_height_velocity(coord_pro, data_profile, vel, wse, nb_sim, max_vel_dist=0):
    """
    This function finds the coordinates of the height/velocity. In hec-ras outputs the data are often written in the
    form (profile, distance along the profile, data). This function passes this type of information in the usual
    coordinate form.

    :param coord_pro: the coordinate (x,y) of the profile. List of np.array.
    :param data_profile: data concening the geometry of the profile, notably its elevation (x,z). List of np.array.
    :param vel: the velocity data. List of np.array.
    :param wse: the water surface elevation. List of np.array.
    :param nb_sim: the number of simulation in case there is more than one
    :param max_vel_dist: the minimum number of velocity point by ten meter before a warnings appears
    :return: for each simulation, a list of np.array representing (x,y,v) and (x,y,h,)

    **Technical comments**

    This is a function called after having loaded the data. Hec-Ras present the data in (profil, distance along
    profile, data) form for the height. For the velocity, it is similar but the distance is given by a number between
    0 and 1 (0 is the start of the profile, 1 is the end of the profile). This function transforms this data in the form
    (x,y, dist, data) using the (x,y) coordinates given in the coord_pro variable. In other word,  we have the
    coordinate of the profile, not of the coordinates of the height and velocity data.

    First, we get the distance between all points in (x,y) system. Then, we get the length of the profile in
    meter or feet. It is possible to have a (x,y) coordinate system in a different unit. Hence, the length of the profil
    is valid for the (profile, distance along profile, data) view. We multiply the velocity distance data by this
    length. Hence, the distance information is now in meter or feet along the profile for water height and velocity.

    There are some lines added to account for the last and first points of the profile (annoying in hec-ras). We then
    calculate the new coordinates. For each velocity and water height point, we find the last known point in the (x,y)
    coordinates. We do a vectorial addition from this point plus the vector between this point and the next multiplied
    by the distance from this point to the point that we tried to calculate.  The variable alpha is used to pass from
    one coordinate system to the next one.

    Careful the height is on the node and the velocity is by zone.
    """

    xy_h_all = []
    zone_v_all = []
    for s in range(0, nb_sim):
        xy_h = []
        zone_v = []
        for p in range(0, len(coord_pro)):

            # get data for this profile
            coord_pro_p = coord_pro[p]
            elev = data_profile[p]
            x = elev[:, 0] - elev[0, 0]
            vel_p = vel[p*nb_sim + s]

            # create array
            zone_v_p = np.zeros((len(vel_p), 4))  # (x,y) of the start of the zone distance and v
            # the end of the zone is the next (x,y) or the end of the profile
            xy2 = np.zeros((len(x), 4))  # (x,y,d, h) in the (x,y) coordinates
            dact = 0.0
            m = 1
            mv = 0

            # find distance between the coordinate system
            dist = np.linalg.norm(coord_pro_p[:-1, :] - coord_pro_p[1:, :], axis=1)  # dist between two points
            if dist[0] == 0:
                m = 2
            dist_tot = np.sum(dist)  # coordinates in (x,y)
            if dist_tot == 0:  # division by zero is annoying
                dist_tot = 1e-8
            dist_pro = x[-1]  # coordinates in meter or feet
            dist2 = dist * dist_pro / dist_tot  # also meter or feet
            vel_x = dist_pro * vel_p[:, 0]

            # get the first and end profile point
            xy2[:, :2] = coord_pro_p[0, :]
            xy2[-1, :2] = coord_pro_p[-1, :]
            zone_v_p[:, :2] = coord_pro_p[0, :]
            if vel_p[0, 0] < -1e30:  # HEC-RAS-> +/-X.XXe35 = end or beginning of profile (if I get it right)
                zone_v_p[0, :2] = coord_pro_p[0, :]
                mv = 1
            if vel_p[-1, 0] > 1e30:
                zone_v_p[-1, :2] = coord_pro_p[-1, :]

            # find the new coordinates
            for i in range(0, len(dist)):
                xi = x[(x > dact) & (x < dact + dist2[i])]  # <=???
                vxi = vel_x[(vel_x > dact) & (vel_x <= dact + dist2[i])]

                alpha = (xi-dact) / dist2[i]
                xy2[m:m+len(xi), 0] = coord_pro_p[i, 0] + alpha * (coord_pro_p[i+1, 0] - coord_pro_p[i, 0])
                xy2[m:m+len(xi), 1] = coord_pro_p[i, 1] + alpha * (coord_pro_p[i+1, 1] - coord_pro_p[i, 1])

                alpha_v = (vxi-dact) / dist2[i]
                zone_v_p[mv:mv+len(vxi), 0] = coord_pro_p[i, 0] + alpha_v * (coord_pro_p[i+1, 0] - coord_pro_p[i, 0])
                zone_v_p[mv:mv+len(vxi), 1] = coord_pro_p[i, 1] + alpha_v * (coord_pro_p[i+1, 1] - coord_pro_p[i, 1])

                dact += dist2[i]
                m += len(xi)
                mv += len(vxi)

            zone_v_p[:, 3] = vel_p[:, 1]
            zone_v_p[:, 2] = vel_x + elev[0, 0]
            xy2[:, 3] = wse[p*nb_sim + s] - elev[:, 1]  # height
            xy2[:, 2] = x + elev[0, 0]
            xy_h.append(xy2)
            zone_v.append(zone_v_p)

            #  check if we get enough velocity point
            #  max_vel_dist is the maximum distance between two velocity measurements
            warn_vel = False
            if dist_pro/len(zone_v_p) >= max_vel_dist and warn_vel:
                print('Warning: the number of velocity point is low compared to the profile length.\n')

        xy_h_all.append(xy_h)
        zone_v_all.append(zone_v)

    return xy_h_all, zone_v_all


def update_output(zone_v, coord_pro_old, data_profile, xy_h, nb_pro_reach_old):
    """
    This function updates the form of the output so it is coherent with mascaret and rubar after the lateral
    distribution of velocity for these two models. There are three important changes. First, coord_pro contains dist along
    the profile (x) and height in addition to the coordinates. Secondly, vh_pro contains only height if height is above
    or equal to zero. Thirdly, a point is created at the water limits and v and height are given at the same points.
    nb_pro_reach is also modified as in mascaret. We want to modify it so it start by zero and is additive, i.e., that
    it gives total number of profile before, not the number of profile by reach.

    :param zone_v: (x,y, dist along profile, v) for each time step. However, the zone are the one from the models.
           They are different than the one from xy_h, which is unpractical for the rest of HABBY.
    :param coord_pro_old: the (x,y) coordinate for the profile
    :param data_profile: the distance along the porfile and height of each profile
    :param xy_h: the water height
    :param nb_pro_reach_old: the number of the profile by reach in the old form.
    :return: coord_pro, vh_pro, nb_pro_reach

    [doc to be finished]
    """

    vh_pro = []
    coord_pro = []
    warn_dup = True
    dist_mov = 0.00001
    for t in range(0, len(zone_v)):
        # vhpro for this time step
        vh_pro_t = []

        for p in range(0, len(coord_pro_old)):
            xy_h_pro = xy_h[t][p]
            data_profile_p = data_profile[p]

            # create an updated form of coord_pro with all the data (one point by height measurement)
            # add dist along profil and height to coord_pro
            if t == 0:
                # check for special case and correct or ignore profile
                if np.sum(abs(xy_h_pro[:, 0]) + abs(xy_h_pro[:, 1])) == 0:
                    print('Warning: profil with only (0,0) as a coordinate. Is ignored. \n')
                    break
                if len(xy_h_pro[:, 0]) < 2:
                    print('Warning: profil with one or zeros points. Is ignored. \n')
                    break
                s = np.sort(xy_h_pro[:, 2], axis=None)
                if (s == xy_h_pro[:, 2]).all:
                    pass
                else:
                    print('Warning: Coordinate points are not aligned along the profile.\n')
                # find if we have duplicates (the grid does not function in this case)
                s2 = s[:-1]
                duplicate = s2[s[1:] == s[:-1]]
                # check duplicate first point
                if xy_h_pro[0, 2] == xy_h_pro[1, 2]:
                    duplicate_start = [0]
                    duplicate_start.extend(duplicate)
                    duplicate = duplicate_start
                # correct the duplicates
                if len(duplicate) > 1:
                    if warn_dup:
                        print('Warning: Duplicate value in the profile. Modifications will be made. \n')
                        warn_dup = False
                    for i in range(0, len(duplicate)):
                        ind_dup = np.where(xy_h_pro[:, 2] == duplicate[i])[0]
                        for j in range(0, len(ind_dup)-1):
                            xy_h_pro[ind_dup[j], 2] -= dist_mov * (j+1)* xy_h_pro[ind_dup[j], 2] #+ dist_mov/100
                            #if ind_dup[j]>0:
                             #   ax = xy_h_pro[ind_dup[j], 0] - xy_h_pro[ind_dup[j]-1, 0]
                             #   ay = xy_h_pro[ind_dup[j], 1] - xy_h_pro[ind_dup[j]-1, 1]
                            #else:
                            ax = xy_h_pro[-1, 0] - xy_h_pro[0, 0]
                            ay = xy_h_pro[-1, 1] - xy_h_pro[0, 1]
                            norm = np.sqrt(ax**2 + ay**2)
                            ax = ax / norm
                            ay = ay / norm
                            if ax == 0 and ay == 0:
                                xy_h_pro[ind_dup[j], 0] -= 1e-10
                                xy_h_pro[ind_dup[j], 1] -= 1e-10
                            else:
                                xy_h_pro[ind_dup[j], 0] -= ax * dist_mov * (j+1)
                                xy_h_pro[ind_dup[j], 1] -= ay * dist_mov * (j+1)

                # add the new profile
                coord_pro_p = [xy_h_pro[:, 0], xy_h_pro[:, 1], data_profile_p[:, 1], xy_h_pro[:, 2]]
                coord_pro.append(coord_pro_p)

            x_p = xy_h_pro[:, 2]
            h_p = xy_h_pro[:, 3]

            # create the vh_pro_t array
            # add the point of the water limits
            zero_crossings = np.where(np.diff(np.signbit(h_p)))[0]
            for i in zero_crossings:
                if x_p[i] < x_p[i + 1]:
                    a = (h_p[i] - h_p[i + 1]) / (x_p[i] - x_p[i + 1])  # lin interpolation
                    b = h_p[i] - a * x_p[i]
                    new_x = - b / a
                elif x_p[i] == x_p[i + 1]:
                    new_x = x_p[i]
                else:
                    print('Error: x-coordinates are not increasing.\n')
                    return [-99], [-99], [-99]
                h_p = np.concatenate((h_p[:i + 1], [0], h_p[i + 1:]))
                x_p = np.concatenate((x_p[:i + 1], [new_x], x_p[i + 1:]))
                zero_crossings += 1
            water_ind = np.where(h_p >= 0)[0]
            x_p0 = x_p
            h_p0 = h_p
            h_p = h_p[water_ind]
            x_p = x_p[water_ind]
            # add the velocity
            zone_v_pro = zone_v[t][p]
            zone_v_new = np.zeros((len(h_p),))
            for i in range(0, len(h_p)):
                # if coord increase along the profile (usually the case)
                if x_p[1] >= x_p[0] or abs(x_p[0] - x_p[1]) < 1e-10:
                    indv = bisect.bisect(zone_v_pro[:, 2], x_p[i]) - 1
                else:
                    print('Error x-coordinate does not increase. \n')
                    return [-99], [-99], [-99]
                #indv = np.argmin(abs(zone_v_pro[:, 2] - x_p[i]))
                zone_v_new[i] = zone_v_pro[indv, 3]
            # velcoity is zeros if water height = 0, velocity is by zone and not by point
            # so two additional point needed for plotting
            # we should not have two identical point(!)
            if len(x_p0) - 1 > max(water_ind) and min(water_ind) > 0:
                x_here = np.concatenate(([x_p0[min(water_ind) - 1]], x_p, [x_p0[max(water_ind) + 1]]))
                h_here = np.concatenate(([h_p0[min(water_ind) - 1]], h_p, [h_p0[max(water_ind) + 1]]))
            elif len(x_p0) - 1 > max(water_ind) and min(water_ind) == 0:
                x_here = np.concatenate(
                    ([x_p[0] - dist_mov * x_p[0] - dist_mov / 100], x_p, [x_p0[max(water_ind) + 1]]))
                h_here = np.concatenate(([h_p[0]], h_p, [h_p0[max(water_ind) + 1]]))
            elif len(x_p0) - 1 < max(water_ind) and min(water_ind) > 0:
                x_here = np.concatenate(([x_p0[min(water_ind) - 1]], x_p, [x_p[-1] + dist_mov * x_p[-1]]))
                h_here = np.concatenate(([h_p0[min(water_ind) - 1]], h_p, [h_p[-1] + dist_mov * h_p[-1]]))
            else:
                x_here = np.concatenate(([x_p0[0] - dist_mov * x_p0[0] - dist_mov / 100],
                                         x_p, [x_p[-1] + dist_mov * x_p[-1]]))
                h_here = np.concatenate(([h_p0[0]], h_p, [h_p[-1]]))
            v_here = np.concatenate(([0], zone_v_new, [0]))
            vh_pro_t_p = [x_here, h_here, v_here]
            vh_pro_t.append(vh_pro_t_p)
        vh_pro.append(vh_pro_t)

    # update nb_pro_reach
    nb_pro_reach = []
    for r in range(0,len(nb_pro_reach_old)):
        nb_pro_reach.append(int(np.sum(nb_pro_reach_old[:r])))
    nb_pro_reach.append(int(np.sum(nb_pro_reach_old)))

    return coord_pro, vh_pro, nb_pro_reach


def figure_xml(data_profile, coord_pro_old, coord_r, xy_h_all, zone_v_all,  pro, path_im, fig_opt, nb_sim=0,
               name_profile='no_name', coord_p2=-99):
    """
    A function to plot the results of the loading of hec-ras data.

    :param data_profile: (list with np.array)
    :param coord_pro_old: (x,y) data of the profile (list with np.array)
    :param coord_r: (x,y) data of the river (list with np.array)
    :param xy_h_all: (x,y, h) for the height data for each simulation (list with np.array)
    :param zone_v_all: (x,y, v) for the velocity data. velocity is by zone of profile. for each simulation.
           the (x,y) indicates the start of the zone which end with the next velocity
    :param pro: a list of int with the profile whcih should be ploted [2,3,4]
    :param nb_sim: which simulation should be plotted. In fact, it often relates to the time step.
    :param name_profile: a list of string with the name of the profiles
    :param coord_p2: the data of the profile when non geo-referenced, optional
    :param path_im: the path where the figure should be saved (string)
    :param fig_opt: the figure options

    **Technical comments**

    We first choose the size of the font to be written. At term, it should be given by the options.

    Two main groups of figure will be done: One list of figure with the form of the profil, the water height, and the
    velocity for the chosen profiles and one (x,y) view of the position of each profile.

    We chose the time step to be written (the variable nb_sim here). The variable pro is a list which says which
    profiles are to be plotted. Hence, we get the velocity and water height for the time step and profile of interest.

    To plot the velocity, we first get the distance along the profile where the water level cut the profile elevation.
    This is the variable xint1 and xint2. We then get the velocity data for the region under the water. We add three
    points for velocity at 0, xint1 and xint2. We then used the step function to plot the vecloity. Because of the added
    point, we will have a zero velocity from 0 to xint1, then the velocity data, then again zeros from xint2 to the end.

    To plot the elevation of the profile, we plot the variable xz and we use the function fill_between to fill
    in blue the region under water. This function creates a line at the water elevation and fills in blue between this
    line and the profile elevation. We add some titles and save the figures.

    For the second type of figure (view in x,y coordinates), We first plot the river position which is saved in the
    coord_r variable. Then we plot the coordinate of each profile and their names. If the name of the profile is not
    known, we plot the profile number.  We also plot the position of each velocity data and height data (as it could be
    useful). If the figure gets too complicated, this can be taken away by changing the two lines which finish
    with height or velocity as comment.  We add some titles and save the figures.
    """
    rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    rcParams['font.size'] = fig_opt['font_size']
    rcParams['lines.linewidth'] = fig_opt['line_width']
    format = int(fig_opt['format'])
    rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if fig_opt['font_size'] > 7:
        rcParams['legend.fontsize'] = fig_opt['font_size'] - 2
    rcParams['legend.loc'] = 'best'

    #close()

    # choose the simulation to plot
    xy_h = xy_h_all[nb_sim]
    zone_v = zone_v_all[nb_sim]

    # plot profile and water surface elevation
    m = 0
    for i in pro:
        xz = data_profile[i]
        xyh_i = xy_h[i]
        v_xy_i = zone_v[i]
        hi = xyh_i[:, 3]
        fig = figure(m)
        suptitle("")
        ax1 = subplot(313)
        # find the water limits (important  to plot the velocity, not the elevation of the profile)
        h0 = hi[0] + xz[0, 1]
        wet = np.squeeze(np.where(hi > 0))
        p1 = wet[0]
        p2 = wet[-1]
        if xz[p1, 0] != xz[p1-1, 0]:  # not vertical profile
            a1 = (xz[p1, 1] - xz[p1-1, 1])/(xz[p1, 0] - xz[p1-1, 0])
            b1 = xz[p1, 1] - a1*xz[p1, 0]
            xint1 = (h0 - b1) / a1
        else:  # vertical profile
            xint1 = xz[p1, 0]
        if wet[0] == 0:   # if the left overbank is totally wet
            xint1 = xz[0, 0]
        if p2 < len(xz)-1:  # if at the end of the profile
            if xz[p2, 0] != xz[p2+1, 0]:  # not vertical profile
                a2 = (xz[p2, 1] - xz[p2+1, 1])/(xz[p2, 0] - xz[p2+1, 0])
                b2 = xz[p2, 1] - a2*xz[p2, 0]
                xint2 = (h0 - b2) / a2
            else:
                xint2 = xz[p2+1, 0]
        else:
            xint2 = xz[p2, 0]
        # update velocity data with point where water level h=0
        v_xy_i_wet = v_xy_i[(xint1 <= v_xy_i[:, 2]) & (v_xy_i[:, 2] <= xint2), 2:]
        if len(v_xy_i_wet) > 0:
            v_xy_i_wet = np.vstack(([[0, 0], [xint1, v_xy_i[0, 3]], v_xy_i_wet, [xint2, 0]]))
        else:  # case with no velocity in the water
            v_xy_i_wet = np.vstack(([[0, 0], [xint1, v_xy_i[0, 3]], [xint2, 0]]))
        # print velocity
        step(v_xy_i_wet[:, 0], v_xy_i_wet[:, 1], where='post', color='r')
        xlim([np.min(xz[:, 0]-1)*0.95, np.max(xz[:, 0])*1.05])
        if fig_opt['language'] == 0:
            xlabel("x [m or ft]")
            ylabel(" Velocity [m/sec or ft/sec]")
        elif fig_opt['language'] == 1:
            xlabel("x [m ou ft]")
            ylabel(" Vitesse [m/sec ou ft/sec]")
        ax1 = subplot(211)
        plot(xz[:, 0], xz[:, 1], 'k')  # profile
        fill_between(xz[:, 0], xz[:, 1],hi + xz[:, 1], where=xz[:, 1] < hi + xz[:, 1], facecolor='blue', alpha=0.5, interpolate=True)
        if fig_opt['language'] == 0:
            xlabel("x [m or ft]")
            ylabel("altitude of the profile [m or ft]")
            if name_profile == 'no_name':
                title("Profile " + str(i))
            else:
                title("Profile " + name_profile[i])
            legend(("Profile", "Water surface"), fancybox=True, framealpha=0.5)
        elif fig_opt['language'] == 1:
            xlabel("x [m ou ft]")
            ylabel("altitude du profil [m ou ft]")
            if name_profile == 'no_name':
                title("Profil " + str(i))
            else:
                title("Profil " + name_profile[i])
            legend(("Profil", "Surface de l'eau"), fancybox=True, framealpha=0.5)
        xlim([np.min(xz[:, 0]-1)*0.95, np.max(xz[:, 0])*1.05])
        m += 1
        if format == 0 or format == 1:
            savefig(os.path.join(path_im, "HEC_profile_"+str(i) + '_day' + time.strftime("%d_%m_%Y_at_%H_%M_%S")+
                                 '.png'), dpi=fig_opt['resolution'])
        if format == 0 or format == 3:
            savefig(os.path.join(path_im, "HEC_profile_"+str(i) + '_day' + time.strftime("%d_%m_%Y_at_%H_%M_%S")+
                                 '.pdf'), dpi=fig_opt['resolution'])
        if format == 2:
            savefig(os.path.join(path_im, "HEC_profile_" + str(i) + '_day' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.jpg'), dpi=fig_opt['resolution'])

    # plot the profile in the (x,y) plane
    fig2 = figure(len(pro))
    if fig_opt['language'] == 0:
        txt_pro = "Profile position"
        txt_h = "Water height coordinates"
        txt_v = "Velocity coordinates"
        txt_riv = "River "
    elif fig_opt['language'] == 1:
        txt_pro = "Position des profils"
        txt_h = "Position des hauteurs d'eau"
        txt_v = "Position des vitesses"
        txt_riv = 'rivière '
    else:
        txt_pro = "Profile position"
        txt_h = "Water height coordinates"
        txt_v = "Velocity coordinates"
        txt_riv = "River "
    xmip = 1000
    xmap = -1000

    for i in range(0,len(coord_r)):
        coord_r_i = coord_r[i]
        plot(coord_r_i[:, 0], coord_r_i[:, 1], label=txt_riv + str(i))
    for j in range(0, len(coord_pro_old)):
        coord_j = coord_pro_old[j]
        xy_j = xy_h[j]
        v_xy_j = zone_v[j]
        plot(coord_j[:, 0], coord_j[:, 1], '-xm', label=txt_pro,  markersize=8)  # profile
        if coord_p2 != -99:
            coord_j2 = coord_p2[j]
            plot(coord_j2[:, 0], coord_j2[:, 1], '-^g', label=txt_pro,  markersize=2)  # profile not georeferenced
        if name_profile == 'no_name':
            text(coord_j[0, 0] + 0.03, coord_j[0, 1] + 0.03, str(j))
        else:
            text(coord_j[0, 0] + 0.03, coord_j[0, 1] + 0.03, name_profile[j])
        plot(xy_j[:, 0], xy_j[:, 1], '.k', label=txt_h,  markersize=3)  # height
        plot(v_xy_j[:, 0], v_xy_j[:, 1], '*g', label=txt_v,  markersize=7)  # velocity
        txt_pro = '_nolegend_'
        txt_h = "_nolegend_"
        txt_v = "_nolegend_"
        xmip = np.min([xmip, np.min(coord_j[:, 0])])
        xmap = np.max([xmap, np.max(coord_j[:, 0])])
    rcParams.update({'font.size': 12})
    xlim([xmip, xmap*1.05])
    ylim([xmip, xmap*1.05])
    xlabel("x []")
    ylabel("y []")
    if fig_opt['language'] == 0:
        title("Position of the profiles")
    elif fig_opt['language'] == 1:
        title("Position des profils")
    axis('equal')  # if right angle are needed
    legend(fancybox=True, framealpha=0.5)
    if format == 0 or format == 1:
        savefig(os.path.join(path_im, "HEC_all_pro_"+time.strftime("%d_%m_%Y_at_%H_%M_%S")+".png"),
                dpi=fig_opt['resolution'], transparent=True)
    if format == 0 or format == 3:
        savefig(os.path.join(path_im, "HEC_all_pro_"+time.strftime("%d_%m_%Y_at_%H_%M_%S")+".pdf"),
                dpi=fig_opt['resolution'], transparent=True)
    if format == 2:
        savefig(os.path.join(path_im, "HEC_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                dpi=fig_opt['resolution'], transparent=True)
    show()



def main():
    """
    This is not the main() of HABBY. This function is used to test this module independently of the rest of HABBY.
    """

    path_test = r'D:\Diane_work\version\file_test'
    #path_test = r'C:\Users\Diane.Von-Gunten\Documents\HEC Data\HEC-RAS\Steady Examples'
    name = 'thames'
    name_xml = name+ '.O01.xml'
    name_geo = name+'.g01'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'

    [coord_pro, vh_pro, nb_pro_reach] = open_hecras(name_geo, name_xml, path_test, path_test, path_im, True)

if __name__ == '__main__':
    main()
