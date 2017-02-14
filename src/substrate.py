import shapefile
import os
import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
import matplotlib.tri as tri
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import time
from src import load_hdf5
from src import manage_grid_8
import triangle


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
        print('Warning: No attibute found in the shapefile given for the substrate.')

    return fields


def load_sub_shp(filename, path, name_att='SUBSTRATE'):
    """
    A function to load the substrate in form of shapefile.

    :param filename: the name of the shapefile
    :param path: the path where the shapefile is
    :param name_att: the name of the substrate column in the attribute table
    :return: grid in form of list of coordinate and connectivity table (two list)
            and an array with substrate type
    """
    # THINK ABOUT START AT ZERO OR ONE
    sf = open_shp(filename, path)

    # get point coordinates and connectivity table in two lists
    shapes = sf.shapes()
    xy = []
    ikle = []
    for i in range(0,len(shapes)):
        p_all = shapes[i].points
        ikle_i = np.zeros((len(p_all)-1, 1))
        for j in range(0, len(p_all)-1):  # last point of sahpefile is the first point
            try:
                ikle_i[j] = int(xy.index(p_all[j]))
            except ValueError:
                ikle_i[j] = int(len(xy))
                xy.append(p_all[j])
        ikle.append(ikle_i)

    # upload the substrate info
    fields = sf.fields
    ind = -99
    # find where the info is
    for i in range(0, len(fields)):
        field_i = fields[i]
        if field_i[0] == name_att:
            ind = i
    if ind == -99:
        print('Error: The substrate information is not found in the attribute table. Check attribute name.')
        return [-99], [-99], [-99]
    records = np.array(sf.records())
    sub = records[:, ind-1]
    # test if the substrate info are of substrate type

    return xy, ikle, sub


def load_sub_txt(filename, path):
    """
    A function to load the substrate in form of a text file. The text file must have 3 column x,y coordinate and
    substrate info, no header or title. It is transform to a grid using a voronoi transformation

    :param filename: the name of the shapefile
    :param path: the path where the shapefile is
    :return: grid in form of list of coordinate and connectivity table (two list)
             and an array with substrate type and (x,y,sub) of the orginal data
    """
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The txt file "+filename+" does not exist.")
        return [-99], [-99], [-99], [-99], [-99], [-99]
    # read
    with open(file, 'rt') as f:
        data = f.read()
    data = data.split()
    if len(data) % 3 != 0:
        print('Error: the number of column in ' + filename+ ' is not three. Check format.')
        return [-99], [-99], [-99], [-99], [-99], [-99]
    # get x,y (you might have alphanumeric data in the this colum)
    x = [data[i] for i in np.arange(0, len(data), 3)]
    y = [data[i] for i in np.arange(1, len(data), 3)]
    sub = [data[i] for i in np.arange(2, len(data), 3)]
    try:
        x = list(map(float,x))
        y = list(map(float,y))
    except TypeError:
        print("Error: Coordinates (x,y) could not be read as float. Check format of the file " + filename +'.')
        return [-99], [-99], [-99], [-99], [-99], [-99]
    # Voronoi
    point_in = np.array(np.reshape(np.array([x,y]), (len(x), 2)))
    vor = Voronoi(point_in)  # with the option further_site
    xy = vor.vertices
    xy = np.reshape(xy, (len(xy), len(xy[0])))
    xgrid = xy[:,0]
    ygrid = xy[:,1]
    ikle = vor.regions
    ikle = [var for var in ikle if var]  # erase empy element
    #voronoi_plot_2d(vor) # figure to debug
    #plt.show()
    # find one sub data by triangle ?
    sub_grid = np.zeros(len(ikle),)
    for e in range(0, len(ikle)):
        ikle_i = ikle[e]
        centerx = np.mean(xgrid[ikle_i])
        centery = np.mean(ygrid[ikle_i])
        nearest_ind = np.argmin(np.sqrt((x-centerx)**2 + (y-centery)**2))
        sub_grid[e] = sub[nearest_ind]

    return xy, ikle, sub_grid, x, y, sub


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
    sub_data_all_t = []
    ikle_both = []
    point_all_both = []
    vel_both = []
    height_both = []

    # here go check for default value
    # NOT DONE YET as form of the substrate data is not known

    m = time.time()
    # load hdf5 hydro
    [ikle_all, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(hdf5_name_hyd, path_prj)

    # load hdf5 sub
    [ikle_sub, point_all_sub, data_sub] = load_hdf5.load_hdf5_sub(hdf5_name_sub, path_prj)

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
    elif len(ikle_sub[0]) < 3:
        print('Error: the connectivity table of the substrate is badly formed.')
        return failload
    elif len(point_all_sub) == 1 and ikle_sub[0][0] == 0:
        # if constant substrate, the hydrological grid is used
        print('Warning: Constant substrate.')
        # not done yet
        sub_data = None
        return ikle_all, point_all, sub_data, inter_vel_all, inter_height_all

    for t in range(0, len(ikle_all)):
        ikle_all2 = []
        point_all2 = []
        data_sub2 = []

        if len(ikle_all[t]) > 0:
            for r in range(0, len(ikle_all[t])):
                point_before = np.array(point_all[t][r])
                ikle_before = np.array(ikle_all[t][r])
                a = time.time()
                [pc, new_data_sub] = point_cross2(ikle_before, point_before, ikle_sub, point_all_sub, data_sub, default_data)
                pc = np.array(pc)
                print(pc)

                if len(pc) < 1:
                    print('Warning: No intersection between the grid and the substrate.\n')
                    sub_data_p = [default_data]*len(point_before)
                    sub_data_all_t.append(sub_data_p)
                    ikle_all2.append(ikle_before)
                    point_all2.append(point_before)
                    break # next time step

                b = time.time()
                [ikle_here, point_all_here, new_data_sub] = grid_update_sub3(ikle_before, point_before, pc, point_all_sub, new_data_sub)
                c = time.time()
                ikle_all2.append(ikle_here)
                point_all2.append(point_all_here)
                data_sub2.append(new_data_sub)

        ikle_both.append(ikle_all2)
        point_all_both.append(point_all2)
        sub_data_all_t.append(data_sub2)

    return ikle_both, point_all_both, sub_data_all_t, vel_both, height_both


def point_cross2(ikle, coord_p, ikle_sub, coord_p_sub, data_sub, default_sub):
    """
    A function which find where the crossing points are. Crossing points are the points on the triangular side of the
    hydrological grid which cross with a side of the substrate grid. The algo based on finding if points of one elements
    are in the same polygon using a ray casting method

    :param ikle: the connectivity table for the hydrological data
    :param coord_p: the coordinates of the points of the hydrological grid
    :param ikle_sub: the connecity vity table of the substrate
    :param coord_p_sub: the coordinates of the points of the substrate grid
    :param data_sub: the data of the substrate (one data by cell)
    :param default_sub: the default_data
    :return: intersection

    """
    pc = []
    new_data_sub = []  # the data sub for the hydrology
    xsubmax = max(coord_p_sub[:, 0])
    ysubmax = max(coord_p_sub[:, 1])
    xsubmin = min(coord_p_sub[:, 0])
    ysubmin = min(coord_p_sub[:, 1])

    # erase substrate cell which are outside of the hydrological grid (to optimize)
    data_sub2 = []
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
            data_sub2.append(data_sub[i])
        i+=1
    ikle_sub = np.array(ikle_sub2)
    data_sub = data_sub2
    nb_poly = len(ikle_sub)
    nb_tri = len(ikle)

    p0 = coord_p[int(ikle[0, 0]), :]
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
            if xsubmax < xhyd or xhyd < xsubmin or ysubmax < yhyd or yhyd < ysubmin:
                find_sub = True
            # think about polygon size for optimization
            while not find_sub:
                # using to send a ray outside of the polygon
                # idea from http://geomalgorithms.com/a03-_inclusion.html
                # the number of time a particular point intersect with a segments
                intersect = 0.0
                # find the "substrate" point of this polygon
                poly_i = ikle_sub[i]
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
            a1 = ikle_sub[sub_num[0]]  # ????
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
                if p_cross[1] is not None:
                    pc.append(p_cross)

        if sub_num[1] != sub_num[2] and sub_num[1] != -99 and sub_num[2] != -99:
            hyd1 = coord_p[int(ikle[e, 1]), :]
            hyd2 = coord_p[int(ikle[e, 2]), :]
            a1 = ikle_sub[sub_num[2]]
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
                    pc.append(p_cross)
            # # # pc.append(hyd1)

        if sub_num[2] != sub_num[0] and sub_num[0] != -99 and sub_num[2] != -99:
            hyd1 = coord_p[int(ikle[e, 2]), :]
            hyd2 = coord_p[int(ikle[e, 0]), :]
            a1 = ikle_sub[sub_num[2]]
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
                    pc.append(p_cross)
            # # pc.append(hyd1)

        # give the substrate data
        # if one hydrological triangle in one substrate cell (sinple case),
        # we gives three times the same data
        data_sub_1_cell = []
        for mi in range(0,len(sub_num)):
            if sub_num[mi] == -1:
                data_sub_1_cell.append(default_sub)
            else:
                data_sub_1_cell.append(data_sub[sub_num[mi]])
        new_data_sub.append(data_sub_1_cell)

    return pc, new_data_sub


def point_cross_bis(ikle, coord_p, ikle_sub, coord_p_sub):
    """
        A function which find where the crossing points are. Crossing pitn are the points on the triangular side of the
        hydrological grid which cross with a side of the substrate grid. Easier than point_cross 2 but slow. it is used
        for the case where point are outside the substrate.

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
        if 0.0 <=t<= 1.0 and 0.0 <=u<= 1.0:
            xcross = hyd1[0] + u * sx
            ycross = hyd1[1] + u * sy
    if e >= 0:
        return [e,xcross,ycross, nx, ny]
    else:
        return [xcross, ycross]


def grid_update_sub3(ikle, coord_p, point_crossing, coord_sub, new_data_sub):
    """
    A function to update the grid after finding the crossing points and finsihed to get the substrate_data.
    We still needs to get the substrate data correclty for complicated geometry

    :param ikle:  the hydrological grid to be merge with the substrate grid
    :param coord_p: the coordinate of the point of the hydrological grid
    :param point_crossing: the crossing point, with the elemtn of the hydrological grid linked with it and the
           direction (nx,ny) of the substrate line at this point
    :param coord_sub: the coordinate of the substrate, only useful to if the the substrate cut two time the samie of a
            cell of the hydrological grid
    :param new_data_sub: the substrate data by hydrological cell (3 information by cells realted to the three poins)
    :return: the new grid
    """

    # prep
    x1 = x2 = x3 = 0
    y1 = y2 = y3 = 0

    # ordered the intersections
    point_crossing = point_crossing[point_crossing[:, 0].argsort()]

    # get all touched element (no duplicate)
    te = list(set(point_crossing[:, 0]))

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
        to_delete = []
        e = int(e)

        # will delete the old element (ikle and substrate)
        to_delete.append(e)

        # get the substrate direction
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
        elif len(pc_here) == 2 and which_side[0] != which_side[1] and nx1 == nx2 and ny1 == ny2:
            # new intersection point
            pc1 = [pc_here[0][1], pc_here[0][2]]
            pc2 = [pc_here[1][1], pc_here[1][2]]
            coord_p = np.vstack((coord_p, pc2))  # order matters
            coord_p = np.vstack((coord_p, pc1))
            # update ikle
            # seg1 = [0,1] and seg2 = [1,2] in ikle order
            if sum(which_side) == 1:
                ikle = np.vstack((ikle, [len(coord_p)-1, len(coord_p)-2, ikle[e, 1]]))
                new_data_sub.append(new_data_sub[e][1])
                if which_side[1] == 1:  # seg = [1, 2]
                    ikle = np.vstack((ikle, [len(coord_p)-1, len(coord_p)-2, ikle[e, 0]]))
                    new_data_sub.append(new_data_sub[e][0])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 2], ikle[e, 0]]))
                    # new_data_sub[e][0] and new_data_sub[e][2] should be identical
                    new_data_sub.append(new_data_sub[e][0])
                else:
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 2]]))
                    new_data_sub.append(new_data_sub[e][2])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 2], ikle[e, 0]]))
                    new_data_sub.append(new_data_sub[e][2])
                # seg1 = [0,1] and seg2 = [0,2]
            if sum(which_side) == 2:
                ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 0]]))
                new_data_sub.append(new_data_sub[e][0])
                if which_side[1] == 0:  # seg = [1, 0]
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 2]]))
                    new_data_sub.append(new_data_sub[e][2])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 2]]))
                    # new_data_sub[e][1] and new_data_sub[e][2] should be identical
                    new_data_sub.append(new_data_sub[e][2])
                else:
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 1]]))
                    new_data_sub.append(new_data_sub[e][1])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 2]]))
                    new_data_sub.append(new_data_sub[e][1])
            # seg1 = [2,1] and seg2 = [0,2]
            if sum(which_side) == 3:
                ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 2]]))
                new_data_sub.append(new_data_sub[e][2])
                if which_side[1] == 2:  # seg = [2, 0]
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 1]]))
                    new_data_sub.append(new_data_sub[e][1])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 0]]))
                    new_data_sub.append(new_data_sub[e][1])
                else:
                    ikle = np.vstack((ikle, [len(coord_p) - 1, len(coord_p) - 2, ikle[e, 0]]))
                    new_data_sub.append(new_data_sub[e][0])
                    ikle = np.vstack((ikle, [len(coord_p) - 2, ikle[e, 1], ikle[e, 0]]))
                    new_data_sub.append(new_data_sub[e][0])
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
            seg_poly = []
            seg_poly.append([coord_p[ikle[e, 0]], coord_p[ikle[e, 1]]])
            seg_poly.append([coord_p[ikle[e, 1]], coord_p[ikle[e, 2]]])
            seg_poly.append([coord_p[ikle[e, 2]], coord_p[ikle[e, 0]]])
            # get the three triangluar point and pc_point
            point_new = []
            for p in range(0,3):
                point_new.append(coord_p[ikle[e, p]])
            #for p in range(0, len(pc_here)):
              #  point_new.append([pc_here[p][1],pc_here[p][2]])
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
                    #print(seg_poly)
                    #print(pc_here[s1][1])
                    #print(pc_here[s1][2])
                    # find if p1 or p2 is in the triangle (just use the polygon function because lazy)
                    inside = manage_grid_8.inside_polygon(seg_poly, p1)
                    if not inside:
                        inside = manage_grid_8.inside_polygon(seg_poly, p2)
                        if inside:
                            p1 = p2
                    if inside:
                        pc = [pc_here[s1][1], pc_here[s1][2]]
                        # check that we have no crossing
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
                seg.append([s1*2 + 3, s1*2 + 4])
                if cross:
                    print('Warning: Complicated geometry for the substrate layer.\n')
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
                        new_data_sub.append(new_data_sub[e][hydi])
                        break
                if not found_new:
                    # !!!!! TO BE CORRECTED!!!!!!
                    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    new_data_sub.append(new_data_sub[e][0])
            #figure (to debug)
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
    new_data_sub = [i for j, i in enumerate(new_data_sub) if j not in to_delete]

    # check and take out column
    si = 0
    for s in new_data_sub:
        if isinstance(s, float) or isinstance(s, int):
            s = [s]
        if len(s) > 1:
            if new_data_sub[0] == new_data_sub[1] and new_data_sub[2] == new_data_sub[1]:
                pass
            else:
                print('Warning: Substrate data is not consistent')
            new_data_sub[si] = new_data_sub[0]
            si += 1

    return ikle, coord_p, new_data_sub


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


def fig_substrate(coord_p, ikle, sub_info, path_im, xtxt = [-99], ytxt= [-99], subtxt= [-99]):
    """
    The function to plot the raw substrate data, which was loaded before

    :param coord_p: the coordinate of the point
    :param ikle: the connectivity table
    :param sub_info: the information on subtrate by element
    :param xtxt: if the data was given in txt form, the orignal x data
    :param ytxt: if the data was given in txt form, the orignal y data
    :param subtxt: if the data was given in txt form, the orignal sub data
    :param path_im: the path where to save the figure
    """
    # pass sub_info to float
    # TO BE DONE!!!!
    sub_info = np.array(list(map(float, sub_info)))
    #plt.rcParams['figure.figsize'] = 7,3
    #plt.close()
    plt.rcParams['font.size'] = 10

    # prepare grid
    xlist = []
    ylist = []
    #ikle = np.array(ikle)
    coord_p = np.array(coord_p)
    #col_ikle = ikle.shape[1]
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

    # color data
    #plt.figure()
    fig,ax = plt.subplots(1)
    patches = []
    cmap = plt.get_cmap('gist_rainbow')
    colors = cmap((sub_info - np.min(sub_info))/(np.max(sub_info) - np.min(sub_info))) # convert nfloors to colors that we can use later
    n = len(sub_info)
    for i in range(0, n-1):
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
    #cbar = plt.colorbar()
    #cbar.ax.set_ylabel('Substrate')
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Substrate Grid')
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'), dpi=1000)
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'), dpi=1000)
    #plt.close()

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
        plt.show()
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
    #filename = 'mytest.shp'
    #filetxt = 'sub_txt2.txt'
    # # load shp file
    # [coord_p, ikle_sub, sub_info] = load_sub_shp(filename, path, 'VELOCITY')
    # fig_substrate(coord_p, ikle_sub, sub_info, path)
    # # load txt file
    #[coord_pt, ikle_subt, sub_infot,  x, y, sub] = load_sub_txt(filetxt, path,)
    #fig_substrate(coord_pt, ikle_subt, sub_infot, path, x, y, sub)
    path1 = r'D:\Diane_work\dummy_folder\DefaultProj'
    hdf5_name_hyd = os.path.join(path1, r'Hydro_HECRAS1D_CRITCREK13_02_2017_at_17_10_03.h5' )
    hdf5_name_sub = os.path.join(path1, r'Substrate_mytest_shp_13_02_2017_at_16_54_54.h5')
    [ikle_both, point_all_both, sub_data, vel, height] = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub,0)
    fig_merge_grid(point_all_both[0], ikle_both[0], path1)
    plt.show()


if __name__ == '__main__':
    main()