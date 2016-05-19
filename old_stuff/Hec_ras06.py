
import xml.etree.ElementTree as Etree
import os
import re
import numpy as np
import warnings
from matplotlib.pyplot import axis, plot, step, figure, xlim, ylim, xlabel, ylabel, title, figure, text, legend, show, subplot, fill_between, rcParams, bar


def open_hecras(geo_file, res_file, path_geo, path_res):
    """
    This function will open HEC-RAS outputs, i.e. the .geo file and the outputs (either .XML, .sdf or .rep) from HEC-RAS

    :rtype: list of numpy array
    :param geo_file: the name of .goX (example .go3) file which is an output from hec-ras containg the profile data
    :param res_file: the name of O0X.xml file from HEC-RAS or the name of the .sdf file from HEC-RAS or the name of the
    .rep file from HEC-RAS
     -To obtain the xml file in hEC-RAS 4, open the project in HEC-RAS,
     click on File , then export geometry and result (RAS Mapper), then OK
     -To obtain the sdf file in HEC-RAS5, click on File, then Export GIS data
     Export all reaches (select Reaches to export -. Full List -> Ok)
     Export all needed profile (select Profile to export -> Select all -> ok)
     - To obtain the report file .rep, click on File, generate report
     Select Flow data and Geometry data in input data and, in Specific Table, Flow distribution and Cross section Table
    :param path_res: path to the result file
    :param path_geo: path to the geo file

    all entry parameter are string
    :return: velocity, height for (x,y) of each river profile -> [x y dist v] and [ x y dist h]
    """

    # load the geometry file which contains info on the profile and the geometry
    [data_profile, coord_pro, coord_r, reach_name, data_bank] = open_geofile(geo_file, path_geo)

    # load the xml, rep, or sdf file to get velocity and wse
    blob, ext = os.path.splitext(res_file)
    if ext == ".xml":
         [vel, wse, riv_name, nb_sim] = open_xmlfile(res_file, reach_name, path_res)
    elif ext == ".sdf":
        try:
            [vel, wse, riv_name, nb_sim] = open_sdffile(res_file, reach_name, path_res)
        except ValueError:
            print("Error: Cannot open .sdf file. Is the model georeferenced? If not, use the .rep file.")
    elif ext == ".rep":
        [vel, wse, riv_name, nb_sim] = open_repfile(res_file, reach_name, path_res, data_profile, data_bank)
    else:
        warnings.warn("The file containing the results is not in XML, rep or sdf format. HABBY try to read it as XML file.")
        [vel, wse, riv_name, nb_sim] = open_xmlfile(res_file, reach_name, path_res)
    # get water height in the (x,y coordinate) and get the velocity in the (x,y) coordinates
    # velocity is by zone (between 2 points) and height is on the node
    [xy_h, zone_v] = find_coord_height_velocity(coord_pro, data_profile, vel, wse, nb_sim)
    # plot and check
    figure_xml(data_profile, coord_pro, coord_r, xy_h, zone_v, [0, 6], 0, riv_name)

    return xy_h, zone_v


def open_xmlfile(xml_file, reach_name, path):
    """
    This function open the xml file from HEC-RAS to get the velocity and water surface elevation.

    :param xml_file:  name of O0X.xml file from HEC-RAS. To obtain this file, open the project in HEC-RAS,
     click on File , then export geometry and result (RAS Mapper), then OK
    :param reach_name, a list of string containing the name of the reaches/rivers in the order of the geo file
     (might not be the one of the xml file)
    :param path: path to the xml file
    all entry parameter are string
    :return: velocity and the water surface elevation for each river profiles in a list of np.array,
    the number of simulation (int) and the name of the river profile (list of string)
    """

    # load the xml file
    root = load_xml(xml_file, path)

    # find the velocity in the XML file
    # .// all child ./ only first child
    try:  # check that the data is not empty
        vel = root.findall(".//Velocity")
    except AttributeError:
        print("Error: Velocity data cannot be read from the XML file")
        return None, None
    if len(vel) == 0:
        warnings.warn('Warning: Velocity data from XML is empty.')

    # find where all water suface elevation are
    try:
        wse = root.findall(".//WSE")
    except AttributeError:
        print("Error: water surface elevation cannot be read from the XML file")
        return None, None
    if len(wse) == 0:
        warnings.warn('Warning: Height data from XML is empty.')

    # find profile name and if there is more than one profile
    try:
        sim_name = root.findall(".//ProfileNames")
        sim_name = str(sim_name[0].text)
        sim_name = sim_name[1:-2] # erase firt and last " sign
        sim_name = sim_name.split('" "')
        nb_sim = len(sim_name)
    except AttributeError:
        warnings.warn("Warning: the number and name of the simulation cannot be read from the XML file.")
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
        warnings.warn("Warning: the name of the river station cannot be read from the XML file.")
        riv_name = []

    # take this out when done!!!
    test_creuse = False
    if test_creuse:
        vel = wse
        print('WARNING: dummy velocity data. DO NOT FORGET')

    # transform the Element data into float
    if len(vel) == len(wse):
        nbstat = len(vel)  # number of profiles
    else:
        nbstat = min(len(vel), len(wse))
        warnings.warn('WARNING: the length of height data and velocity data do not match.')
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
        print('Error: The velocity or height data could not be extracted. Format of the XML file should be checked.')
        return None, None

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
            warnings.warn('The reach and rivers names of the .geo file could not be found in the xml file.')

    riv_name = riv_name[::nb_sim]  # get the name only once
    return data_vel, data_wse, riv_name, nb_sim


def load_xml(xml_file, path):
    """
    This is a small utility function used by openxml_file and opengml_file to load an xml file
    :param xml_file: an xml file
    :param path: a path where the file is
    :return: the loaded data from the XML file
    """
    # check that the xml file has the right extension
    blob, ext_xml = os.path.splitext(xml_file)
    if ext_xml == '.xml' or ext_xml == '.gml':
        pass
    else:
        warnings.warn("Warning: File should be of type XML or GML")

    # load the XML file
    try:
        docxml = Etree.parse(os.path.join(path, xml_file))
        root = docxml.getroot()
    except IOError:
        print("Error: the file "+xml_file+" does not exist")
        return []

    return root


def open_geofile(geo_file, path):
    """
    A function to open the geometry file (.g0X) from HEC-RAS and to extract the (x,z) from each profile
    and the (x,y) if gereferenced
    :param geo_file: the HEC-RAS geometry file
    :param path: path to the geo file
    :return: a list with each river profile. Each profile is represented by a numpy array with the x and the altitude
     of each point in the profile, the coordinate of the profile in alist of np.array, the coordinate of the river
     and a list of string with the name of the reaches/ river in order
    """
    # check that the geo file has the right extension (.goX)
    blob, ext_geo = os.path.splitext(geo_file)
    if ext_geo[:3] == '.G0':
        warnings.warn("Warning: File of G0X type.")
    elif ext_geo[:3] != '.g0':
        warnings.warn("Warning: File should be of type .g0X such as .g01 ou .g02")

    # open the geo file
    try:
        with open(os.path.join(path, geo_file), 'rt') as f:
            data_geo = f.read()
    except IOError:
        print("Error: the file "+geo_file+" does not exist")
        return []

    # find the (x,z) data related to the profiles.
        # HEC_RAS manual p5-4: the geometry file is for-the-most-part self explanotary.
        # Unfortunately not for me. :-(
        # look for all Stat/Elev, then get rid of everything until next line
        # then save all data until not a digit (or white space) arrive

    exp_reg1 = "Sta/Elev=\s+\d+\s*\n([\s+\d+\.-]+)"
    data_profile_str = re.findall(exp_reg1, data_geo, re.DOTALL)
    if not data_profile_str:
        warnings.warn("Warning: no profile found, the geometry file might not be in the right format")
        return []
    data_profile = []
    try:
        for i in range(0, len(data_profile_str)):
                xz = pass_in_float_from_geo(data_profile_str[i], 8)
                data_profile.append(xz)  # fill a list with an array (x,z) for each profile
    except ValueError:
        print('Error: The profile data could be extracted from the geometry file. The format should be checked.')
        return []

    # load the coordinate of the river
    exp_reg2 = 'Reach\s+XY=\s+\d+\s*\n([\s+\d+\.-]+)'
    data_river_str = re.findall(exp_reg2, data_geo, re.DOTALL)
    # case of a straight river
    if not data_river_str:
        exp_reg21 = 'Rch X Y Up \& X Y Dn=([\s+\d+\.-]+,[\s+\d+\.-]+,[\s+\d+\.-]+,[\s+\d+\.-]+)'
        data_river_str = re.findall(exp_reg21, data_geo, re.DOTALL)
        data_river_str[0] = data_river_str[0].replace(',', ' ')
        if data_river_str:
            warnings.warn('Warning: The river is assumed to be straight.')
    if not data_river_str:
        warnings.warn('Warning: no river found, the geometry file might not be in the right format')
    try:
        data_river = []
        for i in range(0, len(data_river_str)):
            data_river.append(pass_in_float_from_geo(data_river_str[i], 16))
    except ValueError:
        print('The river data could not be extracted from the geometry file. The format should be checked.')
        return []

    # load the bank limit (where is the limit of the river without a flood)
    try:
        exp_reg22 = "Bank\sSta=([\s/+\d+\.-]+),([\s+\d+\.-]+)\n"
        data_bank_str = re.findall(exp_reg22, data_geo, re.DOTALL)
        data_bank_str = np.array(data_bank_str)
        data_bank_left = list(map(float, data_bank_str[:, 0]))
        data_bank_right = list(map(float, data_bank_str[:, 1]))
        data_bank = np.column_stack((data_bank_left, data_bank_right))
    except ValueError:
        print('Error: The location of the bank stations on the profile could not be extracted from the geometry file.')
        return []

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
            nb_pro_reach[i] = reach_nb_str.count('#Sta/Elev=')
        reach_nb_str = data_geo[b:]
        nb_pro_reach[i+1] = reach_nb_str.count('#Sta/Elev=')
        check_nb_pro_reach = len(data_profile_str) - np.sum(nb_pro_reach)
        if check_nb_pro_reach > 1:
            warnings.warn("Warning: The number of profile by reach might not be right.")
    else:
        nb_pro_reach = [len(data_profile_str)]

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
                    warnings.warn('Warning: At least one distance between profile is not found. Distance data erased.\
                     Might be a bridge or a culvert.')
                    erase = True
                    data_dist_str_i = '-99,0,-99'
            if data_dist_str_i[0] == ',':
                data_dist_str_i = '-99'+data_dist_str_i
                warnings.warn('Warning: One distance between left overbanks is not found.')
            if data_dist_str_i[-1] == ',':
                data_dist_str_i += '-99'
                warnings.warn('Warning: One distance between right overbanks is not found.')

            data_dist_i = np.array(list(map(float, data_dist_str_i.split(','))))
            if not erase:
                data_dist.append(data_dist_i)

    except ValueError:
        print('Error: The location of the bank stations could not be extracted from the geometry file.')
        return [], [], [], []

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
        warnings.warn('Warnings: The river profiles are not georeferenced. HYP: straight profiles. CHECK NECESSARY')
        coord_p = coord_profile_non_georeferenced(data_bank, data_dist, data_river, data_profile, nb_pro_reach)

    return data_profile, coord_p, data_river, reach_name, data_bank


def coord_profile_non_georeferenced(data_bank_all, data_dist_all, data_river_all, data_profile_all, nb_pro_reach):
    """
    This is a function to create the coordinates of the profile in the non-georeferenced case.
    This function is called by open geo_file()
    Hypothesis: The profile are straight and perpendicular to the river. The last profile is at the end of the river.

    :param data_bank_all: distance along the profile of bank station
    :param data_dist_all: the distance between the profile (left, center channel, right)
    :param data_river_all: the coordinate of the river
    :param data_profile_all: the (d,z) data of the profile
    :param nb_pro_reach: the number of profile by reach
    :return: the coordinates of the profile
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

            dact += dist_xy[i]
            m += len(ri)

        ar += len(data_profile)
    return coord_p


def open_sdffile(sdf_file, reach_name, path):
    """
    This is a function to load .sdf file from HEC-RAS v5
    To obtain this file, click on File, then "export GIS data" in HEC-RAS v5
    Export all reaches (select Reaches to export -. Full List -> Ok)
    :param sdf_file: the name of the sdf file
    :param reach_name, a list of string containing the name of the reaches/rivers in the order of the geo file
     (might not be the one of the sdf file)
    :param path: the path where the file is stored
    :return:
    """

    # check that the sdf file has the right extension (.sdf)
    # we might so the test two times, but so we are sure it is here
    blob, ext_sdf = os.path.splitext(sdf_file)
    if ext_sdf != '.sdf':
        warnings.warn("Warning: File should be of .sdf type.")

    # open the sdf file
    try:
        with open(os.path.join(path, sdf_file), 'rt') as f:
            data_sdf = f.read()
    except IOError:
        print("Error: the file "+sdf_file+" does not exist")
        return []

    # get the velocity data
    exp_reg1 = "VELOCITIES:\s*\n([\s+\d+\,\.-]+)"
    vel_str = re.findall(exp_reg1, data_sdf, re.DOTALL)

    if not vel_str:
        warnings.warn("Warning: no velocity data found, the .sdf file might not be in the right format")
        return []
    vel = []
    try:
        for i in range(0, len(vel_str)):
                vel_str[i] = vel_str[i].replace(',', ' ')
                vel_i = pass_in_float_from_geo(vel_str[i], -99)  # HYP: No data given without space -> -99
                vel.append(vel_i)
    except ValueError:
        print('Error: The velocity data could not be extracted from the sdf file.')
        return []

    # get the height data
    exp_reg2 = "WATER ELEVATION:\s*([\s+\d+\,\.-]+)"
    wse_str = re.findall(exp_reg2, data_sdf, re.DOTALL)
    if not wse_str:
        warnings.warn("Warning: no height data found, the .sdf file might not be in the right format")
        return []
    wse = []
    try:
        for i in range(0, len(wse_str)):
                wse_str[i] = wse_str[i].replace(',', ' ')
                sep_str = wse_str[i].split()
                wse_i = list(map(float, sep_str))
                for j in range(0, len(wse_i)):
                    wse.append(wse_i[j])
    except ValueError:
        print('Error: The water height data could not be extracted from the sdf file.')
        return []

    # get the reach and river name
    exp_reg_extra = "BEGIN CROSS-SECTIONS:(.+)END CROSS-SECTION"
    data_sdf2 = re.findall(exp_reg_extra, data_sdf, re.DOTALL)
    exp_reg3 = "STREAM ID:\s*(.+)\n"
    stream_str = re.findall(exp_reg3, data_sdf2[0])
    exp_reg4 = "REACH ID:\s*(.+)\n"
    reach_str = re.findall(exp_reg4, data_sdf2[0])
    if not stream_str:
        warnings.warn("Warning: Stream names could not be extracted from the .sdf file")
    if not reach_str:
        warnings.warn("Warning: Reach names could not be extracted from the .sdf file")
    stream_str = get_rid_of_white_space(stream_str)
    reach_str = get_rid_of_white_space(reach_str)

    # get the number of simulation
    exp_reg6 = "NUMBER OF PROFILES:\s*([\s*\d+]+)"
    nb_sim_str = re.findall(exp_reg6, data_sdf, re.DOTALL)

    if not nb_sim_str:
        warnings.warn("Warning: the number of profiles is not found in the .sdf file")
        return []
    try:
        nb_sim = int(float(nb_sim_str[0]))
    except ValueError:
        print('Error: The number of simulation could not be extracted from the .sdf file')
        return []

    # get the name of the profile (riv_name)
    exp_reg5 = "STATION:\s*(.+)\n"
    riv_name_a = re.findall(exp_reg5, data_sdf)
    riv_name = []
    for i in range(0, len(riv_name_a)):  # could be coded better
        for s in range(0, nb_sim):
            riv_name.append(riv_name_a[i])
    if not riv_name:
        warnings.warn('Warning: Profile name could not be extracted from the sdf file.')

    [wse, vel, riv_name] = reorder_reach(wse, vel,riv_name, reach_name, reach_str, stream_str, nb_sim)

    riv_name = riv_name[::nb_sim]  # get the name only once
    return vel, wse, riv_name, nb_sim


def reorder_reach(wse, vel, riv_name, reach_name, reach_str, stream_str, nb_sim):
    """
    The order of the reach in HABBY is the order given in the geo file. It can be given in any order ni the orher file.
    (xml, sdf, rep,...). here is a dunction to re-roder the reaches based on theri name
    name should not have white space at the end but have white space into them
    :param wse: water height data (list of np.array for each profile)
    :param vel: velocity data (list of np.array for each profile)
    :param riv_name: the name of the profile (yeah I know it is not really logical as a name)
    :param reach_name: the name of the reach and stream (stream,reach) in the geo file order
    :param reach_str: the name of the reach in the anaylsed file order
    :param stream_str: the name of the stream in the anaylsed file order
    :param nb_sim the number of simulation
    :return: wse, vel, riv_name re-ordered
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
                        print("Error: Some reaches are possibly missing. It is necessary to export all reaches.")
                        print("Click on Select Reach to Export in GIS export of HEC-RAS 5")
                        out_print = False

            m += len(f_reach)
        if m == 0:
            warnings.warn('The reach and rivers names of the .geo file could not be found in the .sdf file.')

    return wse, vel, riv_name


def get_rid_of_white_space(stream_str):
    """
    a small fonction to get rid of white space at the end of name which could contain white space
    :param stream_str the name of the string
    :return the same name without str
   """
    # get rid of space (but not all the space!)
    for i in range(0, len(stream_str)):
        stream_str[i] = stream_str[i].strip()

    return stream_str


def open_repfile(report_file, reach_name, path, data_profile, data_bank):
    """
    A function to open the report file (.rep) from HEC-RAS. To obtain the report file, click on File, generate Report,
    Choose Flow data, Geometry data and, in specific Table, choose Cross section Table and Flow distribution.
    :param report_file:
    :param reach_name :a list of string containing the name of the reaches/rivers in the order of the geo file
     (might not be the one of the sdf file)
    :param path: the path where the file is stored
    :param data_profile: the data from each profile from the geo file
    :param data_bank: the position of the bank limit
    :return: velocity and the water surface elevation for each river profiles in a list of np.array,
    the number of simulation (int) and the name of the river profile (list of string)
    """
    # check that the report file has the right extension (.sdf)
    # we might so the test two times, but so we are sure it is here
    blob, ext_sdf = os.path.splitext(report_file)
    if ext_sdf != '.rep':
        warnings.warn("Warning: File should be of .rep type.")

    # open the rep file
    try:
        with open(os.path.join(path, report_file), 'rt') as f:
            data_rep = f.read()
    except IOError:
        print("Error: the file "+report_file+" does not exist")
        return []

    # obtain WSE data
    exp_reg = "W.S. Elev\s*\(\D+\)\s*([\d\.-]+)\D"
    wse_str = re.findall(exp_reg, data_rep)
    if not wse_str:
        warnings.warn("Warning: Water level is empty")
    try:
        wse = list(map(float, wse_str))
    except ValueError:
        print("The water level height could not be , could not be extracted from the rep file")

    # obtain the number of simulation
    # it is not really given so we we could the number of cross section output
    exp_reg1 = 'CROSS SECTION OUTPUT'
    cros_sec_o = re.findall(exp_reg1, data_rep)
    nb_sim = len(cros_sec_o)/len(data_profile)
    if np.floor(nb_sim) != nb_sim:
        warning.warn("The number of simulation does not seems right. It should be an integer.")
    nb_sim = int(nb_sim)

    # obtain the name of the reaches and the name of the profile
    exp_reg = "CROSS SECTION\s*\n+(.*\n.*\n)"
    name_str = re.findall(exp_reg, data_rep)
    if not name_str:
        warnings.warn("The profile name could be extracrted from the .rep file")
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

    # obtain velocity data
    # if not georeferenced only 3 velocity by channel, other wise all velocity
    exp_reg = "Avg. Vel.\s*\(\D+\)([\d\.\s]+)\n"
    vel_av_str = re.findall(exp_reg, data_rep)
    if not vel_av_str:
        warnings.warn("Warning: the velocity data is empty (.rep file)")

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
        print("Error: the velocity could not be extracted from the .rep file (non-georeferenced case)")

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
        print("Error: the coordinate of the velocity could not be extracted from the .rep file (non-georeferenced case)")

    # put the (x and v) data together
    vel = []
    for i in range(0, len(vel_av)):
        x_av_i = x_av[i]
        vel_i = np.column_stack((x_av_i[m[i]], vel_av[i]))
        vel.append(vel_i)

    [wse, vel, riv_name] = reorder_reach(wse, vel, riv_name, reach_name, reach_str, stream_str, nb_sim)

    return vel, wse, riv_name, nb_sim


def pass_in_float_from_geo(data_str, len_number):
    """
    A small utility function to pass the string data into float for open_geofile and sdf file
    :param data_str: the data in a string
    :param len_number the number of digit for one numer
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
            warnings.warn("Two coordinates were not separated by space. HYP: Number of digit is 8 or 16.")
        except ValueError:
            print("Error: Data are not number.")
    return xz


def find_coord_height_velocity(coord_pro, data_profile, vel, wse, nb_sim):
    """
    find the coordinates of the height/velocity
    :param coord_pro: the coordinate (x,y) of the profile
    :param data_profile: data concening the geometry of the profile, notably (x,z)
    :param vel the velocity data
    :param wse the water sufrace elevation
    :param nb_sim the number of simulation in case there is more than one
    :return: for each simulation, a list of np.array representing (x,y,v) and (x,y,h,)
    Careful the height is on the node and the velocity is by zone
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
            dist_tot = np.sum(dist)  # coordinates in (x,y)
            dist_pro = x[-1]  # coordinates in meter or feet
            dist2 = dist * dist_pro / dist_tot  # also meter or feet
            vel_x = dist_pro * vel_p[:, 0]

            # get the first and end profile point
            xy2[:, :2] = coord_pro_p[0, :]
            zone_v_p[:, :2] = coord_pro_p[0, :]
            if vel_p[0, 0] < -1e30:  # HEC-RAS-> +/-X.XXe35 = end or beginning of profile (if I get it right)
                zone_v_p[0, :2] = coord_pro_p[0, :]
                mv = 1
            if vel_p[-1, 0] > 1e30:
                zone_v_p[-1, :2] = coord_pro_p[-1, :]

            # find the new coordinates
            for i in range(0, len(dist)):
                xi = x[(x > dact) & (x <= dact + dist2[i])]
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

        xy_h_all.append(xy_h)
        zone_v_all.append(zone_v)
    return xy_h_all, zone_v_all


def figure_xml(data_profile, coord, coord_r, xy_h_all, zone_v_all,  pro, nb_sim=0, name_profile='no_name', coord_p2=-99):
    """
    A small function to plot the results
    :param data_profile (list with np.array)
    :param coord: (x,y) data of the profile
    :param coord_r: (x,y) data of the river
    :param xy_h_all: (x,y, h) for the height data for each simulation
    :param zone_v_all: (x,y, v) for the velocity data. velocity is by zone. for each simulation.
    the (x,y) indicates the start of the zone which end with the next velocity
    :param pro: a list with which profile should be plot [2,3,4]
    :param nb_sim which simulatino sould be plotted,
    :param name_profile: a list of string with the name of the profile
    :param coord_p2 the data of the profile when non geo-referenced, optional
    :return: none
    """

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
        ax1 = subplot(313)
        # find the water limits
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
        # update velocity data
        v_xy_i_wet = v_xy_i[(xint1 <= v_xy_i[:, 2]) & (v_xy_i[:, 2] <= xint2), 2:]
        if len(v_xy_i_wet) > 0:
            v_xy_i_wet = np.vstack(([[0, 0], [xint1, v_xy_i[0, 3]], v_xy_i_wet, [xint2, 0]]))
        else:  # case with no velocity in the water
            v_xy_i_wet = np.vstack(([[0, 0], [xint1, v_xy_i[0, 3]], [xint2, 0]]))
        # print velocity
        step(v_xy_i_wet[:, 0], v_xy_i_wet[:, 1], where='post', color='r')
        xlim([np.min(xz[:, 0]-1)*0.95, np.max(xz[:, 0])*1.05])
        xlabel("x [m or ft]")
        ylabel(" Velocity [m or ft / sec]")
        ax1 = subplot(211)
        plot(xz[:, 0], xz[:, 1], 'k')  # profile
        fill_between(xz[:, 0], xz[:, 1],hi + xz[:, 1], where=xz[:, 1] < hi + xz[:, 1], facecolor='blue', alpha=0.5, interpolate=True)
        xlabel("x [m or ft]")
        ylabel("altitude of the profile [m or ft]")
        if name_profile == 'no_name':
            title("Profile " + str(i))
        else:
            title("Profile " + name_profile[i])
        legend(("Profile", "Water surface"))
        xlim([np.min(xz[:, 0]-1)*0.95, np.max(xz[:, 0])*1.05])
        m += 1

    # plot the profile in the (x,y) plane
    fig2 = figure(len(pro))
    txt_pro = "Profile position"
    txt_h = "Water height coordinates"
    txt_v = "Velocity coordinates"
    xmip = 1000
    xmap = -1000

    rcParams.update({'font.size': 9})
    for i in range(0,len(coord_r)):
        coord_r_i = coord_r[i]
        plot(coord_r_i[:, 0], coord_r_i[:, 1], label='River')
    for j in range(0, len(coord)):
        coord_j = coord[j]
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
    title("Position of the profiles")
    axis('equal') # if right angle are needed
    legend()
    show()


def main():

    path_test = r'C:\Users\diane.von-gunten\Documents\HEC Data\HEC-RAS\Unsteady Examples'
    #path_test = r"D:\gros_fichier_pas_sauvegarder\2-Modele-HEC-RAS\Ram"
    path_test = r'C:\Users\diane.von-gunten\Documents\HEC Data\HEC-RAS\2D Unsteady Flow Hydraulics\Muncie'
    #name = 'BaldEagleDamBrk'
    name = 'Muncie'
    name_xml = name+ '.RASexport.sdf'
    #name_xml = name + '.rep'
    #name_xml = name+ '.O04.xml'
    name_geo = name+'.g04'

    [xyh, zone_v] = open_hecras(name_geo, name_xml, path_test, path_test)

if __name__ == '__main__':
    main()
