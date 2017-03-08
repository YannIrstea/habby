import os
import re
import numpy as np
import matplotlib.pyplot as plt
import sqlite3
from src import load_hdf5
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

def load_evha_curve(filename, path):
    """
    This function is used to load the preference curve in the EVHA form . It will be useful to create xml preference
    file, but it is not used direclty by HABBY. This function does not have much control on user input as it is planned
    to be used only by people working on HABBY. The order of the data in the file must be height, velocity, substrate

    :param filename: the name of file containing the preference curve for EVHA
    :param path: the path to this file
    :return: preference for height, vel, sub in a list of list form, name of the fish, code, stade and description
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
                if new_data1old <= new_data1:
                    new_data1old = new_data1
                    if first_point:
                        pref_here = [[new_data1], [new_data2]]
                        first_point = False
                    else:
                        pref_here[0].extend([new_data1])
                        pref_here[1].extend([new_data2])
                else: # go from height to velocity
                    if ind_hvs == 0:
                        height.append(pref_here)
                    if ind_hvs == 1:
                        vel.append(pref_here)
                    ind_hvs += 1
                    pref_here = []
                    first_point = True
                    new_data1old = -1
        # go from velcoity to substrate
        sub.append(pref_here)

    return height, vel, sub, code_fish, name_fish, stade, descri


def figure_pref(height, vel, sub, code_fish, name_fish, stade):
    """
    This function is used to plot the preference curves.

    :param height: the height preference data (list of list)
    :param vel: the height preference data (list of list)
    :param sub: the height preference data (list of list)
    :param code_fish: the three letter code which indiate which fish species is analyzed
    :param name_fish: the name of the fish analyzed
    :param stade: the name of the stade analyzed (ADU, JUV, ...)
    """

    if len(stade)> 1:  # if you take this out, the commande axarr[x,x] does not work as axarr is only 1D
        f, axarr = plt.subplots(len(stade),3, sharey='row')
        plt.suptitle('Preference curve of ' + name_fish + ' (' + code_fish + ') ')
        for s in range(0, len(stade)):
            axarr[s, 0].plot(height[s][0], height[s][1], 'b')
            axarr[s, 0].set_xlabel('Water height [m]')
            axarr[s, 0].set_ylabel('Coeff. Pref ' + stade[s])
            axarr[s, 0].set_ylim([0,1.1])

            axarr[s, 1].plot(vel[s][0], vel[s][1], 'r')
            axarr[s, 1].set_xlabel('Velocity [m/sec]')
            axarr[s, 1].set_ylabel('Coeff. Pref ' + stade[s])
            axarr[s, 1].set_ylim([0, 1.1])

            axarr[s, 2].plot(sub[s][0], sub[s][1], 'k')
            axarr[s, 2].set_xlabel('Substrate []')
            axarr[s, 2].set_ylabel('Coeff. Pref ' + stade[s])
            axarr[s, 2].set_ylim([0, 1.1])
    else:
        f, axarr = plt.subplots(3, 1, sharey='row')
        plt.suptitle('Preference curve of ' + name_fish + ' (' + code_fish + ') ')
        axarr[0].plot(height[0][0], height[0][1], 'b')
        axarr[0].set_xlabel('Water height [m]')
        axarr[0].set_ylabel('Coeff. Pref ' + stade[0])
        axarr[0].set_ylim([0, 1.1])

        axarr[1].plot(vel[0][0], vel[0][1], 'r')
        axarr[1].set_xlabel('Velocity [m/sec]')
        axarr[1].set_ylim([0, 1.1])

        axarr[2].plot(sub[0][0], sub[0][1], 'k')
        axarr[2].set_xlabel('Substrate []')
        axarr[2].set_ylabel('Coeff. Pref ' + stade[0])
        axarr[2].set_ylim([0, 1.1])


def create_and_fill_database(path_bio, name_database, attribute):
    """
    This function create a new database when Habby starts. The goal of creating a database is to avoid freezing the GUI
    when info on the preference curve are asked. So it is possible to select one curve and have information without
    seeing too much of a delay. This is not used anymore by HABBY as the xml file is really small.
    It could however be useful if the xml file becomes too big. In this case, this function could be
    called if modification are found in the pref_file folder and would create a database.

    The attribute can be modified, but they should all be of text type. It is also important to keep stage at the first
    attribute. The modified attribute should reflect the attribute of the xml file. If it not possible, lines should
    be added in the "special case" attributes". The main table with the data is called pref_bio.

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
        print('Warning: the name of the database should have a .db extension \n')

    pathname_database = os.path.join(path_bio, name_database)

    # erase database (to be done at the beginning because rename database at the end is annoying)
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
    rea0 = rea0[:-1] # last comma
    rea0 += ") values("

    # get all xml name
    preffiles = load_hdf5.get_all_filename(path_bio, '.xml')
    if len(preffiles) < 1:
        print('Error: no xml preference file found. Please check the biology folder. \n')
        return

    # for all xml file
    found_one = False
    j = 0
    for preffile in preffiles:
        data = [None]*(len(attribute)-1)

        # load the file
        try:
            try:
                docxml = ET.parse(os.path.join(path_bio,preffile))
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file "+preffile + " does not exist \n")
                break
        except ET.ParseError:
            print("Warning: the xml file "+preffile + "is not well-formed.\n")
            break

        # get the data
        i = -1
        for att in attribute:
            # special attribute
            if att == 'Stage':  # this should be the first attribute as i ==-1 !
                stages = root.findall(".//stage")
                if len(stages) == 0:
                    print('no stage found in '+preffile+ "\n")
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
                data[i] = root.find('.//CdAppelTaxon[@schemeAgencyID="SANDRE"]')
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
                data[i] = root.find(".//"+att)
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
                        d = d.replace("'"," ")
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
                j +=1

        found_one= True

    if not found_one:
        print('Error: No preference file could be read. Please check the biology folder.\n')


def execute_request(path_bio, name_database, request):
    """
    This function execute the SQL request given in the string called request. it saves the found data in a variable.
    The idea is to use this function for SELELCT X FROM X WHERE ... , not really to handle all possible request.
    It also opens and close the database name_database to do this. This is not used anymore by HABBY as we do not use
    a database. it could however be useful if the xml file becomes too big.

    :param path_bio: the path to the biological information (usually ./biology)
    :param name_database: the name of the database (string) without the path
    :param request: the SQL request in a string form
    :return: the result
    """

    blob, ext = os.path.splitext(name_database)
    if ext != ".db":
        print('Warning: the name of the database should have a .db extension \n')
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


def load_xml_name(path_bio, attributes):
    """
    This function looks for all preference curves found in the path_bio folder. It extract the fish name and the stage.
    to be corrected if more than one language. The name of attribute_acc should be coherent with the one from the xml
    file apart from the common name which shoulf be in the form language_common_name (so we can wirte something in the
    GUI to get all langugage if we get something else than English or French)

    :param path_bio: the path to the biological function
    :param attributes: the list of attribute which should be possible to search from the GUI or, more generally
           which should be in data-fish which is returned.
    :return: the list of stage/fish species with the info from [name for GUi, s, xmlfilename, attribute_acc without s]
    """
    # get all xml name
    preffiles = load_hdf5.get_all_filename(path_bio, '.xml')
    if len(preffiles) < 1:
        print('Error: no xml preference file found. Please check the biology folder. \n')
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
                print("Warning: the xml file " + preffile + " does not exist \n")
                break
        except ET.ParseError:
            print("Warning: the xml file " + preffile + "is not well-formed.\n")
            break

        i = -1
        all_ok = True
        for att in attributes:
            att_langue = att.split('_')
            # special attribute
            if att == 'Stage':  # this should be the first attribute as i ==-1 !
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
            elif len(att_langue) == 3 and att_langue[1] == 'common' and att_langue[2] == 'name':
                    b = root.findall('.//ComName')
                    if b is not None:
                        for bi in b:
                            try:
                                if bi.attrib['Language']== att_langue[0]:
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
        for s in stages:
                data_s = [data[4] + ': ' + s + ' - ' + data[5], s, preffile] # order mattter HERE! (ind: +3)
                data_s.extend(data)
                data_fish.append(data_s)
        found_one = True

    if not found_one:
        print('Error: No preference file could be read. Please check the biology folder.\n')

    data_fish = np.array(data_fish)

    return data_fish


def plot_hydrosignature(xmlfile):
    """
    This function plots the hydrosignature in the vclass and hclass given in the xml file.
    It does only work if: units are SI (meter and m/s) and if the order of data is 'velocity increasing
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
    hs = root.find('hydrosignature_of_the_sampling_data')
    if hs is not None:
        hclass = hs.find('class_height_of_water')
        vclass = hs.find('class_velocity')
        data = hs.find('hydrosignature_values')
        if vclass is not None and hclass is not None and data is not None:
            if hclass.attrib['units'] == 'meter' and vclass.attrib['units'] == 'meterspersecond':
                if data.attrib['description_mode'] == 'velocity increasing and then heigth of water increasing':
                    vclass = vclass.text.split()
                    hclass = hclass.text.split()
                    data = data.text.split()
                    try:
                        vclass = list(map(float, vclass))
                        hclass = list(map(float, hclass))
                        data = list(map(float, data))
                    except ValueError:
                        print('Warning: hydrosignature data could not be transformed to float')
                        return
                else:
                    print('Warning: no hydrosignature found in the xml file (1). \n')
                    return
            else:
                print('Warning: no hydrosignature found in the xml file (2). \n')
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

    if len(data) != (len(vclass)-1) * (len(hclass)-1):
        print('Warning: the data for hydrosignature is not of the right length.\n')
        return

    data = data.reshape((len(vclass)-1, len(hclass)-1))

    plt.figure()
    plt.imshow(data, extent=[vclass.min(), vclass.max(), hclass.min(), hclass.max()], cmap='Blues',
               interpolation='nearest')
    plt.title('Hydrosignature')
    plt.xlabel('V [m/s]')
    plt.ylabel('H [m]')
    plt.locator_params(nticks=3)
    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Relative area [%]')
    plt.grid()


def main():
    """
    Used to test the module on the biological preference
    """

    # load the pref
    path = r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF-part1-Multispe1998'
    path = r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF-part2-Lamourouxetal1999'
    filenames = load_hdf5.get_all_filename(path, '.PRF')
    for i in range(0, len(filenames)):
        [height, vel, sub, code_fish, name_fish, stade, descri] = load_evha_curve(filenames[i], path)
        figure_pref(height, vel, sub, code_fish, name_fish, stade)
    plt.show()


if __name__ == '__main__':
    main()