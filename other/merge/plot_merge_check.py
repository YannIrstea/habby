import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from matplotlib import colors


def plot_to_check_mesh_merging(hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data, merge_xy, merge_tin, merge_data):
    """
    hyd : hydraulic
    sub : substrate
    merge : hyd + sub merging
    all numpy array
    xy = coordinates by nodes (2d numpy array of float)
    tin = connectivity table by mesh (3d numpy array of int)
    data = data by mesh (1d numpy array)
    """
    data_min = min(min(sub_data), min(merge_data))
    data_max = max(max(sub_data), max(merge_data))
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)

    linewidth = 2
    hyd_edgecolor = "blue"
    sub_edgecolor = "orange"
    merge_edgecolor = "black"

    # hyd
    axs[0, 0].set_title("hydraulic")
    xlist = []
    ylist = []
    for i in range(0, len(hyd_tin)):
        pi = 0
        tin_i = hyd_tin[i]
        if len(tin_i) == 3:
            while pi < 2:  # we have all sort of xells, max eight sides
                # The conditions should be tested in this order to avoid to go out of the array
                p = tin_i[pi]  # we start at 0 in python, careful about -1 or not
                p2 = tin_i[pi + 1]
                xlist.extend([hyd_xy[p, 0], hyd_xy[p2, 0]])
                xlist.append(None)
                ylist.extend([hyd_xy[p, 1], hyd_xy[p2, 1]])
                ylist.append(None)
                pi += 1
            p = tin_i[pi]
            p2 = tin_i[0]
            xlist.extend([hyd_xy[p, 0], hyd_xy[p2, 0]])
            xlist.append(None)
            ylist.extend([hyd_xy[p, 1], hyd_xy[p2, 1]])
            ylist.append(None)
    axs[0, 0].plot(xlist, ylist, '-b', linewidth=linewidth, color=hyd_edgecolor)
    axs[0, 0].axis("scaled")  # x and y axes have same proportions

    # sub
    axs[0, 1].set_title("substrate")
    masked_array = np.ma.array(sub_data, mask=np.isnan(sub_data))  # create nan mask
    # data_min = masked_array.min()
    # data_max = masked_array.max()
    cmap = mpl.cm.get_cmap("jet")
    cmap.set_bad(color='black', alpha=1.0)
    n = len(sub_data)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = sub_xy[int(sub_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=linewidth, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    data_ploted.set_edgecolor(sub_edgecolor)
    axs[0, 1].add_collection(data_ploted)
    axs[0, 1].axis("scaled")  # x and y axes have same proportions

    # merge only mesh
    axs[1, 0].set_title("merge")
    xlist = []
    ylist = []
    for i in range(0, len(merge_tin)):
        pi = 0
        tin_i = merge_tin[i]
        if len(tin_i) == 3:
            while pi < 2:  # we have all sort of xells, max eight sides
                # The conditions should be tested in this order to avoid to go out of the array
                p = tin_i[pi]  # we start at 0 in python, careful about -1 or not
                p2 = tin_i[pi + 1]
                xlist.extend([merge_xy[p, 0], merge_xy[p2, 0]])
                xlist.append(None)
                ylist.extend([merge_xy[p, 1], merge_xy[p2, 1]])
                ylist.append(None)
                pi += 1
            p = tin_i[pi]
            p2 = tin_i[0]
            xlist.extend([merge_xy[p, 0], merge_xy[p2, 0]])
            xlist.append(None)
            ylist.extend([merge_xy[p, 1], merge_xy[p2, 1]])
            ylist.append(None)
    axs[1, 0].plot(xlist, ylist, '-b', linewidth=linewidth, color=merge_edgecolor)
    axs[1, 0].axis("scaled")  # x and y axes have same proportions

    # mesh with color
    axs[1, 1].set_title("merge (with color)")
    masked_array = np.ma.array(merge_data, mask=np.isnan(merge_data))  # create nan mask
    # data_min = masked_array.min()
    # data_max = masked_array.max()
    cmap = mpl.cm.get_cmap("jet")
    cmap.set_bad(color='black', alpha=1.0)
    n = len(merge_data)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = merge_xy[int(merge_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=linewidth, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    data_ploted.set_edgecolor(merge_edgecolor)
    axs[1, 1].add_collection(data_ploted)
    axs[1, 1].axis("scaled")  # x and y axes have same proportions

    plt.show()
