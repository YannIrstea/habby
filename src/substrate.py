import shapefile
import os
import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
from random import uniform
#import matplotlib.tri as tri
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import time
import triangle
from random import randrange
from src import load_hdf5
from src_GUI import output_fig_GUI


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
        record_all = []
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
        record_all = np.array(record_all).T
        # get the domainant and coarser from the percentage
        [sub_dom, sub_pg] = percentage_to_domcoarse(record_all, dominant_case)
        if len(sub_dom) == 1:
            if sub_dom[0] == -99:
                return  [-99], [-99], [-99], [-99], False
        # transform to cemagref substrate form
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
                a = int('2')
                record_here = sf.records()
                record_here = np.array(record_here)
                record_here = record_here[:, ind-1]
                try:
                    record_here = list(map(float, record_here))  # int('2.000' ) throw an error
                    record_here = list(map(int, record_here))
                except ValueError:
                   print('Error: The substrate code should be formed by an int.\n')
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
                if f[0] == attribute_name[1]:
                    sub_dom = record_here
            ind += 1

    else:
        print('Error: Type of attribute not recognized.\n')
        return failload

    # having a convex subtrate grid is really practical
    [ikle, xy, sub_pg, sub_dom] = modify_grid_if_concave(ikle, xy, sub_pg, sub_dom)

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
            new_record.append(2)
        elif r == 2:
            new_record.append(3)
        elif r == 3:
            new_record.append(4)
        elif r == 4:
            new_record.append(5)
        elif r == 5:
            new_record.append(6)
        elif r == 6:
            if one_give_one:
                new_record.append(6)
                one_give_one = False
            else:
                new_record.append(7)
                one_give_one = True
            #new_record.append(6)
        elif r == 7:
            new_record.append(7)
        elif r == 8:  # slabs? -> check this
            new_record.append(8)

    return new_record


def edf_to_cemagref_by_percentage(records):
    """
    This function change the subtrate in a percetage form from edf code to cemagref code
    :param records: the subtrate data (in 8x len tabular)
    :return:
    """
    new_record = []
    for r in records:
        r2 = [0, 0, 0, 0, 0, 0, 0, 0]
        r2[0] = 0
        r2[1] = r[0]
        r2[2] = r[1]
        r2[3] = r[2]
        r2[4] = r[3]
        r2[5] = r[4] + r[5] * 0.5
        r2[6] = r[6] + r[5] * 0.5
        r2[7] = r[7]
        new_record.append(r2)

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


def percentage_to_domcoarse(sub_data, dominant_case):
    """
    This function is used to pass from percentage data to dominant/coarse. As the code 8 from the subtrate in
    Cemagref code is slab, we do not the 8 code as the coarser substrate.

    :param sub_data: the subtrate data in percentage from Lammi
    :param dominant_case: an int to manage the case where the transfomation form percentage to dominnat is unclear (two
           maxinimum percentage are equal from one element). if -1 take the smallest, if 1 take the biggest,
           if 0, we do not know.
    :return:
    """
    sub_data = np.array(sub_data)

    len_sub = len(sub_data)
    sub_dom = [0] * len_sub
    sub_pg = [0] * len_sub

    for e in range(0, len_sub):
        record_all_i = sub_data[e]
        if sum(record_all_i) != 100:
            print('Warning: Substrate data is given in percentage. However, it does not sum to 100% \n')
        # let find the dominant
        # we cannot use argmax as we need all maximum value, not only the first
        inds = list(np.argwhere(record_all_i == np.max(record_all_i)).flatten())
        if len(inds) > 1:
            # if we have the same percentage for two dominant we send back the function to the GUI to ask the
            # user. It is called again with the arg dominant_case
            if dominant_case == 0:
                print('Warning: no dominant case')
                return [-99], [-99]
            elif dominant_case == 1:
                sub_dom[e] = inds[-1] + 1
            elif dominant_case == -1:
                # sub_dom[e] = int(attribute_name_all[inds[0]][0][1])
                sub_dom[e] = inds[0] + 1
        else:
            sub_dom[e] = inds[0] + 1
        # let find the coarser (the last one not equal to zero)
        ind = np.where(record_all_i[record_all_i != 0])[0]
        if len(ind) > 1:
            sub_pg[e] = ind[-1] + 1
        elif ind:  #just a float
            sub_pg[e] = ind + 1
        else: # no zeros
            sub_pg[e] = len(record_all_i)
        # cas des dalles
        if sub_pg[e] == 8:
            sub_pg[e] = sub_dom[e]

    return sub_dom, sub_pg


def load_sub_txt(filename, path, code_type):
    """
    A function to load the substrate in form of a text file. The text file must have 4 columns x,y coordinate and
    coarser substrate type, dominant substrate type, no header or title. It is transform to a grid using a voronoi
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


def modify_grid_if_concave(ikle, point_all, sub_pg, sub_dom):
    """
    This function check if the grid in entry is composed of convex cell. Indeed, it is possible to have concave
    cells in the substrate grid. However, this is unpractical when the hydrological grid is merged with the subtrate
    grid. Hence, we find here the concave cells. These cells are then modified using the triangle module.

    The algotithm is based on the idea that when you have a convex polygon you turn always in the same direction.
    When you have a concave polygon sometime you will turn left, sometime you will turn right. To check this,
    we can take the determinant betwen each vector which compose the cells and check if they have the same sign.
    Triangle are always convex.

    :param ikle: the connectivity table of the grid (one reach, one time step as substrate grid is constant)
    :param point_all: the point of the grid
    :param sub_pg: the coarser substrate, one data by cell
    :param sub_dom: the dominant subtrate, one data by cell
    :return: ikle, point_all with only convexe cells
    """

    point_alla = np.array(point_all)

    to_delete = []
    for ic, c in enumerate(ikle):
        concave = False
        lenc = len(c)
        sign_old = 0
        if lenc > 3: # triangle are convex
            v00 = point_alla[c[1]] - point_alla[c[0]]
            v0 = v00
            for ind in range(0, lenc):
                # find vector
                if ind < lenc - 2:
                    v1 = point_alla[c[ind+2]] - point_alla[c[ind+1]]
                elif ind == lenc - 2:
                    v1 = point_alla[c[0]] - point_alla[c[ind+1]]
                elif ind == lenc -1:
                    v1 = v00
                # calulate deteminant (x0y1 - x1y0)
                det = v0[0]*v1[1] - v1[0] * v0[1]
                # check sign
                if ind == 0:
                    sign_old = np.sign(det)
                else:
                    sign = np.sign(det)
                    if sign != sign_old:
                        concave = True
                    break
                v0 = v1

        # if concave, correct the substrate grid
        if concave:
            to_delete.append(ic)
            # create triangle intput
            point_cell = np.zeros((lenc, 2))
            seg_cell = np.zeros((lenc, 2))
            for ind in range(0, lenc):
                point_cell[ind] = point_all[c[ind]]
                if ind < lenc-1:
                    seg_cell[ind] = [ind, ind+1]
                else:
                    seg_cell[ind] = [ind, 0]
            # triangulate
            try:
                dict_point = dict(vertices=point_cell, segments=seg_cell)
                grid_dict = triangle.triangulate(dict_point, 'p')
            except:
                # to be done: create a second threat so that the error management will function
                print('Triangulation failed')
                return

            try:
                ikle_new = grid_dict['triangles']
                point_new = grid_dict['vertices']
                # add this triagulation to the ikle
                ikle.extend(list(np.array(ikle_new) + len(point_all)))
                point_all.extend(point_new)
                for m in range(0, len(ikle_new)):
                    sub_pg.append(sub_pg[ic])
                    sub_dom.append(sub_dom[ic])
            except KeyError:
                # in case triangulation was not ok
                print('Warning: A concave element of the substrate grid could not be corrected \n')

    # remove element
    if len(to_delete)>0:
        for d in reversed(to_delete):  # to_delete is ordered
            del ikle[d]
        sub_pg = np.delete(sub_pg, to_delete)
        sub_dom = np.delete(sub_dom, to_delete)

    return ikle, point_all, sub_pg, sub_dom


def create_dummy_substrate_from_hydro(h5name, path, new_name, code_type, attribute_type, nb_point=200, path_out='.'):
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
    :param code_type: the code type for the substrate (Sandre, Cemagref, Const_cemagref, or EDF). All subtrate value
           to 4 for Const_cemagref.
    :param attribute_type: if the substrate is given in the type coarser/dominant/..(0) or in percenctage (1)
    :param nb_point: the number of point needed (more points results in smaller substrate form)
    :param path_out: the path where to save the new substrate shape
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
        maxx_here = max(point_all[r][:, 0])
        minx_here = min(point_all[r][:, 0])
        maxy_here = max(point_all[r][:, 1])
        miny_here = min(point_all[r][:, 1])
        if maxx_here > maxx:
            maxx = maxx_here
        if minx_here < minx:
            minx = minx_here
        if maxy_here > maxy:
            maxy = maxy_here
        if miny_here < miny:
            miny = miny_here

    # to test the case where substrate shp does not cover the whole reach
    # miny *= 0.90

    # get random coordinate
    point_new = []
    for p in range(0, nb_point):
        x = uniform(minx, maxx)
        y = uniform(miny, maxy)
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
            elif code_type == 'Const_cemagref':
                s1 = 4
                s2 = 4
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
    w.save(os.path.join(path_out, new_name + '.shp'))

    # pass to text file
    if attribute_type == 0:
        data = np.hstack((np.array(point_new), np.array(data_sub_txt)))
        np.savetxt(os.path.join(path_out, new_name+'.txt'), data)


def fig_substrate(coord_p, ikle, sub_pg, sub_dom, path_im, fig_opt={}, xtxt = [-99], ytxt= [-99], subtxt= [-99]):
    """
    The function to plot the substrate data, which was loaded before. This function will only work if the substrate
    data is given using the cemagref code.

    :param coord_p: the coordinate of the point
    :param ikle: the connectivity table
    :param sub_pg: the information on subtrate by element for the "coarser part"
    :param sub_dom: the information on subtrate by element for the "dominant part"
    :param fig_opt: the figure option as a doctionnary
    :param xtxt: if the data was given in txt form, the orignal x data
    :param ytxt: if the data was given in txt form, the orignal y data
    :param subtxt: if the data was given in txt form, the orignal sub data
    :param path_im: the path where to save the figure\
    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']

    sub_dom = np.array(sub_dom)
    sub_pg = np.array(sub_pg)
    if len(sub_dom) == 0 or len(sub_pg) == 0:
        print('no data found to plot.')
        return

    # prepare grid (to optimize)
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
    cmap = plt.get_cmap(fig_opt['color_map1'])
    colors_val = np.array(sub_pg) # convert nfloors to colors that we can use later (cemagref)
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    norm = mpl.colors.Normalize(vmin=1, vmax=8)
    n = len(sub_pg)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True,edgecolor='w')
        patches.append(polygon)
    collection = PatchCollection(patches, linewidth=0.0, cmap=cmap, norm=norm)
    ax.add_collection(collection)
    #collection.set_color(colors)
    collection.set_array(colors_val)
    ax.autoscale_view()
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Substrate Grid - Coarser Data')
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure
    # colorbar

    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap,
                                    norm=norm,
                                    orientation='vertical')
    cb1.set_label('Code Cemagrfef')
    if format == 0 or format == 1:
        plt.savefig(os.path.join(path_im, "substrate_pg" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'), dpi=fig_opt['resolution'])
    if format == 0 or format == 3:
        plt.savefig(os.path.join(path_im, "substrate_pg" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'), dpi=fig_opt['resolution'])
    if format == 2:
        plt.savefig(os.path.join(path_im, "substrate_pg" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.jpg'), dpi=fig_opt['resolution'])

    # substrate dominant
    fig, ax = plt.subplots(1)
    patches = []
    cmap = plt.get_cmap(fig_opt['color_map2'])
    colors_val = np.array(sub_dom)  # convert nfloors to colors that we can use later
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    norm = mpl.colors.Normalize(vmin=1, vmax=8)
    n = len(sub_dom)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    collection = PatchCollection(patches,linewidth=0.0, cmap=cmap, norm=norm)
    ax.add_collection(collection)
    collection.set_array(colors_val)
    ax.autoscale_view()
    # cbar = plt.colorbar()
    # cbar.ax.set_ylabel('Substrate')
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Substrate Grid - Dominant')

    # colorbar
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7]) # posistion x2, sizex2, 1= top of the figure
    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap,
                                    norm=norm,
                                    orientation='vertical')
    cb1.set_label('Code Cemagrfef')

    # save the figure
    if format == 0 or format == 1:
        plt.savefig(os.path.join(path_im, "substrate_dom" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'), dpi=fig_opt['resolution'])
    if format == 0 or format == 3:
        plt.savefig(os.path.join(path_im, "substrate_dom" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'), dpi=fig_opt['resolution'])
    if format == 2:
        plt.savefig(os.path.join(path_im, "substrate_dom" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.jpg'), dpi=fig_opt['resolution'])

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
    path1 = r'D:\Diane_work\dummy_folder\DefaultProj'
    hdf5_name_hyd = os.path.join(path1, r'Hydro_RUBAR2D_BS15a607_02_2017_at_15_52_59.h5' )
    hdf5_name_sub = os.path.join(path1, r'Substrate_dummy_hyd_shp06_03_2017_at_11_27_59.h5')
    [ikle_both, point_all_both, sub_data1, subdata2,  vel, height] = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, -1)
    # fig_merge_grid(point_all_both[0], ikle_both[0], path1)
    # plt.show()

    # test create dummy substrate
    # path = r'D:\Diane_work\dummy_folder\DefaultProj'
    # fileh5 = 'Hydro_RUBAR2D_BS15a607_02_2017_at_15_50_13.h5'
    # create_dummy_substrate_from_hydro(fileh5, path, 'dummy_hydro_substrate2', 'Sandre', 0)


if __name__ == '__main__':
    main()