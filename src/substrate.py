import shapefile
import os
import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
import matplotlib.tri as tri
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import time
from src import load_hdf5
from src import manage_grid_8
import triangle
from random import randrange


def open_shp(filename, path):
    """
    This function open a ArcGIS shpaefile.

    :param filename: the name of the shapefile
    :param path: the path to this shapefile
    :return: a shapefile object as define in the model
    """

    # test extension and if the file exist
    blob, ext = os.path.splitext(filename)
    if ext != '.shp':
        print('Warning: the file does not have a .shp extension.')
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The shapefile " + filename + " does not exist.")
        return [-99], [-99], [-99]
    # read shp
    try:
        sf = shapefile.Reader(file)
    except shapefile.ShapefileException:
        print('Error: Cannot open the shapefile ' + filename + ', or one of the associated files (.shx, .dbf)')
        return [-99], [-99], [-99]

    return sf


def get_all_attribute(filename, path):
    """
    This function open a shapefile and get the list of all the attibute which is contains in it.

    :param filename: the name of the shpae file
    :param path: the path to this shapefile
    :return: a list with the name and information of all attribute. The form of each element of the list
             is [name(str), type (F,N), int, int]
    """

    sf = open_shp(filename, path)
    fields = sf.fields
    if len(fields) > 1:
        fields = fields[1:]
    else:
        print('Warning: No attibute found in the shapefile.')

    return fields


def get_useful_attribute(attributes):
    """
    This function find if the substrate was given in percentage or coarser/dominant/accesory and get the attribute
    or header name useful to load the substrate. If the subtrate is given by percentage, it is important to get
    attribute in order (S1, S2, S3) and not (S3, S1,S2) for this function and the next functions.

    :param attributes: The list of attribute from the shp file or the header list from the text file
    :return: The attribute type as int (percentage=1 and coarser/... = 0 and failed = -99) and the attribute names
                    If we are in the attribute type 0, attribute list is in the order of: coarser, dominant, and accessory

    """

    # all the different attribute names which can be accepted in the shape file
    pg = ['plus gros', 'coarser', 'PG', 'PLUS GROS', 'COARSER']
    dom = ['dominant', 'DOMINANT', 'DM']
    acc1 = ['acc', 'ACC', 'ACCESSORY', 'accessoire', 'ACCESSOIRE']
    # create per_name
    per_all = []
    for m in range(0,15):
        per_all.append('S' + str(m))
        per_all.append('s' + str(m))

    # stating
    found_per = False
    found_pg = False
    found_one_pg = 0  # if we found dominant and "plus gros", we get found_pg = True
    attribute_type = -99 # -99 indicates a failed load.
    attribute_name = ['-99','-99', '-99']
    num_here = 0

    for f in attributes:

        if f[0] in pg:
            found_one_pg += 1
            attribute_name[0] = f[0]
        if f[0] in dom:
            found_one_pg += 1
            attribute_name[1] = f[0]
        if f[0] in acc1:
            attribute_name[2] = f[0]

        if found_one_pg == 2:
            found_pg = True
            attribute_type = 0

        if f[0] in per_all:
            num_here +=1
            found_per = True
            attribute_type = 1
            if f[-1] == '1':
                attribute_name[0] = f[0]
            if f[-1] == '2':
                attribute_name[1] = f[0]
            if f[-1] == '3':
                attribute_name[2] = f[0]
            else:
                attribute_name.append(f[0])

        if found_per and found_pg:
            print('Error: The attributes of substrate shapefile cannot be understood: mixing betweeen percentage and'
                  'coarser/dominant attributes.\n')
            attribute_type = -99
            return

    if not found_pg and not found_per:
        print('Error: The attribute names of the substrate could not be recognized.\n')
        attribute_type = -99

    return attribute_type, attribute_name


def load_sub_shp(filename, path, code_type, dominant_case=0):
    """
    A function to load the substrate in form of shapefile.

    :param filename: the name of the shapefile
    :param path: the path where the shapefile is
    :param code_type: the type of code used to define the substrate (string)
    :param dominant_case: an int to manage the case where the transfomation form percentage to dominnat is unclear (two
           maxinimum percentage are equal from one element). if -1 take the smallest, if 1 take the biggest,
           if 0, we do not know.
    :return: grid in form of list of coordinate and connectivity table (two list)
            and an array with substrate type and a boolean which allows to get the case where we have tow dominant case

    """
    # initialization
    xy = []  # point
    ikle = []  # connectivity table
    sub_dom = []  # dominant substrate
    sub_pg = []  # coarser substrate ("plus gros")
    ind = 0
    failload = [-99], [-99], [-99], [-99], True

    # open shape file (think about zero or one to start! )
    sf = open_shp(filename, path)

    # get point coordinates and connectivity table in two lists
    shapes = sf.shapes()
    for i in range(0,len(shapes)):
        p_all = shapes[i].points
        ikle_i = []
        for j in range(0, len(p_all)-1):  # last point of sahpefile is the first point
            try:
                ikle_i.append(int(xy.index(p_all[j])))
            except ValueError:
                ikle_i.append(int(len(xy)))
                xy.append(p_all[j])
        ikle.append(ikle_i)

    # get all the attributes in the shape file
    fields = sf.fields

    # find where the info is and how was given the substrate (percentage or coarser/dominant/accessory)
    [attribute_type, attribute_name] = get_useful_attribute(fields)
    if attribute_type == -99:
        return failload

    # if percentage type
    if attribute_type == 1:
        attribute_name_all = get_all_attribute(filename, path)
        record_all = []
        indf = 0
        # get the data and pass it int
        for f in fields:
            if f[0] in attribute_name:
                record_here = sf.records()
                record_here = np.array(record_here)
                record_here = record_here[:,ind]
                try:
                    record_here = list(map(int, record_here))
                except ValueError:
                    print('Error: The substate code should be formed by an int.\n')
                    return failload
                record_all.append(record_here)
                ind += 1
        record_all = np.array(record_all)
        # get the domainant abd coarser from the percentage
        sub_dom = [0] * len(record_all[0])
        sub_pg = [0] * len(record_all[0])
        for e in range(0, len(record_all[0])):
            record_all_i = record_all[:, e]
            # let find the dominant
            # we cannot use argmax as we need all maximum value, not only the first
            inds = list(np.argwhere(record_all_i == np.max(record_all_i)).flatten())
            if len(inds) > 1:
                # if we have the same percentage for two dominant we send back the function to the GUI to ask the
                # user. It is called again with the arg dominant_case
                if dominant_case == 0:
                    return [-99], [-99], [-99], [-99], False
                elif dominant_case == 1:
                    sub_dom[e] = inds[-1]+1
                elif dominant_case == -1:
                    #sub_dom[e] = int(attribute_name_all[inds[0]][0][1])
                    sub_dom[e] = inds[0]+1
            else:
                sub_dom[e] = inds[0]+1
            # let find the coarser (the last one not equal to zero)
            ind = np.where(record_all_i[record_all_i != 0])[0]
            sub_pg[e] = ind[-1] + 1
        # now let's checked and change code
        if np.any(sum(sub_pg)) !=100 and np.any(sum(sub_dom)) != 100:
            print('Warning: Substrate data is given in percentage. However, it does not sum to 100% \n')
        if code_type == 'Cemagref':
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The Cemagref code should be formed by an int between 1 and 8. (2)\n')
                return failload
            elif max(sub_dom) > 8 or max(sub_pg) > 8:
                print('Error: The Cemagref code should be formed by an int between 1 and 8. (3)\n')
                return failload
        # code type edf - checked and transform
        elif code_type == 'EDF':
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The edf code should be formed by an int between 1 and 8. (2)\n')
                return failload
            elif max(sub_dom) > 8 or max(sub_pg) > 8:
                print('Error: The edf code should be formed by an int between 1 and 8. (3)\n')
                return failload
            else:
                sub_dom = edf_to_cemagref(sub_dom)
                sub_pg = edf_to_cemagref(sub_pg)
        # code type sandre
        elif code_type == 'Sandre':
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The sandre code should be formed by an int between 1 and 12. (2)\n')
                return failload
            elif max(sub_dom) > 12 or max(sub_pg) > 12:
                print('Error: The sandre code should be formed by an int between 1 and 12. (3)\n')
                return failload
            else:
                sub_dom = sandre_to_cemagref(sub_dom)
                sub_pg = sandre_to_cemagref(sub_pg)
        else:
            print('Error: The substrate code is not recognized.\n')
            return failload


    # pg/coarser/accessory type
    elif attribute_type == 0:
        for f in fields:
            if f[0] == attribute_name[0] or f[0] == attribute_name[1]:  # [0] coarser and [1] pg
                # read for all code type
                record_here = sf.records()
                record_here = np.array(record_here)
                record_here = record_here[:, ind-1]
                try:
                    record_here = list(map(int, record_here))
                except ValueError:
                    print('Error: The substate code should be formed by an int.\n')
                    return failload

                # code type cemagref - checked
                if code_type == 'Cemagref':
                    if min(record_here) < 1:
                        print('Error: The Cemagref code should be formed by an int between 1 and 8. (2)\n')
                        return failload
                    elif max(record_here) > 8:
                        print('Error: The Cemagref code should be formed by an int between 1 and 8. (3)\n')
                        return failload
                # code type edf - checked and transform
                elif code_type == 'EDF':
                    if min(record_here) < 1:
                        print('Error: The edf code should be formed by an int between 1 and 8. (2)')
                        return [-99], [-99], [-99], [-99], True
                    elif max(record_here) > 8:
                        print('Error: The edf code should be formed by an int between 1 and 8. (3)')
                        return [-99], [-99], [-99], [-99], True
                    else:
                        record_here = edf_to_cemagref(record_here)
                # code type sandre
                elif code_type == 'Sandre':
                    if min(record_here) < 1:
                        print('Error: The sandre code should be formed by an int between 1 and 12. (2)\n')
                        return failload
                    elif max(record_here) > 12:
                        print('Error: The sandre code should be formed by an int between 1 and 12. (3)\n')
                        return failload
                    else:
                        record_here = sandre_to_cemagref(record_here)
                else:
                    print('Error: The substrate code is not recognized.\n')
                    return failload

                # now that we have checked and transform, give the data
                if f[0] == attribute_name[0]:
                    sub_pg = record_here
                if f[0] == attribute_name[0]:
                    sub_dom = record_here
            ind += 1

    else:
        print('Error: Type of attribute not recognized.\n')
        return failload

    return xy, ikle, sub_dom, sub_pg, True


def edf_to_cemagref(records):
    """
    This function passes the substrate data from the code type 'EDF" to the code type "Cemagref". As the code 1 from EDF
    can be the code 2 or code 1 in Cemagref, a code 1 in EDF is code 1 in Cemagref half of the time and code 2 the
    other half of the time. This function is not optimized yet. For the definiction of the code, see the tabular at the 14
    of the LAMMI manual. THIS IS NOT RIGHT AS CLASS ARE NOT SPEAREATED IDENTICALLY,  TO BE CORRECTED !!!

    :param records: the substrate data in code edf
    :return: the substrate data in code cemagref

    """
    new_record = []
    one_give_one = False
    for r in records:
        if r == 1:
            if one_give_one:
                new_record.append(1)
                one_give_one = False
            else:
                new_record.append(2)
                one_give_one = True
        elif r == 2:
            new_record.append(3)
        elif r == 3:
            new_record.append(4)
        elif r == 4:
            new_record.append(5)
        elif r == 5:
            new_record.append(6)
        elif r == 6:
            new_record.append(6)
        elif r == 7:
            new_record.append(7)
        elif r == 8:  # slabs? -> check this
            new_record.append(8)

    return new_record


def sandre_to_cemagref(records):
    """
    This function passes the substrate data from the code type "Sandre" to the code type "Cemagref". This function is
    not optimized yet. For the definition of the code, see the tabular at the 14 of the LAMMI manual.

    :param records: the substrate data in code samdre
    :return: the substrate data in code cemagref

    """

    new_record = []
    for r in records:
        if r == 1:
            new_record.append(1)
        elif r == 2:
            new_record.append(2)
        elif r == 3:
            new_record.append(3)
        elif r == 4:
            new_record.append(3)
        elif r == 5:
            new_record.append(4)
        elif r == 6:
            new_record.append(4)
        elif r == 7:
            new_record.append(5)
        elif r == 8:
            new_record.append(5)
        elif r ==9:
            new_record.append(6)
        elif r ==10:
            new_record.append(6)
        elif r == 11:
            new_record.append(7)
        elif r == 12:
            new_record.append(8)

    return new_record


def load_sub_txt(filename, path, code_type):
    """
    A function to load the substrate in form of a text file. The text file must have 4 columns x,y coordinate and
    xoarser substrate type, dominant substrate type, no header or title. It is transform to a grid using a voronoi
    transformation.

    :param filename: the name of the shapefile
    :param path: the path where the shapefile is
    :param code_type: the type of code used to define the substrate (string)
    :return: grid in form of list of coordinate and connectivity table (two list)
             and an array with substrate type and (x,y,sub) of the orginal data
    """
    failload = [-99], [-99], [-99], [-99], [-99], [-99],[-99],[-99]
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The txt file "+filename+" does not exist.\n")
        return failload
    # read
    with open(file, 'rt') as f:
        data = f.read()
    data = data.split()
    if len(data) % 4 != 0:
        print('Error: the number of column in ' + filename+ ' is not four. Check format.\n')
        return failload
    # get x,y (you might have alphanumeric data in the substrate column)
    x = [data[i] for i in np.arange(0, len(data), 4)]
    y = [data[i] for i in np.arange(1, len(data), 4)]
    sub_pg = [data[i] for i in np.arange(2, len(data), 4)]
    sub_dom = [data[i] for i in np.arange(3, len(data), 4)]
    try:
        x = list(map(float,x))
        y = list(map(float,y))
    except TypeError:
        print("Error: Coordinates (x,y) could not be read as float. Check format of the file " + filename +'.\n')
        return failload
    # Voronoi
    point_in = np.vstack((np.array(x), np.array(y))).T
    vor = Voronoi(point_in)
    xy = vor.vertices
    xy = np.reshape(xy, (len(xy), len(xy[0])))
    xgrid = xy[:, 0]
    ygrid = xy[:, 1]
    ikle = vor.regions
    ikle = [var for var in ikle if var]  # erase empy element
    # because Qhul from Vornoi has strange results
    # it create element with a value -1. this is not the last point!
    # so we take out all element with -1
    ikle = [var for var in ikle if len(var) == len([i for i in var if i>0])]
    # in addition it creates cells which are areally far away for the center
    ind_bad = []
    maxxy = [max(x), max(y)]
    minxy = [min(x), min(y)]
    i = 0
    for xyi in xy:
        if xyi[0] > maxxy[0] or xyi[1] >maxxy[1]:
            ind_bad.append(i)
        if xyi[0] < minxy[0] or xyi[1] < minxy[1]:
            ind_bad.append(i)
        i+=1
    ikle = [var for var in ikle if len(var) == len([i for i in var if i not in ind_bad])]
    #voronoi_plot_2d(vor) # figure to debug
    #plt.show()
    # find one sub data by triangle ?
    sub_dom2 = np.zeros(len(ikle),)
    sub_pg2 = np.zeros(len(ikle), )
    for e in range(0, len(ikle)):
        ikle_i = ikle[e]
        centerx = np.mean(xgrid[ikle_i])
        centery = np.mean(ygrid[ikle_i])
        nearest_ind = np.argmin(np.sqrt((x-centerx)**2 + (y-centery)**2))
        sub_dom2[e] = sub_dom[nearest_ind]
        sub_pg2[e] = sub_pg[nearest_ind]

    # transform code for text case
    if code_type == 'Cemagref':
        if min(sub_dom2) < 1 or min(sub_pg2) < 1:
            print('Error: The Cemagref code should be formed by an int between 1 and 8. (2)\n')
            return failload
        elif max(sub_dom2) > 8 or max(sub_pg2) > 8:
            print('Error: The Cemagref code should be formed by an int between 1 and 8. (3)\n')
            return failload
    # code type edf - checked and transform
    elif code_type == 'EDF':
        if min(sub_dom2) < 1 or min(sub_pg2) < 1:
            print('Error: The edf code should be formed by an int between 1 and 8. (2)\n')
            return failload
        elif max(sub_dom2) > 8 or max(sub_pg2) > 8:
            print('Error: The edf code should be formed by an int between 1 and 8. (3)\n')
            return failload
        else:
            sub_dom2 = edf_to_cemagref(sub_dom2)
            sub_pg2 = edf_to_cemagref(sub_pg2)
    # code type sandre
    elif code_type == 'Sandre':
        if min(sub_dom2) < 1 or min(sub_pg2) < 1:
            print('Error: The sandre code should be formed by an int between 1 and 12. (2)\n')
            return failload
        elif max(sub_dom2) > 12 or max(sub_pg2) > 12:
            print('Error: The sandre code should be formed by an int between 1 and 12. (3)\n')
            return failload
        else:
            sub_dom2 = sandre_to_cemagref(sub_dom2)
            sub_pg2 = sandre_to_cemagref(sub_pg2)
    else:
        print('Error: The substrate code is not recognized.\n')
        return failload

    return xy, ikle, sub_dom2, sub_pg2, x, y, sub_dom, sub_pg


def create_dummy_substrate_from_hydro(h5name, path, new_name, code_type, attribute_type, nb_point=200):
    """
    This function takes an hydrological hdf5 as inputs and create a shapefile of substrate and a text file of substrate
    which can be used as input for habby. The substrate data is random. So it is mainly useful to test an hydrological
    input.

    The created shape file is rectangular with a size based on min/max of the hydrological coordinates. The substrate
    grid is not the same as the hydrological grids (which is good to test the programm). In addition, one side of the shp
    is smaller than the hydrological grid to test the 'default substrate' option (which is used if the substrate
    shapefile is not big enough).

    :param h5name: the name of the hydrological hdf5 file
    :param path: the path to this file
    :param new_name: the name of the create shape file wihtout the shp (string)
    :param code_type: the code type for the substrate (sandre, cemagref or edf)
    :param attribute_type: if the substrate is given in the type coarser/dominant/..(0) or in percenctage (1)
    :param nb_point: the number of point needed (more points results in smaller substrate form)
    """

    # load hydro hdf5
    [ikle_all_t, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(h5name, path)

    # get min max of coord
    minx = 1e40
    maxx = -1e40
    miny = 1e40
    maxy = -1e40
    point_all = np.array(point_all[0])  # full profile
    for r in range(0, len(point_all)):
        maxx_here = max(point_all[r ,:, 0])
        minx_here = min(point_all[r ,:, 0])
        maxy_here = max(point_all[r ,:, 1])
        miny_here = min(point_all[r ,:, 1])
        if maxx_here > maxx:
            maxx = maxx_here
        if minx_here < minx:
            minx = minx_here
        if maxy_here > maxy:
            maxy = maxy_here
        if miny_here < miny:
            miny = miny_here

    # to test the default substrate
    miny *= 0.9

    # get random coordinate
    point_new = []
    for p in range(0, nb_point):
        x = randrange(int(minx), int(maxx))
        y = randrange(int(miny), int(maxy))
        point_new.append([x,y])

    # get a new substrate grid
    dict_point = dict(vertices=point_new)
    grid_sub = triangle.triangulate(dict_point)
    try:
        ikle_r = list(grid_sub['triangles'])
        point_all_r = list(grid_sub['vertices'])
    except KeyError:
        print('Warning: Reach with an empty grid.\n')
        return

    # gett random substrate data for shapefile
    data_sub = []
    data_sub_txt = []
    for i in range(0, len(ikle_r)):
        if attribute_type == 0:
            if code_type == 'EDF' or code_type == 'Cemagref':
                s1 = randrange(1, 8)
                s2 = randrange(1, 8)
            elif code_type == 'Sandre':
                s1 = randrange(1, 12)
                s2 = randrange(1, 12)
            else:
                print('code not recognized')
                return
            data_sub.append([s1, s2])  # coarser, dominant
            if i < len(point_new):
                data_sub_txt.append([s1, s2])
        elif attribute_type == 1:
            data_sub_here = []
            if code_type == 'EDF' or code_type == 'Cemagref':
                for j in range(0, 8):
                    sx = randrange(1, 100)
                    data_sub_here.append(sx)
            elif code_type == 'Sandre':
                for j in range(0, 12):
                    sx = randrange(1, 100)
                    data_sub_here.append(sx)
            else:
                print('code not recognized')
                return
            data_sub.append(data_sub_here)
        else:
            print('Error: the attribute type should 1 or 0')
            return

    # pass the substrate data to shapefile
    w = shapefile.Writer(shapefile.POLYGON)
    if attribute_type == 0:
        w.field('PG', 'F', 10, 8)
        w.field('DM', 'F', 10, 8)
    elif attribute_type == 1:
        if code_type == 'EDF' or code_type == 'Cemagref':
            for j in range(1, 9):  # we want to start with S1 to get the corresponding class
                w.field('S'+str(j), 'F', 10, 8)
        elif code_type == 'Sandre':
            for j in range(1, 13):
                w.field('S'+str(j), 'F', 10, 8)

    for i in range(0, len(ikle_r)):
        p1 = list(point_all_r[ikle_r[i][0]])
        p2 = list(point_all_r[ikle_r[i][1]])
        p3 = list(point_all_r[ikle_r[i][2]])
        w.poly(parts=[[p1, p2, p3, p1]])  # the double [[]] is important or it bugs, but why?
    for i in range(0, len(ikle_r)):
        if attribute_type == 0:
            w.record(data_sub[i][0], data_sub[i][1])  # data_sub[i] does not work
        elif attribute_type == 1:
            if code_type == 'EDF' or code_type == 'Cemagref':
                w.record(data_sub[i][0], data_sub[i][1], data_sub[i][2], data_sub[i][3],data_sub[i][4], data_sub[i][5],
                         data_sub[i][6], data_sub[i][7])
            elif code_type == 'Sandre':
                w.record(data_sub[i][0], data_sub[i][1],data_sub[i][2], data_sub[i][3],data_sub[i][4], data_sub[i][5],
                         data_sub[i][6], data_sub[i][7],data_sub[i][8], data_sub[i][9],data_sub[i][10], data_sub[i][11])
    w.autoBalance = 1
    w.save(os.path.join(path, new_name + '.shp'))

    # pass to text file
    if attribute_type == 0:
        data = np.hstack((np.array(point_new), np.array(data_sub_txt)))
        np.savetxt(os.path.join(path, new_name+'.txt'), data)


def merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, default_data, path_prj =''):
    """
    After the data for the substrate and the hydrological data are loaded, they are still in different grids.
    This functions will merge both grid together. This is done for all time step and all reaches. If a
    constant substrate is there, the hydrological hdf5 is just copied.

    !TO BE CORRECTED if there is more than one intersection on a substrate side!

    :param hdf5_name_hyd: the path and name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the path and the name of the hdf5 with the substrate data
    :param default_data: The substrate data given in the region of the hydrological grid where no substrate is given
    :param path_prj: the path to the project
    :return: the connectivity table, the coordinates, the substrated data, the velocity and height data all in a merge form.

    """
    failload = [-99], [-99], [-99], [-99], [-99]
    sub_dom_all_t = []
    sub_pg_all_t = []
    ikle_both = []
    point_all_both = []
    point_c_all_both = []
    vel_all_both = []
    height_all_both = []

    try:
        default_data= float(default_data)
    except ValueError:
        print('Error: Dafault data should be a float.\n')
        return failload

    m = time.time()
    # load hdf5 hydro
    [ikle_all, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(hdf5_name_hyd, path_prj)

    # load hdf5 sub
    [ikle_sub, point_all_sub, data_sub_pg, data_sub_dom] = load_hdf5.load_hdf5_sub(hdf5_name_sub, path_prj)
    # find the additional crossing points for each time step and each reach
    # and modify the grid

    # simple test case to debug( two triangle separated by an horizontal line)
    # point_all = [[np.array([[0.5, 0.55], [0.3, 0.55], [0.5, 0.3], [0.3, 0.3]])]]
    # ikle_all = [[np.array([[0, 1, 3], [0, 2, 3]])]]
    # ikle_sub = np.array([[0, 1, 2]])
    # point_all_sub = np.array([[0.4, 0.45], [0.48, 0.45], [0.32, 0.35], [1, 1]])

    if len(ikle_all) == 1 and ikle_all[0][0][0][0] == [-99]:
        print('Error: hydrological data could not be loaded.')
        return failload
    elif len(ikle_sub) == 1 and ikle_sub[0][0] == -99:
        print('Error: Substrate data could not be loaded.')
        return failload
    elif ikle_sub == [] or ikle_all == []:
        print('Error: No connectivity table found.\n')
        return failload
    elif len(point_all_sub) == 1 and ikle_sub[0][0] == 0:
        # if constant substrate, the hydrological grid is used
        # the default value is not really used
        print('Warning: Constant substrate.')
        for t in range(0, len(ikle_all)):
            sub_data_all_pg = []
            sub_data_all_dom = []
            if len(ikle_all[t]) > 0:
                for r in range(0, len(ikle_all[t])):
                    try:
                        sub_data_pg = np.zeros(len(ikle_all[t][r]),) + float(data_sub_dom)
                        sub_data_dom = np.zeros(len(ikle_all[t][r]),) + float(data_sub_pg)
                    except ValueError:
                        print('Error: no int in substrate. (only float or int accepted for now). \n')
                        return failload
                    sub_data_all_pg.append(sub_data_dom)
                    sub_data_all_dom.append(sub_data_pg)
            sub_dom_all_t.append(sub_data_dom)
            sub_pg_all_t.append(sub_data_all_pg)
        sub_dom_all_t = sub_dom_all_t
        sub_pg_all_t = sub_pg_all_t
        return ikle_all, point_all, sub_dom_all_t, sub_pg_all_t, inter_vel_all, inter_height_all
    elif len(ikle_sub[0]) < 3:
        print('Error: the connectivity table of the substrate is badly formed.')
        return failload

    for t in range(0, len(ikle_all)):
        ikle_all2 = []
        point_all2 = []
        data_sub2_pg = []
        data_sub2_dom = []
        vel2 = []
        height2 = []

        if len(ikle_all[t]) > 0:
            for r in range(0, len(ikle_all[t])):
                point_before = np.array(point_all[t][r])
                ikle_before = np.array(ikle_all[t][r])
                if t > 0:
                    vel_before = inter_vel_all[t][r]
                    height_before = inter_height_all[t][r]
                else:
                    vel_before = []
                    height_before = []
                a = time.time()
                if len(ikle_before) < 1:
                    print('Warning: One time steps without grids found. \n')
                    break
                [pc, new_data_sub_pg, new_data_sub_dom] = point_cross2(ikle_before, point_before, ikle_sub,
                                                                       point_all_sub, data_sub_pg, data_sub_dom, default_data)
                pc = np.array(pc)

                if len(pc) < 1:
                    print('Warning: No intersection between the grid and the substrate for one reach.\n')
                    try:
                        sub_data_here = np.zeros(len(ikle_all[t][r]), ) + float(default_data)  # check if ok for float
                    except ValueError:
                        print('Error: no float in substrate. (only float accepted fro now)')
                        return failload
                    sub_dom_all_t.append(sub_data_here)
                    sub_pg_all_t.append(sub_data_here)
                    ikle_all2.append(ikle_before)
                    point_all2.append(point_before)
                    break # next time step

                b = time.time()
                [ikle_here, point_all_here, new_data_sub_pg, new_data_sub_dom, vel_new, height_new] = \
                    grid_update_sub3(ikle_before, point_before, pc, point_all_sub, new_data_sub_pg, new_data_sub_dom,
                                     vel_before, height_before)
                c = time.time()
                ikle_all2.append(ikle_here)
                point_all2.append(point_all_here)
                data_sub2_pg.append(new_data_sub_pg)
                data_sub2_dom.append(new_data_sub_dom)
                vel2.append(vel_new)
                height2.append(height_new)

        ikle_both.append(ikle_all2)
        point_all_both.append(point_all2)
        sub_pg_all_t.append(data_sub2_pg)
        sub_dom_all_t.append(data_sub2_dom)
        vel_all_both.append(vel2)
        height_all_both.append(height2)

    return ikle_both, point_all_both, sub_pg_all_t, sub_dom_all_t, vel_all_both, height_all_both


def point_cross2(ikle, coord_p, ikle_sub, coord_p_sub, data_sub_pg, data_sub_dom, default_sub):
    """
    A function which find where the crossing points are. Crossing points are the points on the triangular side of the
    hydrological grid which cross with a side of the substrate grid. The algo based on finding if points of one elements
    are in the same polygon using a ray casting method

    :param ikle: the connectivity table for the hydrological data
    :param coord_p: the coordinates of the points of the hydrological grid
    :param ikle_sub: the connecity vity table of the substrate
    :param coord_p_sub: the coordinates of the points of the substrate grid
    :param data_sub_pg: the data of the coaser  substrate in cemargef code(one data by cell)
    :param data_sub_dom: the data of the  dominant substratein cemargef code(one data by cell)
    :param default_sub: the default_data
    :return: intersection

    """
    pc = []
    new_data_sub_pg = []  # the data sub for the hydrology
    new_data_sub_dom = []
    xsubmax = max(coord_p_sub[:, 0])
    ysubmax = max(coord_p_sub[:, 1])
    xsubmin = min(coord_p_sub[:, 0])
    ysubmin = min(coord_p_sub[:, 1])

    # erase substrate cell which are outside of the hydrological grid (to optimize)
    data_sub_pg2 = []
    data_sub_dom2 = []
    ikle_sub2 =[]
    xhydmax = max(coord_p[:, 0])
    yhydmax = max(coord_p[:, 1])
    xhydmin = min(coord_p[:, 0])
    yhydmin = min(coord_p[:, 1])
    i = 0
    for k in ikle_sub:
        coord_x_sub = np.array([coord_p_sub[int(k[0]), 0], coord_p_sub[int(k[1]), 0], coord_p_sub[int(k[2]), 0]])
        coord_y_sub = np.array([coord_p_sub[int(k[0]), 1], coord_p_sub[int(k[1]), 1], coord_p_sub[int(k[2]), 1]])
        if xhydmax >= min(coord_x_sub) and xhydmin <= max(coord_x_sub) and \
                        yhydmax >= min(coord_y_sub) and yhydmin <= max(coord_y_sub):
            ikle_sub2.append(k)
            data_sub_pg2.append(data_sub_pg[i])
            data_sub_dom2.append(data_sub_dom[i])
        i+=1
    ikle_sub = np.array(ikle_sub2)
    if len(ikle_sub) < 1:
        return [], new_data_sub_pg, new_data_sub_dom
    data_sub_pg = data_sub_pg2
    data_sub_dom = data_sub_dom2
    nb_poly = len(ikle_sub)
    nb_tri = len(ikle)

    p0 = coord_p[int(ikle[0, 0])]
    nx = ny = 0  # direction of the substrate grid

    # for each triangle in the hydro mesh
    for e in range(0, nb_tri):
        sub_num = [-99, -99, -99]  # where are the polygon
        # for each points in this triangle
        for p in range(0, 3):
            [xhyd, yhyd] = coord_p[int(ikle[e, p]), :]
            find_sub = False
            # let's analyse each polygon of the substrate grid
            i = 0
            # if cross is not possible anyway
            #if xsubmax < xhyd or xhyd < xsubmin or ysubmax < yhyd or yhyd < ysubmin:
                #find_sub = True
            # think about polygon size for optimization
            while not find_sub:
                # using to send a ray outside of the polygon
                # idea from http://geomalgorithms.com/a03-_inclusion.html
                # the number of time a particular point intersect with a segments
                intersect = 0.0
                # find the "substrate" point of this polygon
                poly_i = ikle_sub[i]
                idem_x = False
                # for each side of the substrate polygon
                for i2 in range(0, len(poly_i)):
                    if i2 == len(poly_i)-1:
                        [x1sub, y1sub] = coord_p_sub[int(poly_i[i2])]
                        [x2sub, y2sub] = coord_p_sub[int(poly_i[0])]
                    else:
                        [x1sub, y1sub] = coord_p_sub[int(poly_i[i2])]
                        [x2sub, y2sub] = coord_p_sub[int(poly_i[i2+1])]
                    # send ray is along the x direction, positif y = const
                    # check if it is possible to have an interesection using <>
                    if xhyd <= max(x1sub, x2sub) and min(y1sub, y2sub) <= yhyd <= max(y1sub, y2sub):
                        # find the possible intersection
                        if x1sub != x2sub:
                            # case where the side of the triangle is on the "wrong side"
                            # of xhyd even if xhyd <= max(x1sub,x2sub)
                            if y1sub != y2sub:
                                a = (y1sub - y2sub) / (x1sub - x2sub)
                                x_int = (yhyd - y1sub)/a + x1sub  # (yhyd - (y1sub - x1sub *a)) / a
                            else:
                                x_int = xhyd+1000  # crossing if horizontal
                        else:
                            x_int = xhyd  # x1sub

                        # if we have interesection
                        if xhyd <= x_int:
                            intersect += 1

                        # manage the case where the yhyd is at the same height than subtrate (we want one intersection
                        # and not two)
                        if yhyd == y1sub or yhyd == y2sub:
                            if idem_x:
                                intersect -= 1
                                idem_x = False
                            else:
                                idem_x = True

                            # seg = seg.append(i2)
                # if number of intersection is odd, then point inside
                if intersect % 2 == 1:
                    find_sub = True
                    sub_num[p] = i

                # in case there is point outside of any substrat polygon
                if i == nb_poly-1 and not find_sub:
                    # have a look in divers/test_code_sub.text
                    find_sub = True
                    sub_num[p] = -1

                # get to the next polygon
                i += 1
        # if there is an intersection, find the intersection and the info concerning it
        # the intersection(s) will be done when reconstructing the grid
        # what if theremore than one intersection for 2 points? ( managed now, I guess)
        # colinear case als

        if sub_num[0] != sub_num[1] and sub_num[0] != -99 and sub_num[1] != -99:
            hyd1 = coord_p[int(ikle[e, 0]), :]
            hyd2 = coord_p[int(ikle[e, 1]), :]
            # choosing 0 or 1 does not matter as long as we are not outside of the subtrate
            if sub_num[0] != -1:
                a1 = ikle_sub[sub_num[0]]
            else:
                a1 = ikle_sub[sub_num[1]]
            # find the side with an intersection
            for seg in range(0, len(a1)):  # We coud use while to not test all intersection
                if seg < len(a1) - 1:
                    sub1 = coord_p_sub[int(a1[seg])]
                    sub2 = coord_p_sub[int(a1[seg+1])]
                else:
                    sub1 = coord_p_sub[int(a1[seg])]
                    sub2 = coord_p_sub[int(a1[0])]
                norm = np.sqrt((sub2[0] - sub1[0]) ** 2 + (sub1[1] - sub2[1]) ** 2)
                nx = (sub2[0] - sub1[0]) / norm
                ny = (sub2[1] - sub1[1]) / norm
                p_cross = intersec_cross(hyd1, hyd2, sub1, sub2, e, nx, ny)
                # p_cross = [e, xcross,ycross,nx,ny, subx, suby,subx,suby]
                if p_cross[1] is not None:
                    p_cross.extend([sub1[0], sub1[1], sub2[0], sub2[1]])
                    pc.append(p_cross)

        if sub_num[1] != sub_num[2] and sub_num[1] != -99 and sub_num[2] != -99:
            hyd1 = coord_p[int(ikle[e, 1]), :]
            hyd2 = coord_p[int(ikle[e, 2]), :]
            if sub_num[2] != -1:
                a1 = ikle_sub[sub_num[2]]
            else:
                a1 = ikle_sub[sub_num[1]]
            # find the side with an intersection
            for seg in range(0, len(a1)):
                if seg < len(a1) - 1:
                    sub1 = coord_p_sub[int(a1[seg])]
                    sub2 = coord_p_sub[int(a1[seg+1])]
                else:
                    sub1 = coord_p_sub[int(a1[seg])]
                    sub2 = coord_p_sub[int(a1[0])]
                norm = np.sqrt((sub2[0] - sub1[0]) ** 2 + (sub1[1] - sub2[1]) ** 2)
                nx = (sub2[0] - sub1[0]) / norm
                ny = (sub2[1] - sub1[1]) / norm
                p_cross = intersec_cross(hyd1, hyd2, sub1, sub2, e, nx, ny)
                if p_cross[1] is not None:
                    p_cross.extend([sub1[0], sub1[1], sub2[0], sub2[1]])
                    pc.append(p_cross)

            # # # pc.append(hyd1)

        if sub_num[2] != sub_num[0] and sub_num[0] != -99 and sub_num[2] != -99:
            hyd1 = coord_p[int(ikle[e, 2]), :]
            hyd2 = coord_p[int(ikle[e, 0]), :]
            if sub_num[2] != -1:
                a1 = ikle_sub[sub_num[2]]
            else:
                a1 = ikle_sub[sub_num[0]]
            # find the side with an intersection
            for seg in range(0, len(a1)):
                if seg < len(a1) - 1:
                    sub1 = coord_p_sub[int(a1[seg])]
                    sub2 = coord_p_sub[int(a1[seg+1])]
                else:
                    sub1 = coord_p_sub[int(a1[seg])]
                    sub2 = coord_p_sub[int(a1[0])]
                norm = np.sqrt((sub2[0] - sub1[0]) ** 2 + (sub1[1] - sub2[1]) ** 2)
                nx = (sub2[0] - sub1[0]) / norm
                ny = (sub2[1] - sub1[1]) / norm
                p_cross = intersec_cross(hyd1, hyd2, sub1, sub2, e, nx,ny)
                if p_cross[1] is not None:
                    p_cross.extend([sub1[0], sub1[1], sub2[0], sub2[1]])
                    pc.append(p_cross)

            # # pc.append(hyd1)

        # prepare the substrate data
        # three value for each cells (one by triangle)
        # if one hydrological triangle in one substrate cell (simple case),
        # we gives three times the same data
        data_sub_1_cell_pg = []
        data_sub_1_cell_dom = []
        for mi in range(0, len(sub_num)):
            if sub_num[mi] == -1 or sub_num[mi] == -99:
                data_sub_1_cell_pg.append(default_sub)
                data_sub_1_cell_dom.append(default_sub)
            else:
                data_sub_1_cell_pg.append(data_sub_pg[sub_num[mi]])
                data_sub_1_cell_dom.append(data_sub_dom[sub_num[mi]])
        new_data_sub_pg.append(data_sub_1_cell_pg)
        new_data_sub_dom.append(data_sub_1_cell_dom)

    return pc, new_data_sub_pg, new_data_sub_dom


def point_cross_bis(ikle, coord_p, ikle_sub, coord_p_sub):
    """
        A function which find where the crossing points are. Crossing pitn are the points on the triangular side of the
        hydrological grid which cross with a side of the substrate grid. Easier than point_cross 2 but slow. \
        So it is not used.

        :param ikle: the connectivity table for the hydrological data
        :param coord_p: the coordinates of the points of the hydrological grid
        :param ikle_sub: the connecity vity table of the substrate
        :param coord_p_sub: the coordinates of the points of the substrate grid
        :return: intersection
    """
    nb_tri = len(ikle[:, 0])
    nb_poly = len(ikle_sub)
    pc = []

    nx = ny = 0  # direction of the substrate grid

    # for each triangle in the hydro mesh
    for e in range(0, nb_tri):
        at = ikle[e]
        p0 = coord_p[at[0]]#coord_p[ikle[e,0]]
        p1 = coord_p[at[1]]#coord_p[ikle[e,1]]
        p2 = coord_p[at[2]]#coord_p[ikle[e,2]]
        for pe in range(0,3):
            # for each element in the substrate
            if pe ==0:
                pa = p0
                pb = p1
            elif pe == 1:
                pa = p1
                pb = p2
            elif pe == 2:
                pa = p2
                pb = p0
            for s in range(0, len(ikle_sub)):
                for sp in range(0,len(ikle_sub[s])):
                    if sp < len(ikle_sub[s])-1:
                        ps1 = coord_p_sub[int(ikle_sub[s, sp])]
                        ps2 = coord_p_sub[int(ikle_sub[s, sp+1])]
                    else:
                        ps1 = coord_p_sub[int(ikle_sub[s, sp])]
                        ps2 = coord_p_sub[int(ikle_sub[s, 0])]
                    if min(pa[0], pb[0]) <= max(ps1[0], ps2[0]) and min(pa[1], pb[1]) <= max(ps1[1],ps2[1]):
                        [inter, pl] = manage_grid_8.intersection_seg(pa, pb, ps1, ps2, False)
                        if inter:
                            norm = np.sqrt((ps2[0] - ps1[0]) ** 2 + (ps1[1] - ps2[1]) ** 2)
                            nx = (ps2[0] - ps1[0]) / norm
                            ny = (ps2[1] - ps1[1]) / norm
                            pc_here = [e, pl[0][0], pl[0][1], nx, ny]
                            pc.append(pc_here)
    return pc


def intersec_cross(hyd1, hyd2, sub1, sub2, e=-99, nx=[], ny=[]):
    """
    A function function to calculate the intersection, segment are not parrallel,
    used in case where we know that the intersection exists
    Also save various info with the intersection (element, direction, etc.)

    :param hyd1: the first hydrological point
    :param hyd2: the second
    :param sub1: the first substrate point
    :param sub2: the second
    :param e: the element of the hydrological grid (optional)
    :param nx: the direction of the cutting part of the substrate grid (x dir)
    :param ny: the direction of the cutting part of the substrate grid (y dir)
    :return: intersection and the direction of cutting part.
    """

    sub1 = np.array(sub1)
    sub2 = np.array(sub2)
    wig = 0

    [sx,sy] = [hyd2[0] - hyd1[0], hyd2[1] - hyd1[1]]
    [rx,ry] = [sub2[0] - sub1[0], sub2[1] - sub1[1]]
    rxs = rx * sy - ry* sx
    term2 = (hyd1[0] - sub1[0]) * ry - rx * (hyd1[1]- sub1[1])
    xcross = None
    ycross = None

    if rxs ==0 and term2 ==0:
        print('collinear points, error')
        return [-99, -99, -99, -99, -99]
    if rxs != 0 :
        u = term2 / rxs
        t = ((hyd1[0] - sub1[0]) * sy - sx * (hyd1[1] - sub1[1])) / rxs
        if 0.0 -wig <=t<= 1.0+wig and 0.0 -wig <=u<= 1.0+wig:
            xcross = hyd1[0] + u * sx
            ycross = hyd1[1] + u * sy
    if e >= 0:
        return [e,xcross,ycross, nx, ny]
    else:
        return [xcross, ycross]


def grid_update_sub3(ikle, coord_p, point_crossing, coord_sub, new_data_sub_pg, new_data_sub_dom, vel, height):
    """
    A function to update the grid after finding the crossing points and finsihed to get the substrate_data.
    We still needs to get the substrate data correclty for complicated geometry

    :param ikle:  the hydrological grid to be merge with the substrate grid
    :param coord_p: the coordinate of the point of the hydrological grid
    :param point_crossing: the crossing point, with the elemtn of the hydrological grid linked with it and the
           direction (nx,ny) of the substrate line at this point
    :param coord_sub: the coordinate of the substrate, only useful to if the the substrate cut two time the samie of a
            cell of the hydrological grid
    :param new_data_sub_pg: the coarser substrate data by hydrological cell (3 information by cells realted to
           the three points)
    :param new_data_sub_dom: the dominant substrate data by hydrological cell (3 information by cells realted to
           the three points)
    :param vel: the velocity (one time step, one reach) for each point in coord_p
    :param height: the water height (one time step, one reach) for each point in coord_p
    :return: the new grid

    ** Technical comments**

    This function corrects all element of the grids where a crossing point have been found by the function point_cross2()

    First, we find on which side of the triangle is the crossing points.

    Next there are three cases: a) one one crossing point -> no change b) two crossing points -> done manually c)
    more than two crossing point on the elements -> We call the extrenal module triangle to re-do a small triagulation
    into the element. This last cases covers many possible case, but it is slow. To optimize, we can think about writing
    more individual cases.

    In the trianlge case, we do not have a good management of the substrate data yet. All new elements into in the
    old elements which do not touch one of the orginal trianlgular node are the given the first substrate data type.

    If a substrate cells is totally in the hydrological cells, it is considerated too small to be accounted for and
    it is neglected by the present function. It can be changed but it will be really slower as it would mean looping
    over all element (or to get a list of not found element in the function above).

    """

    # prep
    x1 = x2 = x3 = 0
    y1 = y2 = y3 = 0
    vel = list(vel)
    height= list(height)

    # ordered the intersections
    point_crossing = point_crossing[point_crossing[:, 0].argsort()]

    # get all touched element (no duplicate)
    te = list(set(point_crossing[:, 0]))
    # for all these element
    to_delete = []
    for e in te:
        # get the crossing pionts touched by these elements
        ind1 = np.searchsorted(point_crossing[:,0], e)
        ind2 = np.searchsorted(point_crossing[:,0], e, side='right')
        if ind1 == ind2 - 1:
            ind_all = [ind1]
        else:
            ind_all = range(ind1, ind2)

        # check on which triangle we are
        pc_here = []  # the list of point_crossing for this elements, max one by side
        which_side = []  # the side of each pc_here (based on ikle order)

        for ie in ind_all:  # even in only one ind_all, we need to know on which side it is
            xcross = point_crossing[ie, 1]
            ycross = point_crossing[ie, 2]
            for s in range(0, 3):
                seg_found= False
                [x1, y1] = coord_p[int(ikle[int(e), s]), :]
                if s < 2:
                    [x2, y2] = coord_p[int(ikle[int(e), s + 1]), :]
                    if s == 0:  # so ikle[e,1]
                        x3 = np.copy(x2)
                        y3 = np.copy(y2)
                else:
                    [x2, y2] = coord_p[int(ikle[int(e), 0]), :]

                # get on which side of the triangle is the intersection
                if x1 != x2:
                    a = (y1 - y2) / (x1 - x2)
                else:
                    a = 0
                b = y1 - a * x1
                ytest = a * xcross + b
                if abs(ytest - ycross) < ycross / 10000:  # if true, interesection (with a bit of unprecision)
                    seg_found = True
                if seg_found:
                    # check if we do not have an identical point before
                    # looks for an easier way
                    if len(pc_here) > 0:
                        pc_new = np.array([point_crossing[ie, 1], point_crossing[ie, 2]])
                        pc_here_arr = np.array(pc_here)
                        sum_reach = np.sum(abs(pc_here_arr[:,1:3] - pc_new), axis=1)
                    else:
                        sum_reach = np.array([1, 1])
                    # check if the substrate is parrallel to the triangle
                    parr = False
                    crossvec = point_crossing[ie, 3]*(y2-y1) - point_crossing[ie, 4]*(x2-x1)
                    if crossvec < 10**-10:
                        parr = True
                    if (sum_reach > 10**-10).all():
                        # add the point
                        pc_here.append(point_crossing[ie, :])
                        which_side.append(s)

        # for each pc of the element e, let's create new triangles
        e = int(e) # used as index here

        # will delete the old element at the end(ikle and substrate)
        to_delete.append(e)

        # check if we have substrate point in pc_here
        # do not account for substrate cell totally in the hydrological cell
        point_in = []
        seg_poly = []
        seg_poly.append([coord_p[ikle[e, 0]], coord_p[ikle[e, 1]]])
        seg_poly.append([coord_p[ikle[e, 1]], coord_p[ikle[e, 2]]])
        seg_poly.append([coord_p[ikle[e, 2]], coord_p[ikle[e, 0]]])
        for pi in pc_here:
            sub1 = [pi[5], pi[6]]
            sub2 = [pi[7], pi[8]]
            inside1 = manage_grid_8.inside_polygon(seg_poly, sub1)
            inside2 = manage_grid_8.inside_polygon(seg_poly, sub2)
            if inside1:
                point_in.append(sub1)
            if inside2:
                point_in.append(sub2)

        # get the substrate direction (important if the substrate only cross)
        if len(pc_here) == 2:
            nx1 = np.abs(pc_here[0][3])
            nx2 = np.abs(pc_here[1][3])
            ny1 = np.abs(pc_here[0][4])
            ny2 = np.abs(pc_here[1][4])

        # if we have one crossing point, let's ignore it as the gris is already ok
        if len(pc_here) == 1 or len(pc_here) == 0:
            pass

        # if simple crossing do it 'by hand"(i.e. witbout the triangle module)
        # this is the case used most often so it must be quick
        # calling triangle is slow, so we used it only for rare case
        # analyze if other case should be handled separately
        # nx1== nx2 check for point_in
        elif len(pc_here) == 2 and which_side[0] != which_side[1] and nx1 == nx2 and ny1 == ny2:
            # new intersection point
            pc1 = [pc_here[0][1], pc_here[0][2]]
            pc2 = [pc_here[1][1], pc_here[1][2]]
            coord_p = np.vstack((coord_p, pc2))  # order matters
            coord_p = np.vstack((coord_p, pc1))
            # get the new height and velocity data
            if len(vel) > 0: # not used by t=0, for the grid representing the whole profile
                point_old = [coord_p[ikle[e, 0]], coord_p[ikle[e, 1]], coord_p[ikle[e, 2]]]
                vel_here = [vel[ikle[e, 0]], vel[ikle[e, 1]], vel[ikle[e, 2]]]
                h_here = [height[ikle[e, 0]], height[ikle[e, 1]], height[ikle[e, 2]]]
                vel_new1 = get_new_vel_height_data(pc1, point_old, vel_here)
                vel_new2 = get_new_vel_height_data(pc2, point_old, vel_here)
                vel.append(vel_new1)
                vel.append(vel_new2)
                h_new1 = get_new_vel_height_data(pc1, point_old, h_here)
                h_new2 = get_new_vel_height_data(pc2, point_old, h_here)
                height.append(h_new1)
                height.append(h_new2)
            # update ikle
            # seg1 = [0,1] and seg2 = [1,2] in ikle order
            if sum(which_side) == 1:
                ikle = np.vstack((ikle, [len(coord_p)-1, len(coord_p)-2, ikle[e, 1]]))
                new_data_sub_pg.append(new_data_sub_pg[e][1])
                new_data_sub_dom.append(new_data_sub_dom[e][1])
                if which_side[1] == 1:  # seg = [1, 2]
                    ikle = np.vstack((ikle, [len(coord_p)-1, len(coord_p)-2, ikle[e, 0]]))
                    new_data_sub_pg.append(new_data_sub_pg[e][0])
                    new_data_sub_dom.append(new_data_sub_dom[e][0])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 2], ikle[e, 0]]))
                    # new_data_sub[e][0] and new_data_sub[e][2] should be identical
                    new_data_sub_dom.append(new_data_sub_dom[e][0])
                    new_data_sub_pg.append(new_data_sub_pg[e][0])
                else:
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 2]]))
                    new_data_sub_dom.append(new_data_sub_dom[e][2])
                    new_data_sub_pg.append(new_data_sub_pg[e][2])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 2], ikle[e, 0]]))
                    new_data_sub_dom.append(new_data_sub_dom[e][2])
                    new_data_sub_pg.append(new_data_sub_pg[e][2])
                # seg1 = [0,1] and seg2 = [0,2]
            if sum(which_side) == 2:
                ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 0]]))
                new_data_sub_dom.append(new_data_sub_dom[e][0])
                new_data_sub_pg.append(new_data_sub_pg[e][0])
                if which_side[1] == 0:  # seg = [1, 0]
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 2]]))
                    new_data_sub_pg.append(new_data_sub_pg[e][2])
                    new_data_sub_dom.append(new_data_sub_dom[e][2])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 2]]))
                    # new_data_sub[e][1] and new_data_sub[e][2] should be identical
                    new_data_sub_pg.append(new_data_sub_pg[e][2])
                    new_data_sub_dom.append(new_data_sub_dom[e][2])
                else:
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 1]]))
                    new_data_sub_pg.append(new_data_sub_pg[e][1])
                    new_data_sub_dom.append(new_data_sub_dom[e][1])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 2]]))
                    new_data_sub_pg.append(new_data_sub_pg[e][1])
                    new_data_sub_dom.append(new_data_sub_dom[e][1])
            # seg1 = [2,1] and seg2 = [0,2]
            if sum(which_side) == 3:
                ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 2]]))
                new_data_sub_pg.append(new_data_sub_pg[e][2])
                new_data_sub_dom.append(new_data_sub_dom[e][2])
                if which_side[1] == 2:  # seg = [2, 0]
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 1]]))
                    new_data_sub_pg.append(new_data_sub_pg[e][1])
                    new_data_sub_dom.append(new_data_sub_dom[e][1])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 0]]))
                    new_data_sub_pg.append(new_data_sub_pg[e][1])
                    new_data_sub_dom.append(new_data_sub_dom[e][1])
                else:
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 0]]))
                    new_data_sub_dom.append(new_data_sub_dom[e][0])
                    new_data_sub_pg.append(new_data_sub_pg[e][0])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 0]]))
                    new_data_sub_dom.append(new_data_sub_dom[e][0])
                    new_data_sub_pg.append(new_data_sub_pg[e][0])
        else:

            # all other cases
            # make a new trianglulation inside the trianlge
            # get hole
            # hole is outside of the triangle
            cex = 1 / 3 * (x1 + x2 + x3)
            cey = 1 / 3 * (y1 + y2 + y3)
            holex = x1 - (cex - x1)
            holey = y1 - (cey - y1)
            hole = [holex, holey]
            # get segments forming the triangle
            seg = []
            seg.append([0, 1])
            seg.append([1, 2])
            seg.append([2, 0])
            # get the three triangluar point and pc_point
            point_new = []
            for p in range(0, 3):
                point_new.append(coord_p[ikle[e, p]])
            # get the segment indicating the direction of the substrate
            m0 = 10  # do not go too high here and neither too small afterward
            cross = True
            inter = False
            for s1 in range(0, len(pc_here)):
                m = m0
                while cross and m > 10**-10:
                    cross = False
                    m = m/2
                    p1x = pc_here[s1][1] + m * pc_here[s1][3]  # pc + m*nx
                    p1y = pc_here[s1][2] + m * pc_here[s1][4]
                    p1 = [p1x, p1y]
                    p2x = pc_here[s1][1] - m * pc_here[s1][3]
                    p2y = pc_here[s1][2] - m * pc_here[s1][4]
                    p2 = [p2x, p2y]
                    # find if p1 or p2 is in the triangle (just use the polygon function because lazy)
                    inside = manage_grid_8.inside_polygon(seg_poly, p1)
                    if not inside:
                        inside = manage_grid_8.inside_polygon(seg_poly, p2)
                        if inside:
                            p1 = p2
                    if inside:
                        pc = [pc_here[s1][1], pc_here[s1][2]]
                        # check that we have no crossing if we are sill far
                        # if we are very close we want to get the easier possible path because it is complicated
                        # enough
                        if m > m0/16:
                            for s2 in range(s1+1, len(pc_here)):
                                p3x = pc_here[s2][1] + m0 * pc_here[s2][3]  # m0 is the highest possible m multiplied by two
                                p3y = pc_here[s2][2] + m0 * pc_here[s2][4]
                                p3 = [p3x, p3y]
                                p4x = pc_here[s2][1] - m0 * pc_here[s2][3]
                                p4y = pc_here[s2][2] - m0 * pc_here[s2][4]
                                p4 = [p4x, p4y]
                                [inter, blob] = manage_grid_8.intersection_seg(pc, p1, p3, p4, False)
                                if inter:
                                    cross = True
                    else:
                        cross = True
                pc = [pc_here[s1][1], pc_here[s1][2]]
                point_new.append(p1)
                point_new.append(pc)
                # add point in the substrate
                if len(point_in) > 1:
                    for pii in point_in:
                        point_new.append(pii)
                seg.append([s1*2 + 3, s1*2 + 4])
                if cross:
                    print('Warning: Complicated geometry for the substrate layer.\n')
                    # also debug
                    # for pi in range(0, len(pc_here)):
                    #     plt.plot(pc_here[pi][1], pc_here[pi][2], '*g')
                    # for pi in range(0, 3):
                    #     plt.plot(coord_p[ikle[e, pi]][0], coord_p[ikle[e, pi]][1], '^r')
                    # plt.plot(p1[0], p1[1], '^b')
                    # plt.plot(p2[0], p2[1], '^b')
                    # plt.show()

            #triangulation
            point_new = np.array(point_new)
            seg = np.array(seg)
            #sorted_data = point_new[np.lexsort(point_new.T), :]
            #row_mask = np.append([True], np.any(np.diff(sorted_data, axis=0), 1))
            #test_unique = sorted_data[row_mask]
            #if len(test_unique) != len(point_new):
               # print('Warning: There is duplicate points in the sub-grid.\n')
            dict_point = dict(vertices=point_new, segments=seg, holes=hole)
            grid_dict = triangle.triangulate(dict_point)
            ikle_new = grid_dict['triangles']
            point_new = grid_dict['vertices']
            ikle = np.vstack((ikle, np.array(ikle_new) + len(coord_p)))
            coord_p = np.vstack((coord_p, point_new))
            # add substrate data
            for i in ikle_new:
                found_new = False
                # if one of the origanl data is in, we know the substrate
                for hydi in range(0,3):
                    phere = coord_p[ikle[e][hydi]]
                    ind = np.argmin(abs(phere[0] - point_new[:, 0]) + abs(phere[1]-point_new[:, 1]))
                    if ind in ikle_new:
                        found_new = True
                        new_data_sub_pg.append(new_data_sub_pg[e][hydi])
                        new_data_sub_dom.append(new_data_sub_dom[e][hydi])
                if not found_new:
                    # !!!!! TO BE CORRECTED!!!!!!
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    new_data_sub_dom.append(new_data_sub_dom[e][0])
                    new_data_sub_pg.append(new_data_sub_pg[e][0])
            # add new velcoity and height data
            if len(vel) > 0:
                point_old = [coord_p[ikle[e, 0]], coord_p[ikle[e, 1]], coord_p[ikle[e, 2]]]
                vel_here = [vel[ikle[e, 0]], vel[ikle[e, 1]], vel[ikle[e, 2]]]
                for i in point_new:
                        h_here = [height[ikle[e, 0]], height[ikle[e, 1]], height[ikle[e, 2]]]
                        vel_new1 = get_new_vel_height_data(i, point_old, vel_here)
                        vel.append(vel_new1)
                        h_new1 = get_new_vel_height_data(i, point_old, h_here)
                        height.append(h_new1)

            # figure (to debug)
            # if len(pc_here) > 2:
            #     xlist = []
            #     ylist = []
            #     fig = plt.figure()
            #     if len(ikle_new) > 1:
            #         col_ikle = len(ikle_new[0])
            #         for i in range(0, len(ikle_new)):
            #             pi = 0
            #             while pi < col_ikle - 1:  # we have all sort of xells, max eight sides
            #                 p = int(ikle_new[i, pi])  # we start at 0 in python, careful about -1 or not
            #                 p2 = int(ikle_new[i, pi + 1])
            #                 xlist.extend([point_new[p, 0], point_new[p2, 0]])
            #                 xlist.append(None)
            #                 ylist.extend([point_new[p, 1], point_new[p2, 1]])
            #                 ylist.append(None)
            #                 pi += 1
            #             p = int(ikle_new[i, pi])
            #             p2 = int(ikle_new[i, 0])
            #             xlist.extend([point_new[p, 0], point_new[p2, 0]])
            #             xlist.append(None)
            #             ylist.extend([point_new[p, 1], point_new[p2, 1]])
            #             ylist.append(None)
            #     plt.plot(xlist, ylist, linewidth=0.1)
            #     for pi in range(0, len(pc_here)):
            #         plt.plot(pc_here[pi][1], pc_here[pi][2], '*g')
            #     for pi in range(0, 3):
            #         plt.plot(coord_p[ikle[e, pi]][0], coord_p[ikle[e, pi]][1], '^r')
            #     c = ['--m', '--b', '--g', '--y', '--r', '--k']
            #     for s in range(3, len(seg)):
            #         plt.plot([point_new[seg[s][0]][0], point_new[seg[s][1]][0]],[point_new[seg[s][0]][1], point_new[seg[s][1]][1]], c[s])
            #     plt.show()

    # remove element from ikle and new_data_sub
    ikle = [i for j, i in enumerate(ikle) if j not in to_delete]
    new_data_sub_pg = [i for j, i in enumerate(new_data_sub_pg) if j not in to_delete]
    new_data_sub_dom = [i for j, i in enumerate(new_data_sub_dom) if j not in to_delete]


    # check and take out column
    si = 0
    for s in new_data_sub_pg:
        s2 = new_data_sub_dom[si]
        if isinstance(s, float) or isinstance(s, int) or isinstance(s, np.integer):
            s = [s]
        if len(s) > 1:
            if s[0] == s[1] and s[2] == s[1] and s2[0] == s2[1] and s2[1] == s2[2]:
                pass
            else:
                print('Warning: Substrate data is not consistent')
                print(new_data_sub_pg[si])
                print(new_data_sub_dom[si])
            new_data_sub_pg[si] = s[0]
            new_data_sub_dom[si] = s2[0]
            si += 1

    return ikle, coord_p, new_data_sub_pg, new_data_sub_dom, vel, height


def get_new_vel_height_data(newp, point_old, data_old):
    """
    This function gets the height and velcoity data for a new point in or on the side of an element. It does an
    average of the data (velocity or height) given at the node of the original (old) elements. This average is weighted
    as a function of the distance of the point.

    :param newp: the coordinates of the new points
    :param point_old: the coordinates of thre three old points (would work with more than three)
    :param data_old: the data for the point in point_old
    :return: the new data
    """
    point_old = np.array(point_old)
    d_all = np.sqrt((point_old[:,0] - newp[0])**2 + (point_old[:,1]-newp[1])**2)
    data_new = 0
    for i in range(0, len(point_old)):
        data_new += d_all[i] * data_old[i]
    sum_d_all = np.sum(d_all)
    data_new = data_new/sum_d_all
    return data_new


def grid_update_sub2(ikle, coord_p, point_crossing, coord_sub):
    """
    A function to find the updated grid with the substrate. More complicated than grid_update3 because it tries to makes
    new cell based on the lines linkes the centroid and the side of the trianlge. Looks more elegant at first but
    quite complicated and do not work for all cases. So it is not used.

    :param ikle:  the hydrological grid to be merge with the substrate grid
    :param coord_p: the coordinate of the point of the hydrological grid
    :param point_crossing: the crossing point, with the elemtn of the hydrological grid linked with it and the
           direction (nx,ny) of the substrate line at this point
    :param coord_sub: the coordinate of the substrate, only useful to if the the substrate cut two time the samie of a
           cell of the hydrological grid
    :return: the new grid
    """

    # prep
    x1 = x2 = x3 = 0
    y1 = y2 = y3 = 0
    double_test = False  # allow for having two intersection on the same side

    # ordered the intersections
    point_crossing = point_crossing[point_crossing[:, 0].argsort()]

    # get all touched element (no duplicate)
    te = list(set(point_crossing[:,0]))

    # for all these element
    for e in te:
        # get the crossing pionts touched by these elements
        ind1 = np.searchsorted(point_crossing[:,0], e)
        ind2 = np.searchsorted(point_crossing[:,0], e, side='right')
        if ind1 == ind2 - 1:
            ind_all = [ind1]
        else:
            ind_all = range(ind1, ind2)

        # check on which triangle we are
        pc_here = []  # the list of point_crossing for this elements, max one by side
        which_side = [] # the side of each pc_here (based on ikle order)
        double_side = []

        for ie in ind_all:  # even in oly one ind_all, we need to know on which side it is
            xcross = point_crossing[ie, 1]
            ycross = point_crossing[ie, 2]
            for s in range(0, 3):
                seg_found= False
                [x1, y1] = coord_p[int(ikle[int(e), s]), :]
                if s < 2:
                    [x2, y2] = coord_p[int(ikle[int(e), s + 1]), :]
                    if s == 0:  # so ikle[e,1]
                        x3 = np.copy(x2)
                        y3 = np.copy(y2)
                else:
                    [x2, y2] = coord_p[int(ikle[int(e), 0]), :]
                # find if the three points are on the same ligne
                if x1 != x2:
                    a = (y1 - y2) / (x1 - x2)
                else:
                    a = 0
                b = y1 - a * x1
                ytest = a * xcross + b
                if abs(ytest - ycross) < ycross / 100000:  # if true, interesection (with a bit of unprecision)
                    seg_found = True
                if seg_found:
                    if s not in which_side:
                        pc_here.append(point_crossing[ie, :])
                        which_side.append(s)
                    else:
                        # case where there is two intersection on the double side
                        # sometime not used to simplify
                        if double_test:
                            if s not in double_side:
                                double_side.append(s)
                                which_side_arr = np.array(which_side)
                                ind_old_pc = np.where(which_side_arr == s)[0]
                                pc_old = [pc_here[ind_old_pc][1], pc_here[ind_old_pc][2]]
                                sub_point = coord_sub[point_crossing[ie, 5]]
                                # if the point is double, we just add a small triangle to correct for this
                                pc_d = [point_crossing[ie,1], point_crossing[ie,2]]
                                coord_p = np.vstack((coord_p, pc_old))
                                coord_p = np.vstack((coord_p, sub_point))
                                coord_p = np.vstack((coord_p,  pc_d))
                                ikle = np.vstack((ikle, [len(coord_p)-1, len(coord_p)-2, len(coord_p)-3]))
                            else:
                                print('Warning: a substrate side cut more than two time on one hydrological cells.'
                                      ' Case not supported \n')

        # get the centroid
        # calling point[ikle] is slow
        # s==2 -> x1 = 2, x2 = 0, x3 = 1
        cex = 1/3 * (x1 + x2 + x3)
        cey = 1/3 * (y1 + y2 + y3)
        ce = [cex, cey]

        pl_all = []
        pl_fin = []
        to_delete = []
        # for each pc of the element e, let's create new triangle
        for ind in range(0, len(pc_here)):

            # create aline in the segment line direction
            pc = [pc_here[ind][1], pc_here[ind][2]]
            pc1x = pc[0] - pc_here[ind][3] * 10**5
            pc1y = pc[1] - pc_here[ind][4] * 10**5
            pc1 = [pc1x, pc1y]
            pc = [pc_here[ind][1], pc_here[ind][2]]
            pc2x = pc[0] + pc_here[ind][3] * 10**5
            pc2y = pc[1] + pc_here[ind][4] * 10**5
            pc2 = [pc2x, pc2y]
            inter_all = 0

            # get 3 lines from the centroid to the side of triangle and looks which lines is crossed by the line
            # defined by the point_corssing and the (nx,ny) related to this point
            # if there are two intersectins, pick the closest intersection
            which_li = 0  # for each point_crossing, note with which line it intersects
            for li in range(0, 3):
                sub2 = coord_p[int(ikle[int(e), li]), :]
                [inter, pl] = manage_grid_8.intersection_seg(pc1, pc2, ce, sub2, True)
                if inter:
                    pl_all.append(pl[0])
                    inter_all += 1
            if inter_all == 1:
                pl_fin = pl_all[0]   # all ok
                which_li = li
            elif inter_all == 0:
                print('Warning: Grid could not be modified by the substrate layer for one element \n')
                pl_fin = [0,0]
            # if we have more than one intersection, take the cloest one
            elif inter_all > 1:
                dmin = 10**12
                for i in range(0, inter_all):
                    d = np.sqrt((pc[0] - pl_all[i][0])**2 + (pc[1] - pl_all[i][1])**2)
                    if d < dmin:
                        dmin = d
                        pl_fin = pl_all[i]
                        which_li = li

            # add all point to coord_p (oder matters)
            coord_p = np.vstack((coord_p, pc))
            coord_p = np.vstack((coord_p, pl_fin))
            coord_p = np.vstack((coord_p, ce))
            # note element to be erased
            if ind == 0:
                to_delete.append(e)
            if ind > 1:
                to_delete.append(len(ikle)- which_side[ind] -1)

            # add five new triangle to ikle
            ce_ind = len(coord_p) - 1
            pc2_ind = len(coord_p) -2
            pc_ind = len(coord_p) - 3
            e = int(e)
            if which_side[ind] == 0:
                ikle = np.vstack((ikle, [ce_ind, ikle[e, 2], ikle[e, 1]]))
                ikle = np.vstack((ikle, [ce_ind, ikle[e, 2], ikle[e, 0]]))
                ikle = np.vstack((ikle, [pc_ind, pc2_ind, ikle[e, 1]]))
                ikle = np.vstack((ikle, [pc_ind, pc2_ind, ikle[e, 0]]))
                if which_li == 0:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 0]]))
                if which_li == 1:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 1]]))
                if which_li == 2: # should not happens
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 1]]))
            if which_side[ind] == 1:
                ikle = np.vstack((ikle, [ce_ind, ikle[e, 0], ikle[e, 1]]))
                ikle = np.vstack((ikle, [ce_ind, ikle[e, 0], ikle[e, 2]]))
                ikle = np.vstack((ikle, [pc_ind, pc2_ind, ikle[e, 1]]))
                ikle = np.vstack((ikle, [pc_ind, pc2_ind, ikle[e, 2]]))
                if which_li == 0:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 0]]))
                if which_li == 1:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 1]]))
                if which_li == 2:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 2]]))
            if which_side[ind] == 2:
                ikle = np.vstack((ikle, [ce_ind, ikle[e, 1], ikle[e, 0]]))
                ikle = np.vstack((ikle, [ce_ind, ikle[e, 1], ikle[e, 2]]))
                ikle = np.vstack((ikle, [pc_ind, pc2_ind, ikle[e, 0]]))
                ikle = np.vstack((ikle, [pc_ind, pc2_ind, ikle[e, 2]]))
                if which_li == 0:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 0]]))
                if which_li == 1:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 1]]))
                if which_li == 2:
                    ikle = np.vstack((ikle, [ce_ind, pc2_ind, ikle[e, 2]]))

    # remove elemnt from ikle
    ikle = [i for j, i in enumerate(ikle) if j not in to_delete]

    return ikle, coord_p


def fig_substrate(coord_p, ikle, sub_pg, sub_dom, path_im, xtxt = [-99], ytxt= [-99], subtxt= [-99]):
    """
    The function to plot the substrate data, which was loaded before. This function will only work if the substrate
    data is given using the cemagref code.

    :param coord_p: the coordinate of the point
    :param ikle: the connectivity table
    :param sub_pg: the information on subtrate by element for the "coarser part"
    :param sub_dom: the information on subtrate by element for the "dominant part"
    :param xtxt: if the data was given in txt form, the orignal x data
    :param ytxt: if the data was given in txt form, the orignal y data
    :param subtxt: if the data was given in txt form, the orignal sub data
    :param path_im: the path where to save the figure\
    """
    # pass sub_info to float
    # TO BE DONE!!!!

    plt.rcParams['font.size'] = 10

    sub_dom = np.array(sub_dom)
    sub_pg = np.array(sub_pg)
    if len(sub_dom) == 0 or len(sub_pg) == 0:
        print('no data found to plot.')
        return

    # prepare grid
    xlist = []
    ylist = []
    coord_p = np.array(coord_p)
    for i in range(0, len(ikle)):
        pi = 0
        while pi < len(ikle[i])-1:  # we have all sort of xells, max eight sides
            p = int(ikle[i][pi])  # we start at 0 in python, careful about -1 or not
            p2 = int(ikle[i][pi+1])
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = int(ikle[i][pi])
        p2 = int(ikle[i][0])
        xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
        xlist.append(None)
        ylist.extend([coord_p[p,1], coord_p[p2, 1]])
        ylist.append(None)

    # substrate coarser
    fig, ax = plt.subplots(1)
    patches = []
    cmap = plt.get_cmap('gist_rainbow')
    colors = cmap((sub_pg - np.min(sub_pg)) / (
    np.max(sub_pg) - np.min(sub_pg)))  # convert nfloors to colors that we can use later
    n = len(sub_pg)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    collection = PatchCollection(patches)
    ax.add_collection(collection)
    collection.set_color(colors)
    ax.autoscale_view()
    # cbar = plt.colorbar()
    # cbar.ax.set_ylabel('Substrate')
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Substrate Grid - Coarser Data')
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure

    # colorbar
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    norm = mpl.colors.Normalize(vmin=1, vmax=8)
    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap,
                                    norm=norm,
                                    orientation='vertical')
    cb1.set_label('Code Cemagrfef')
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'), dpi=1000)
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'), dpi=1000)

    # substrate dominant
    fig, ax = plt.subplots(1)
    patches = []
    cmap = plt.get_cmap('gist_rainbow')
    colors = cmap((sub_dom - np.min(sub_dom)) / (
        np.max(sub_dom) - np.min(sub_dom)))  # convert nfloors to colors that we can use later
    n = len(sub_dom)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    collection = PatchCollection(patches)
    ax.add_collection(collection)
    collection.set_color(colors)
    ax.autoscale_view()
    # cbar = plt.colorbar()
    # cbar.ax.set_ylabel('Substrate')
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Substrate Grid - Dominant')

    # colorbar
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7]) # posistion x2, sizex2, 1= top of the figure
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    norm = mpl.colors.Normalize(vmin=1, vmax=8)
    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap,
                                    norm=norm,
                                    orientation='vertical')
    cb1.set_label('Code Cemagrfef')

    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'), dpi=1000)
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'), dpi=1000)

    # if we start with txt data, plot the original data
    if xtxt != [-99]:
        plt.figure()
        subtxt = list(map(float, subtxt))
        # size of the marker (to avoid having to pale, unclear figure)
        # this is a rough estimation, no need for precise number here
        d1 = 0.5 * np.sqrt((xtxt[1] - xtxt[0])**2 + (ytxt[1] - xtxt[1])**2)  # dist in coordinate
        dist_data = np.mean([np.max(xtxt) - np.min(xtxt), np.max(ytxt) - np.min(ytxt)])
        f_len = 5 * 72  # point is 1/72 inch, figure is 5 inch large
        transf = f_len/dist_data
        s1 = 3.1 * (d1* transf)**2 / 2  # markersize is given as an area

        cm = plt.cm.get_cmap('gist_rainbow')
        sc = plt.scatter(xtxt, ytxt, c=subtxt, vmin=np.nanmin(subtxt), vmax=np.nanmax(subtxt), s=34, cmap=cm, edgecolors='none')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Original Substrate Data (x,y)')
        plt.savefig(os.path.join(path_im, "substrate_txtdata" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'), dpi=1000)
        plt.savefig(os.path.join(path_im, "substrate_txtdata" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'), dpi=1000)
        #plt.show()
        #plt.close()

    #plt.show()


def fig_merge_grid(point_all_both_t, ikle_both_t, path_im, ikle_orr=[], point_all_orr=[]):
    """
    A function to plot the grid after it was merged with the substrate data.
    It plots one time step at the time.

    :param point_all_both_t: the coordinate of the points of the updated grid
    :param ikle_both_t: the connectivity table
    :param path_im: the path where the image should be saved
    :param ikle_orr: the orginial ikle
    :param point_all_orr: the orginal point_all
    """
    if not os.path.isdir(path_im):
        print('Error: No directory found to save the figures \n')
        return

    # prepare grid
    xlist = []
    ylist = []
    fig = plt.figure()
    for r in range(0, len(ikle_both_t)):
        ikle = np.array(ikle_both_t[r])
        if len(ikle) > 1:
            coord_p = point_all_both_t[r]
            col_ikle = len(ikle[0])
            for i in range(0, len(ikle)):
                pi = 0
                while pi < col_ikle - 1:  # we have all sort of xells, max eight sides
                    p = int(ikle[i, pi])  # we start at 0 in python, careful about -1 or not
                    p2 = int(ikle[i, pi + 1])
                    xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
                    xlist.append(None)
                    ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
                    ylist.append(None)
                    pi += 1

                p = int(ikle[i, pi])
                p2 = int(ikle[i, 0])
                xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
                xlist.append(None)
                ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
                ylist.append(None)
        plt.plot(xlist, ylist, linewidth=0.1)
        #plt.plot(coord_p[:, 0], coord_p[:, 1], '*r')
    # for test, remove otherwise
    # point_all_sub = np.array([[0.4, 0.45], [0.48, 0.45], [0.32, 0.35]])
    # plt.plot(point_all_sub[:, 0], point_all_sub[:, 1], '*r')
    plt.title('Computational grid, updated for substrate data')
    plt.xlabel('x coordinate')
    plt.ylabel('y coordinate')
    #plt.show()
    plt.savefig(os.path.join(path_im, "Grid_merge_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"), dpi=1000)
    plt.savefig(os.path.join(path_im, "Grid_merge_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"), dpi=1000)


def main():
    """
    Used to test this module.
    """

    path = r'D:\Diane_work\output_hydro\substrate'


    # test create shape
    #filename = 'mytest.shp'
    #filetxt = 'sub_txt2.txt'
    # # load shp file
    # [coord_p, ikle_sub, sub_info] = load_sub_shp(filename, path, 'VELOCITY')
    # fig_substrate(coord_p, ikle_sub, sub_info, path)
    # # load txt file
    #[coord_pt, ikle_subt, sub_infot,  x, y, sub] = load_sub_txt(filetxt, path,)
    #fig_substrate(coord_pt, ikle_subt, sub_infot, path, x, y, sub)


    # test merge grid
    # path1 = r'D:\Diane_work\dummy_folder\DefaultProj'
    # hdf5_name_hyd = os.path.join(path1, r'Hydro_HECRAS1D_CRITCREK13_02_2017_at_17_10_03.h5' )
    # hdf5_name_sub = os.path.join(path1, r'Substrate_mytest_shp_13_02_2017_at_16_54_54.h5')
    # [ikle_both, point_all_both, sub_data, vel, height] = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub,0)
    # fig_merge_grid(point_all_both[0], ikle_both[0], path1)
    # plt.show()

    # test create dummy substrate
    path = r'D:\Diane_work\dummy_folder\DefaultProj'
    fileh5 = 'Hydro_RUBAR2D_BS15a607_02_2017_at_15_50_13.h5'
    create_dummy_substrate_from_hydro(fileh5, path, 'dummy_hydro_substrate2', 'Sandre', 0)


if __name__ == '__main__':
    main()