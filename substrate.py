import shapefile
import os
import numpy as np
import matplotlib.tri as tri
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import time


def load_sub_shp(filename, path, name_att='SUBSTRATE'):
    """
    A function to load the substrate in form of shapefile.
    :param filename the name of the shapefile
    :param path the path where the shapefile is
    :param name_att the name of the substrate column in the attribute table
    :return grid in form of list of coordinate and connectivity table (two list)
    and an array with substrate type
    """
    # THINK ABOUT START AT ZERO OR ONE
    # test extension and if the file exist
    blob, ext = os.path.splitext(filename)
    if ext != '.shp':
        print('Warning: the file does not have a .shp extension.')
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The shapefile "+filename+" does not exist.")
        return [-99], [-99], [-99]
    # read shp
    try:
        sf = shapefile.Reader(file)
    except shapefile.ShapefileException:
        print('Error: Cannot open the shapefile ' + filename + ', or one of the associated files (.shx, .dbf)')
        return [-99], [-99], [-99]

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
    A function to load the substrate in form of a text file
    the text file must have 3 column x,y corrdinate and substrate info, no header or title
    :param filename the name of the shapefile
    :param path the path where the shapefile is
    :return grid in form of list of coordinate and connectivity table (two list)
    and an array with substrate type and (x,y,sub) of the orginal data
    """
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The txt file "+filename+" does not exist.")
        return [-99], [-99], [-99]
    # read
    with open(file, 'rt') as f:
        data = f.read()
    data = data.split()
    if len(data) % 3 != 0:
        print('Error: the number of column in ' + filename+ ' is not three. Check format.')
        return [-99], [-99], [-99]
    # get x,y (you might have alphanumeric data in the thris colum)
    x = [data[i] for i in np.arange(0, len(data), 3)]
    y = [data[i] for i in np.arange(1, len(data), 3)]
    sub = [data[i] for i in np.arange(2, len(data), 3)]
    try:
        x = list(map(float,x))
        y = list(map(float,y))
    except TypeError:
        print("Error: Coordinates (x,y) could not be read as float. Check format of the file " + filename +'.')

    # Delauney
    triang = tri.Triangulation(x, y)
    ikle = triang.triangles
    xgrid = np.array(triang.x)
    ygrid = np.array(triang.y)
    xy = np.column_stack((xgrid,ygrid))
    # find one sub data by triangle ?
    sub_grid = np.zeros(len(ikle),)
    for e in range(0, len(ikle)):
        ikle_i = ikle[e]
        centerx = np.mean(xgrid[ikle_i])
        centery = np.mean(ygrid[ikle_i])
        nearest_ind = np.argmin(np.sqrt((x-centerx)**2 + (y-centery)**2))
        sub_grid[e] = sub[nearest_ind]

    return xy, ikle, sub_grid, x,y,sub


def fig_substrate(coord_p, ikle, sub_info, path_im, xtxt = [-99], ytxt= [-99], subtxt= [-99]):
    """
    :param coord_p: the coordinate of the point
    :param ikle: the connectivity table
    :param sub_info: the information on subtrate by element
    :param xtxt if the data was given in txt form, the orignal x data
    :param ytxt if the data was given in txt form, the orignal y data
    :param subtxt if the data was given in txt form, the orignal sub data
    :param path_im the path where to save the figure
    :return: figure
    """
    # pass sub_info to float
    # TO BE DONE!!!!
    sub_info = np.array(list(map(float, sub_info)))
    #plt.rcParams['figure.figsize'] = 7,3
    plt.close()
    plt.rcParams['font.size'] = 10

    # prepare grid
    xlist = []
    ylist = []
    ikle = np.array(ikle).squeeze()
    coord_p = np.array(coord_p)
    col_ikle = ikle.shape[1]
    for i in range(0, len(ikle)):
        pi = 0
        while pi < col_ikle-1:  # we have all sort of xells, max eight sides
            p = int(ikle[i, pi])  # we start at 0 in python, careful about -1 or not
            p2 = int(ikle[i, pi+1])
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = int(ikle[i, pi])
        p2 = int(ikle[i, 0])
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
        for j in range(0, len(ikle[i,:])):
            verts_j = coord_p[ikle[i, j], :]
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
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "substrate" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    plt.close()

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
        sc = plt.scatter(xtxt, ytxt, c=subtxt, vmin=np.nanmin(subtxt), vmax=np.nanmax(subtxt), s=s1, cmap=cm, edgecolors='none')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Original Substrate Data (x,y)')
        plt.savefig(os.path.join(path_im, "substrate_txtdata" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(os.path.join(path_im, "substrate_txtdata" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        plt.close()

    #plt.show()


def main():

    path = r'D:\Diane_work\output_hydro\substrate'
    filename = 'mytest.shp'
    filetxt = 'sub_test.txt'
    # load shp file
    [coord_p, ikle_sub, sub_info] = load_sub_shp(filename, path, 'VELOCITY')
    fig_substrate(coord_p, ikle_sub, sub_info, path)
    # load txt file
    [coord_pt, ikle_subt, sub_infot,  x, y, sub] = load_sub_txt(filetxt, path,)
    fig_substrate(coord_pt, ikle_subt, sub_infot, path, x, y, sub)


if __name__ == '__main__':
    main()