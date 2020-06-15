import numpy as np
import matplotlib.pyplot as plt
import triangle as tr
import math
from datetime import datetime

from src.plot_mod import plot_to_check_mesh_merging


def merge(hyd_xy, hyd_data_node, hyd_tin, iwholeprofile, hyd_data_mesh, sub_xy, sub_tin, sub_data, sub_default,
          coeffgrid):
    """
    Merging an hydraulic TIN (Triangular Irregular Network) and a substrate TIN to obtain a merge TIN
    (based on the hydraulic one) by partitionning each hydraulic triangle/mesh if necessary into smaller
    triangles/meshes that contain a substrate from the substrate TIN or a default substrate. Additional nodes inside
    or on the edges of an hydraulic mesh will be given hydraulic data by interpolation of the hydraulic data from the
    hydraulic mesh nodes.Flat hydraulic or substrates triangles will not been taken inot account.
     Using numpy arrays as entry and returning numpy arrays.
    :param hyd_xy: The x,y nodes coordinates of a hydraulic TIN (Triangular Irregular Network)
    :param hyd_data_node: The hydraulic data of the hydraulic nodes (eg : z, wather depth, mean velocity...)
    :param hyd_tin: The hydraulic TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a
            mesh/triangle
    :param iwholeprofile: A two columns numpy array describing each hydraulic mesh:
            first column an index corresponding to the original hydraulic TIN (before taking away the dry part for
            instance) 2nd column i_split 0 if the hydraulic original mesh have never been partitioned, 1 if it has been
            partitioned by taking away a dry part
    :param hyd_data_mesh: hydraulic data affected to each hydraulic mesh
    :param sub_xy: the x,y nodes coordinates of a substrate TIN (Triangular Irregular Network)
    :param sub_tin: the substrate TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a
    mesh/triangle
    :param sub_data: substrate data affected to each substrate mesh
    :param sub_default: substrate data given by default to a merge mesh if no substrate
    :param coeffgrid: a special coefficient for defining a grid build in  the area surrounding the TINs  and used for
    the grid algorithm this grid is used to select substrate meshes that are just in the surrounding of an hydraulic
    mesh in order to define all the segments from hydraulix substrate edges that are intersecting the hydraulic mesh
    considered.
    :return:
            merge_xy1 : the x,y nodes coordinates of a hydraulic TIN
            merge_data_node : the hydraulic data of the merge nodes (eg : z, wather depth, mean velocity...)
            merge_tin1 : the merge TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a
                        mesh/triangle
            iwholeprofilemerge : similar to iwholeprofile describing each hydraulic mesh
                           i_split can also have the values :  2 if the mesh has been partioned by the merge : 3  if the mesh has been partioned previously by taking away a dry part and also a second time by the merge
                           a third column is added i_subdefaut marking by the value 1 when the defaut substrate has been assigned to the mesh, 0 otherwise
            merge_data_mesh : hydraulic data affected to each merge mesh
            merge_data_sub_mesh : substrate data affected to each merge mesh
    """
    gridelt = griddef(hyd_xy, sub_xy, hyd_tin, sub_tin, coeffgrid)  # building the grid
    # print(gridelt)
    # print ("titi")
    celltriangleindexsub, celltrianglelistsub = gridtin(sub_xy, sub_tin,
                                                        gridelt,
                                                        True)  # indexing the substrate ikle (list of mesh/triangles) in reference to the grid
    decalnewpointmerge = 0
    xymerge = []
    iklemerge = []
    merge_data_sub_mesh = []
    xymergepointlinkstohydr = []
    iwholeprofilemerge, merge_data_mesh = [], []
    # merging each hydraulic mesh/triangle with the substrate mesh/triangles that can be found in the same part of the grid
    for i in range(hyd_tin.size // 3):  # even if one single triangle for hyd_tin
        xyo, xya, xyb = hyd_xy[hyd_tin[i][0]], hyd_xy[hyd_tin[i][1]], hyd_xy[hyd_tin[i][2]]
        axy, bxy = xya - xyo, xyb - xyo
        deta = bxy[1] * axy[0] - bxy[0] * axy[1]
        if deta == 0:
            print('before merging an hydraulic triangle have an area=0 ')
        else:

            xymesh = np.vstack((xyo, xya, xyb))
            xymeshydmax, xymeshydmin = np.max(xymesh, axis=0), np.min(xymesh, axis=0)
            listcells = intragridcells(xymesh,
                                       gridelt)  # list of the grid cells containing the surrounding of the hydraulic mesh/triangle

            # finding the edges of substrate mesh/triangles able to be in the hydraulic triangle or to cut it eliminating duplicate edges
            # determining the list of substrate mesh that are in the same grid area of the hydraulic triangle
            setofmeshsubindex = set()  # the list of substrate mesh that are in the same grid area of the hydraulic triangle
            for c in listcells:
                if celltriangleindexsub[c][
                    0] != -1:  # the surrounding of a substrate mesh/triangle is in a grid cell (that is surrounding our hydraulic mesh)
                    for k in range(celltriangleindexsub[c][0], celltriangleindexsub[c][1] + 1):
                        isub = celltrianglelistsub[k][1]
                        setofmeshsubindex.add(isub)

            listofsubedges = []  # the list of substrate edges in the surrounding of the hydraulic mesh/triangle
            listofsubedgesindex = []  # the list of substrate mesh indexes corresponding to substrate edges
            for isub in setofmeshsubindex:
                # eliminating substrate mesh out of the very surrounding of the hydraulic mesh
                xymeshsub = np.vstack((sub_xy[sub_tin[isub][0]], sub_xy[sub_tin[isub][1]], sub_xy[sub_tin[isub][2]]))
                if not ((np.min(xymeshsub, axis=0) > xymeshydmax).any() or (
                        np.max(xymeshsub, axis=0) < xymeshydmin).any()):
                    listofsubedges.extend([[sub_tin[isub][0], sub_tin[isub][1]], [sub_tin[isub][1], sub_tin[isub][2]],
                                           [sub_tin[isub][2], sub_tin[isub][0]]])
                    listofsubedgesindex.extend([isub, isub, isub])
            if len(listofsubedgesindex) != 0:
                subedges = np.array(
                    listofsubedges)  # array of substrate edges in the surrounding of the hydraulic mesh/triangle
                subedgesindex = np.array(
                    listofsubedgesindex)  # array of substrate mesh indexes corresponding to substrate edges
                # removing duplicate edges
                subedges.sort(
                    axis=1)  # in order to be able in the following : to consider (1,4) and (4,1) as the same edge (we have here at least 3 edges)
                subedgesunique, indices = np.unique(subedges, axis=0,
                                                    return_inverse=True)  # subedgesunique the edges of substrate mesh/triangles able to be in the hydraulic triangle or to cut it whith no duplicates
                subedgesuniqueindex = np.stack((indices, subedgesindex), axis=-1)
                subedgesuniqueindex = subedgesuniqueindex[subedgesuniqueindex[:, 0].argsort()]
                lsubedgesuniqueindex = []
                j0 = -3
                for j in range(len(indices)):
                    if subedgesuniqueindex[j][0] != j0:
                        if j0 != -3:
                            lsubedgesuniqueindex.append(l)
                        l = [subedgesuniqueindex[j][1]]
                        j0 = subedgesuniqueindex[j][0]
                    else:
                        l.append(subedgesuniqueindex[j][1])
                lsubedgesuniqueindex.append(
                    l)  # we have now for each edge of subedgesunique a corresponding list of substrate mesh/triangles (lsubedgesuniqueindex) wich are using that edge one edge can belong to two substrate mesh

                # finding the edges of substrate mesh/triangles that are inside the hydraulic triangle
                xynewpoint = []  # the points we are creating
                xynewpointlinkstohydr = []  # for each point of xynewpoint a sublist of 2 or 3 hydraulic points indexes in order to interpolate hydraulics values
                inewpoint = -1
                segin = []  # list of segments by reference to two newpoint index that are in
                # checking if points defining the substrate segment are inside or not in the hydraulic triangle and what exact edge of this triangle can be crossed
                lsubmeshin = []  # list of list of substrate mesh wich are in the hydraulic triangle (to flatten and duplicates have to be eliminated)
                # the vertices of our hydraulic triangle are stored because we will used them for segment definition given to Triangle library
                xynewpoint.extend([xyo, xya, xyb])
                xynewpointlinkstohydr.extend(
                    [[hyd_tin[i][0], -1, -1], [hyd_tin[i][1], -1, -1], [hyd_tin[i][2], -1, -1]])
                inewpoint += 3

                # seaching for each substrate segment if we can extract a sub-segment inside the hydraulic triangle
                sidecontact1, sidecontact2, sidecontact4 = [], [], []
                for j in range(len(subedgesunique)):
                    xyp, xyq = sub_xy[subedgesunique[j][0]], sub_xy[subedgesunique[j][1]]
                    xyaffp = [(bxy[1] * (xyp[0] - xyo[0]) - bxy[0] * (xyp[1] - xyo[1])) / deta,
                              (-axy[1] * (xyp[0] - xyo[0]) + axy[0] * (xyp[1] - xyo[1])) / deta]
                    xyaffq = [(bxy[1] * (xyq[0] - xyo[0]) - bxy[0] * (xyq[1] - xyo[1])) / deta,
                              (-axy[1] * (xyq[0] - xyo[0]) + axy[0] * (xyq[1] - xyo[1])) / deta]
                    sidecontact = [0,
                                   0]  # 2 numbers defining the position regarding the hydraulic triangle of repectively  P and Q (the points defining the subtrate segment )
                    for k, xyaff in enumerate([xyaffp, xyaffq]):
                        if xyaff[1] <= 0:
                            sidecontact[k] += 1
                        if xyaff[0] <= 0:
                            sidecontact[k] += 2
                        if xyaff[1] >= -xyaff[0] + 1:
                            sidecontact[k] += 4
                    # both points of the substrate segment are inside the hydraulic triangle
                    if sidecontact[0] == 0 and sidecontact[1] == 0:
                        xynewpoint.extend([xyp, xyq])
                        xynewpointlinkstohydr.extend(
                            [[hyd_tin[i][0], hyd_tin[i][1], hyd_tin[i][2]],
                             [hyd_tin[i][0], hyd_tin[i][1], hyd_tin[i][2]]])
                        segin.append([inewpoint + 1, inewpoint + 2])
                        inewpoint += 2
                        lsubmeshin.append(lsubedgesuniqueindex[j])
                    # one point of the substrate segment is inside the hydraulic triangle
                    elif (sidecontact[0] != 0 and sidecontact[1] == 0) or (sidecontact[1] != 0 and sidecontact[0] == 0):
                        xypq = [xyp, xyq]
                        kin, kout = 0, 1  # index of the xypq coordinates of the points defining the segment that are inside and outside the hydraulic triangle
                        if sidecontact[1] == 0:
                            kin, kout = 1, 0
                        xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][1], hyd_tin[i][2]])
                        bok1, bok2, bok4 = False, False, False
                        if sidecontact[kout] == 1:
                            bok1, xycontact1, distsqr1 = intersection2segmentsdistsquare(xyo, xya, xyp, xyq)
                        elif sidecontact[kout] == 2:
                            bok2, xycontact2, distsqr2 = intersection2segmentsdistsquare(xyb, xyo, xyp, xyq)
                        elif sidecontact[kout] == 4:
                            bok4, xycontact4, distsqr4 = intersection2segmentsdistsquare(xya, xyb, xyp, xyq)
                        elif sidecontact[kout] == 3:
                            bok1, xycontact1, distsqr1 = intersection2segmentsdistsquare(xyo, xya, xyp, xyq)
                            bok2, xycontact2, distsqr2 = intersection2segmentsdistsquare(xyb, xyo, xyp, xyq)
                        elif sidecontact[kout] == 5:
                            bok1, xycontact1, distsqr1 = intersection2segmentsdistsquare(xyo, xya, xyp, xyq)
                            bok4, xycontact4, distsqr4 = intersection2segmentsdistsquare(xya, xyb, xyp, xyq)
                        elif sidecontact[kout] == 6:
                            bok4, xycontact4, distsqr4 = intersection2segmentsdistsquare(xya, xyb, xyp, xyq)
                            bok2, xycontact2, distsqr2 = intersection2segmentsdistsquare(xyb, xyo, xyp, xyq)
                        if bok1 + bok2 + bok4 != 1: #numerical problem the intersection point  is just close to a node but out of the hydraulic triangle
                            print("Numerical problems doing for the best")
                            bsolve=True
                            if sidecontact[kout] ==1 or sidecontact[kout] ==2 or sidecontact[kout] ==4:
                                bsolve,relativeindexhyd=intersection2doitesaffines(sidecontact[kout], xyaffp, xyaffq)
                            elif sidecontact[kout] == 3:
                                relativeindexhyd=0
                            elif sidecontact[kout] ==5:
                                relativeindexhyd = 1
                            elif sidecontact[kout] == 6:
                                relativeindexhyd = 2
                            if bsolve:
                                xynewpointlinkstohydr.append([hyd_tin[i][relativeindexhyd], -1, -1])
                                xynewpoint.extend([xypq[kin]])
                                segin.append([inewpoint + 1, relativeindexhyd])
                                inewpoint += 1
                        else:
                            if bok1:
                                xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][1], -1])
                                sidecontact1.append([distsqr1, inewpoint + 2])
                                xynewpoint.extend([xypq[kin], xycontact1])
                            elif bok2:
                                xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][2], -1])
                                sidecontact2.append([distsqr2, inewpoint + 2])
                                xynewpoint.extend([xypq[kin], xycontact2])
                            elif bok4:
                                xynewpointlinkstohydr.append([hyd_tin[i][1], hyd_tin[i][2], -1])
                                sidecontact4.append([distsqr4, inewpoint + 2])
                                xynewpoint.extend([xypq[kin], xycontact4])
                            segin.append([inewpoint + 1, inewpoint + 2])
                            inewpoint += 2
                        lsubmeshin.append(lsubedgesuniqueindex[j])

                        # print(subedgesunique[j])

                    # seaching if the substrate segment cut 2 edges of the the hydraulic triangle
                    else:
                        bok1, xycontact1, distsqr1 = intersection2segmentsdistsquare(xyo, xya, xyp, xyq)
                        bok2, xycontact2, distsqr2 = intersection2segmentsdistsquare(xyb, xyo, xyp, xyq)
                        bok4, xycontact4, distsqr4 = intersection2segmentsdistsquare(xya, xyb, xyp, xyq)
                        if bok1 + bok2 + bok4 == 2:
                            if bok1 and bok2:
                                xynewpoint.extend([xycontact1, xycontact2])
                                xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][1], -1])
                                xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][2], -1])
                                sidecontact1.append([distsqr1, inewpoint + 1])
                                sidecontact2.append([distsqr2, inewpoint + 2])
                            if bok1 and bok4:
                                xynewpoint.extend([xycontact1, xycontact4])
                                xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][1], -1])
                                xynewpointlinkstohydr.append([hyd_tin[i][1], hyd_tin[i][2], -1])
                                sidecontact1.append([distsqr1, inewpoint + 1])
                                sidecontact4.append([distsqr4, inewpoint + 2])
                            if bok4 and bok2:
                                xynewpoint.extend([xycontact4, xycontact2])
                                xynewpointlinkstohydr.append([hyd_tin[i][1], hyd_tin[i][2], -1])
                                xynewpointlinkstohydr.append([hyd_tin[i][0], hyd_tin[i][2], -1])
                                sidecontact4.append([distsqr4, inewpoint + 1])
                                sidecontact2.append([distsqr2, inewpoint + 2])
                            segin.append([inewpoint + 1, inewpoint + 2])
                            inewpoint += 2
                            lsubmeshin.append(lsubedgesuniqueindex[j])

                # using Triangle library to build a triangular mesh based on substrate segments inside the hydraulic triangle
                if inewpoint != 2:
                    # adding all partials segments along the edges of the hydraulical triangle
                    if len(sidecontact1) != 0:
                        sidecontact1.sort()
                        sidecontact1 = [y[1] for y in sidecontact1]
                    if len(sidecontact2) != 0:
                        sidecontact2.sort()
                        sidecontact2 = [y[1] for y in sidecontact2]
                    if len(sidecontact4) != 0:
                        sidecontact4.sort()
                        sidecontact4 = [y[1] for y in sidecontact4]
                    sidecontact1 = [0] + sidecontact1 + [1]
                    sidecontact2 = [2] + sidecontact2 + [0]
                    sidecontact4 = [1] + sidecontact4 + [2]
                    for sidecontactx in (sidecontact1, sidecontact2, sidecontact4):
                        for y in range(len(sidecontactx) - 1):
                            segin.append([sidecontactx[y], sidecontactx[y + 1]])

                    # A = {'vertices': xynewpoint, 'segments': segin}

                    # eliminating duplicate points for using Triangle library
                    nxynewpoint = np.array(xynewpoint)  # [xypq[kin], xycontact,......])
                    nsegin = np.array(segin)  # [inewpoint + 1, inewpoint + 2]
                    nxynewpointlinkstohydr = np.array(
                        xynewpointlinkstohydr)  # [hyd_tin[i][0], hyd_tin[i][1], hyd_tin[i][2]],[hyd_tin[i][0], hyd_tin[i][1], -1],.
                    nxynewpoint2, indices2 = np.unique(nxynewpoint, axis=0, return_inverse=True)
                    nsegin2 = indices2[nsegin]
                    nxynewpoint2, indices3 = np.unique(nxynewpoint, axis=0,
                                                       return_index=True)  # nxynewpoint2 doesnt change
                    nxynewpointlinkstohydr2 = nxynewpointlinkstohydr[indices3]
                    # Using Triangle library to build a mesh from our segments
                    A = {'vertices': nxynewpoint2, 'segments': nsegin2}
                    t = tr.triangulate(A, 'p')

                    # tr.compare(plt, A, t)
                    # plt.show()
                    # print(nxynewpoint2)
                    # print(t['vertices'],t['triangles'])

                    # check if Triangle library has added new points at the end of our original list of 'vertices'
                    nxynewpoint, iklenew = t['vertices'], t['triangles']
                    newpointtrianglevalidate = len(t['vertices']) - len(nxynewpoint2)
                    if newpointtrianglevalidate != 0:  # Triangle library has added new points at the end of our original list of 'vertices'
                        nxynewpointlinkstohydr = np.vstack([nxynewpointlinkstohydr2, np.repeat(
                            [[hyd_tin[i][0], hyd_tin[i][1], hyd_tin[i][2]]], newpointtrianglevalidate, axis=0)])

                    else:
                        nxynewpointlinkstohydr = nxynewpointlinkstohydr2

                    # affecting substrate values to meshes merge
                    ssubmeshin2 = set([item for sublist in lsubmeshin for item in
                                       sublist])  # set of substrate mesh that can be in the hydraulic triangle
                    # testing meshes merge centers regarding substrate mesh  to affect substrate values to meshes merge
                    datasubnew = [sub_default.tolist()] * (iklenew.size // 3)  # even if one single triangle for iklenew
                    for ii, ikle in enumerate(iklenew):
                        xyc = (nxynewpoint[ikle[0]] + nxynewpoint[ikle[1]] + nxynewpoint[ikle[2]]) / 3
                        for jj in ssubmeshin2:
                            if point_inside_polygon(xyc[0], xyc[1],
                                                    [sub_xy[sub_tin[jj][0]].tolist(), sub_xy[sub_tin[jj][1]].tolist(),
                                                     sub_xy[sub_tin[jj][2]].tolist()]):
                                datasubnew[ii] = sub_data[jj].tolist()
                                break

                else:  # no substrate edges in the hydraulic triangle
                    nxynewpoint = np.array([xyo, xya, xyb])
                    nxynewpointlinkstohydr = np.array(
                        [[hyd_tin[i][0], -1, -1], [hyd_tin[i][1], -1, -1], [hyd_tin[i][2], -1, -1]])
                    iklenew = np.array([[0, 1, 2]])
                    datasubnew = [sub_default.tolist()]
                    # checking if a substrate mesh contain the hydraulic mesh
                    xyc = (xyo + xya + xyb) / 3
                    for jj in setofmeshsubindex:
                        if point_inside_polygon(xyc[0], xyc[1],
                                                [sub_xy[sub_tin[jj][0]].tolist(), sub_xy[sub_tin[jj][1]].tolist(),
                                                 sub_xy[sub_tin[jj][2]].tolist()]):
                            datasubnew[0] = sub_data[jj]
                            break
            else:  # no substrate mesh around the hydraulic triangle
                nxynewpoint = np.array([xyo, xya, xyb])
                nxynewpointlinkstohydr = np.array(
                    [[hyd_tin[i][0], -1, -1], [hyd_tin[i][1], -1, -1], [hyd_tin[i][2], -1, -1]])
                iklenew = np.array([[0, 1, 2]])
                datasubnew = [sub_default.tolist()]

            # merges accumulation
            nbmeshmergeadd = len(iklenew)
            xymerge.extend(nxynewpoint.tolist())
            iklemerge.extend((iklenew + decalnewpointmerge).tolist())
            merge_data_sub_mesh.extend(datasubnew)
            lwp = iwholeprofile[i].tolist()
            if nbmeshmergeadd != 1:
                lwp[
                    1] += 2  # marking the second column of iwholprofile with +2 that indicates that the merge operation have partitionned a hydraulic mesh
            iwholeprofilemerge.extend([lwp] * nbmeshmergeadd)
            merge_data_mesh.extend([hyd_data_mesh[i].tolist()] * nbmeshmergeadd)
            xymergepointlinkstohydr.extend(nxynewpointlinkstohydr.tolist())
            decalnewpointmerge += len(nxynewpoint)
    # get rid of duplicate points
    merge_xy = np.array(xymerge)
    merge_tin = np.array(iklemerge)
    merge_xypointlinkstohydr = np.array(xymergepointlinkstohydr)
    merge_xy1, indices2 = np.unique(merge_xy, axis=0, return_inverse=True)
    merge_tin1 = indices2[merge_tin]
    merge_xy1, indices3 = np.unique(merge_xy, axis=0, return_index=True)  # nxynewpoint2 doesnt change
    merge_xypointlinkstohydr1 = merge_xypointlinkstohydr[indices3]
    # ++++interpolate datahyd
    nbline, nbcol = len(merge_xy1), hyd_data_node.shape[1]
    merge_data_node = np.zeros((nbline, nbcol), dtype=np.float64)
    col1 = merge_xypointlinkstohydr1[:, 1] == -1
    col2 = merge_xypointlinkstohydr1[:, 2] == -1
    # merge_data_node[not(col1+col2)]=hyd_data_node[merge_xypointlinkstohydr1[not(col1+col2)]]
    for i in range(nbline):
        if col1[i] and col2[i]:
            merge_data_node[i] = hyd_data_node[merge_xypointlinkstohydr1[i][0]]
        elif col2[i]:
            merge_data_node[i] = linear_interpolation_segment(merge_xy1[i], hyd_xy[merge_xypointlinkstohydr1[i][0:2]],
                                                              hyd_data_node[merge_xypointlinkstohydr1[i][0:2]])
        else:
            merge_data_node[i] = finite_element_interpolation(merge_xy1[i], hyd_xy[merge_xypointlinkstohydr1[i]],
                                                              hyd_data_node[merge_xypointlinkstohydr1[i]])
    #marking  in iwholeprofilemerge the mesh containing defautsub in third column
    # iwholeprofilemerge=np.array(iwholeprofilemerge)
    merge_data_sub_mesh=np.array(merge_data_sub_mesh)
    (np.sum(merge_data_sub_mesh == defautsub, axis=1) // 2).reshape((merge_data_sub_mesh.size//defautsub.size, 1))
    iwholeprofilemerge=np.hstack((iwholeprofilemerge, (np.sum(merge_data_sub_mesh == defautsub, axis=1) // 2).reshape(merge_data_sub_mesh.size//defautsub.size, 1)))
    return merge_xy1, merge_data_node, merge_tin1, iwholeprofilemerge, np.array(merge_data_mesh),merge_data_sub_mesh


def finite_element_interpolation(xyp, xypmesh, datamesh):
    """
    This function gets the value of a data (z for instance) for a  point inside of finite element (mesh)  by linear interpolation.
    :param xyp: the coordinates of the  point
    :param xypmesh: the coordinates of  three  points
    :param datamesh: the data for the  three  points
    :return: the interpolated data for the point inside the mesh
    """
    x1, x2, x3 = xypmesh[0][0], xypmesh[1][0], xypmesh[2][0]
    y1, y2, y3 = xypmesh[0][1], xypmesh[1][1], xypmesh[2][1]
    va1, va2, va3 = datamesh[0], datamesh[1], datamesh[2]
    # point new
    xm, ym = xyp[0], xyp[1]
    valm = va1  # force to have coherent value (if divide by 0)
    det = (x2 - x3) * (y2 - y1) - (x2 - x1) * (y2 - y3)
    if det == 0:
        print("divide by zero, not a triangle ?")
    else:
        # formula Yann Le Coarer
        valm = va1 + ((xm - x1) * ((y2 - y1) * (va2 - va3) - (y2 - y3) * (va2 - va1)) + (ym - y1) * (
                (x2 - x3) * (va2 - va1) - (x2 - x1) * (va2 - va3))) / det
    return valm


def linear_interpolation_segment(xyM, xyAB, data):
    """
    This function gets the value of a data (z for instance) for a  point inside a segment 2D  by linear interpolation.
    :param xyM: the coordinates of the  point
    :param xyAB: the coordinates of  2  points
    :param data: the data for the  three  points
    :return: the interpolated data for the point inside the mesh
    """
    xa, xb = xyAB[0][0], xyAB[1][0]
    ya, yb = xyAB[0][1], xyAB[1][1]
    va, vb, = data[0], data[1]
    # point new
    xm, ym = xyM[0], xyM[1]
    vm = va  # force to have coherent value (if divide by 0)
    dab = math.sqrt((xb - xa) ** 2 + (yb - ya) ** 2)
    if dab == 0:
        print("the segment is a point ?")
    else:
        dam = math.sqrt((xm - xa) ** 2 + (ym - ya) ** 2) / dab
        vm = (1 - dam) * va + dam * vb
    return vm

def intersection2doitesaffines(sidecontactaffine,  xyc, xyd):
    if sidecontactaffine==1:
        xya, xyb,ka,kb=[0,0],[1,0],0,1
    elif sidecontactaffine == 2:
        xya, xyb,ka,kb = [0, 0], [0, 1],0,2
    elif sidecontactaffine == 4:
        xya, xyb,ka,kb = [1, 0], [0, 1],1,2
    u1, u2 = xyb[1] - xya[1], xyd[1] - xyc[1]
    v1, v2 = xya[0] - xyb[0], xyc[0] - xyd[0]
    w1, w2 = xya[1] * xyb[0] - xya[0] * xyb[1], xyc[1] * xyd[0] - xyc[0] * xyd[1]
    det = u1 * v2 - u2 * v1
    bok,nodeindex = False,-1
    if det != 0:
        bok = True
        xycontact = [(-w1 * v2 + w2 * v1) / det, (-u1 * w2 + u2 * w1) / det]
        dist_square_to_a = (xycontact[0] - xya[0]) ** 2 + (xycontact[1] - xya[1]) ** 2
        if dist_square_to_a<0.1:
            nodeindex=ka
        else:
            nodeindex = kb
    return bok,nodeindex

def intersection2segmentsdistsquare(xya, xyb, xyc, xyd):
    '''
     defining if 2 segments respetively AB ,CD are crossing  and giving coordinates of the instersection point and its the square distance from A
    :param xya, xyb, xyc xyd: the x,y coordinates of 4 points defining 2 segments respetively AB ,CD
    :return:
            bok : True if  the segments  AB  & CD are crossing, False if not
            xycontact  : the x,y coordinates of the instersection point
            dist_square_to_a :  the square distance from A of the instersection point
    '''
    bok = False
    xycontact = [None, None]
    dist_square_to_a = 0
    u1, u2 = xyb[1] - xya[1], xyd[1] - xyc[1]
    v1, v2 = xya[0] - xyb[0], xyc[0] - xyd[0]
    w1, w2 = xya[1] * xyb[0] - xya[0] * xyb[1], xyc[1] * xyd[0] - xyc[0] * xyd[1]
    det = u1 * v2 - u2 * v1
    if det != 0:
        # valeur 0 acceptée car l'on admet que l'un des points A,B,C,D peut être sur les 2 segments
        if (u2 * xya[0] + v2 * xya[1] + w2) * ((u2 * xyb[0] + v2 * xyb[1] + w2)) <= 0 and (
                u1 * xyc[0] + v1 * xyc[1] + w1) * ((u1 * xyd[0] + v1 * xyd[1] + w1)) <= 0:
            bok = True
            xycontact = [(-w1 * v2 + w2 * v1) / det, (-u1 * w2 + u2 * w1) / det]
            dist_square_to_a = (xycontact[0] - xya[0]) ** 2 + (xycontact[1] - xya[1]) ** 2
    return bok, xycontact, dist_square_to_a


def gridtin(sub_xy, sub_tin, gridelt, bnoflat):  # sub_xy, sub_tin
    '''
    building the table : for each cell of the grid  determining the list of meshes from the substrate TIN that have at least a part in the cell
    :param sub_xy: the x,y nodes coordinates of a substrate TIN (Triangular Irregular Network)
    :param sub_tin: the substrate TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a mesh/triangle
    :param gridelt a dictionary
            : xymax,xymin : respectively the xy maximum and minimum coordinates of the rectangle defining the limits of the grid
            : deltagrid : the measure of grid cell edge
            :nbcell : the total number of the cells in the grid
    :param bnoflat if True we do not take into account flat triangle
    :return:
            celltriangleindex : a two columns list corresponding for each line to a grid cell
                                for a cell index (a line)
                                    if no substrate mesh inside [-1,-1]
                                    if at least a substrate mesh inside [first index of celltrianglelist, last index of celltrianglelist]
                                        defining the range of lines in celltrianglelist corresponding to the cell index (1st column) and substrate mesh indexes (2nd column)

            celltrianglelist :  a two columns sorted list by grid cell index  first column a grid cell index second column a substrate index mesh
    '''
    table0 = []

    area2 = (sub_xy[sub_tin[:, 1]][:, 0] - sub_xy[sub_tin[:, 0]][:, 0]) * (
                sub_xy[sub_tin[:, 2]][:, 1] - sub_xy[sub_tin[:, 0]][:, 1]) - (
                    sub_xy[sub_tin[:, 2]][:, 0] - sub_xy[sub_tin[:, 0]][:, 0]) * (
                        sub_xy[sub_tin[:, 1]][:, 1] - sub_xy[sub_tin[:, 0]][:, 1])

    for i in range(sub_tin.size // 3):  # even if one single triangle for sub_tin
        if area2[i] != 0 and bnoflat:  # not take into account flat triangle
            xymesh = np.vstack((sub_xy[sub_tin[i][0]], sub_xy[sub_tin[i][1]], sub_xy[sub_tin[i][2]]))
            listcells = intragridcells(xymesh, gridelt)
            for j in listcells:
                table0.append([j, i])
    # print(table0)
    celltrianglelist = np.array(
        table0)  # to avoid topoligical problem  eventually set(table0) if orignal ikle contains double ....
    # print()
    # print( celltrianglelist)
    celltrianglelist = celltrianglelist[celltrianglelist[:, 0].argsort()]
    celltriangleindex = np.empty((gridelt['nbcell'][0] * gridelt['nbcell'][1] + 1,
                                  2))  # WARNING  +1 the first line index 0 in python is not used the first cell of the grid began to one
    celltriangleindex.fill(-1)
    j0 = -3
    for i, j in enumerate(celltrianglelist):
        if j[0] != j0:
            celltriangleindex[j[0]][0] = i
            celltriangleindex[j[0]][1] = i  # in case of one single triangle
            j0 = j[0]
        else:
            celltriangleindex[j[0]][1] = i  # TODO improve...

    # print(celltriangleindex)
    # print()
    # print( celltrianglelist)
    return celltriangleindex.astype(
        np.int64), celltrianglelist  # the first column of celltrianglelist will not be used after


def intragridcells(xymesh, gridelt):
    '''
    how to extract the cells numbers of the intra-grid(sub grid) that contains the triangle
    :param xymesh: the xy, coordinates of 3 nodes defining a mesh
    :param gridelt a dictionary
            : xymax,xymin : respectively the xy maximum and minimum coordinates of the rectangle defining the limits of the grid
            : deltagrid : the measure of grid cell edge
            :nbcell : the total number of the cells in the grid
    :return:
            listcells : the cells numbers of the intra-grid(sub grid) that contains the triangle
    '''
    xymaxmesh = np.max(xymesh, axis=0)
    xyminmesh = np.min(xymesh, axis=0)
    rectangle = np.array([[xyminmesh[0], xyminmesh[1]], [xymaxmesh[0], xyminmesh[1]], [xyminmesh[0], xymaxmesh[1]],
                          [xymaxmesh[0], xymaxmesh[1]]])
    listcells0 = []
    for j in range(4):
        xx = (rectangle[j][0] - gridelt['xymin'][0]) / gridelt['deltagrid']
        xx1 = math.floor(xx)
        if xx - xx1 != 0:
            xx1 += 1
        if xx1 == 0:
            xx1 = 1
        yy = (rectangle[j][1] - gridelt['xymin'][1]) / gridelt['deltagrid']
        yy1 = math.floor(yy) * gridelt['nbcell'][0]  # gridelt['nbcell'][0] = number of columns of the grid
        listcells0.append(int(xx1 + yy1))
    listcells = []
    nbcolx = listcells0[1] - listcells0[0] + 1
    if listcells0[3] - listcells0[2] + 1 != nbcolx:
        print('Error in extracting intra-grid')
    intragridx = [listcells0[0] + y * gridelt['nbcell'][0] for y in range(
        (listcells0[2] - listcells0[0]) // gridelt['nbcell'][
            0] + 1)]  # (listcells0[3]-listcells0[0])//gridelt['nbcell'][0]+1 = nblines of the intragrid
    listcells = [y for k in intragridx for y in range(k, k + nbcolx)]
    return listcells


def griddef(xyhyd, sub_xy, iklehyd, sub_tin, coeffgrid):
    '''
    defining the grid that will be  used to select substrate meshes that are just in the surrounding of an hydraulic mesh to minimize the computing time
    :param xyhyd:the x,y nodes coordinates of a hydraulic TIN (Triangular Irregular Network)
    :param sub_xy: the x,y nodes coordinates of a substrate TIN (Triangular Irregular Network)
    :param iklehyd: the hydraulic TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a mesh/triangle
    :param sub_tin: the substrate TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a mesh/triangle
    :param coeffgrid: a special coefficient for defining a grid build in  the area surrounding the TINs  and used for the grid algorithm  is define
    :return: gridelt a dictionary
            : xymax,xymin : respectively the xy maximum and minimum coordinates of the rectangle defining the limits of the grid
            : deltagrid : the measure of grid cell edge
            :nbcell : the total number of the cells in the grid
    '''
    gridelt = {}
    xyall = np.concatenate((xyhyd, sub_xy), axis=0)
    xymax0 = np.ceil(
        np.max(xyall, axis=0) + 0.1)  # +0.1 to avoid point with xmax or ymax beign out of the constructed grid
    xymin = np.floor(np.min(xyall, axis=0))
    dxygrid = xymax0 - xymin
    totalarea = dxygrid[0] * dxygrid[1]

    areahyd, densityhyd = tinareadensity(xyhyd, iklehyd)
    areasub, densitysub = tinareadensity(sub_xy, sub_tin)
    nbgrid = math.ceil(max(densityhyd, densitysub) * totalarea * coeffgrid)

    # nbmeshhyd,nbmeshsub=hyd_tin.size // 3,sub_tin.size // 3
    # nbgrid=math.ceil(max(nbmeshhyd,nbmeshsub)*coeffgrid)

    # nbgrid = math.ceil(math.sqrt(63 + 0.0005 * (len(hyd_xy) + len(sub_xy)) / 2))

    if nbgrid == 0:
        return False  # TODO Gerer ce cas ou les maillages sont vides
    deltagrid = math.ceil(math.sqrt(totalarea / nbgrid))
    nbcell = np.ceil(dxygrid / deltagrid)
    gridelt['xymax'] = xymin + nbcell * deltagrid
    gridelt['xymin'] = xymin
    gridelt['deltagrid'] = deltagrid
    gridelt['nbcell'] = nbcell.astype(np.int64)
    return gridelt


def point_inside_polygon(x, y, poly):
    """
    http://www.ariel.com.au/a/python-point-int-poly.html
    To know if point is inside or outsite of a polygon (without holes)
    :param x: coordinate x in float
    :param y: coordinate y in float
    :param poly: list of coordinates [[x1, y1], ..., [xn, yn]]
    :return: True (inside), False (not inseide)
    """
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def tinareadensity(xy, ikle):
    '''
    Calculating the total area and the density (total_mesh_area/number_of_meshes) of a Triangular Irregular Network
    :param xy: a numpy array of x and y coordinate
    :param ikle: a tin description of the TIN given by lines of 3 indexes (xy)  corresponding to the 3 nodes f each triangle/mesh
    :return: total_area ,density (total_area/number_of_meshes)
    '''
    total_area = np.sum(0.5 * (np.abs(
        (xy[ikle[:, 1]][:, 0] - xy[ikle[:, 0]][:, 0]) * (xy[ikle[:, 2]][:, 1] - xy[ikle[:, 0]][:, 1]) - (
                xy[ikle[:, 2]][:, 0] - xy[ikle[:, 0]][:, 0]) * (xy[ikle[:, 1]][:, 1] - xy[ikle[:, 0]][:, 1]))))
    return total_area, total_area / (ikle.size // 3)


####################################TEST PART ########################################################################################
def build_hyd_sub_mesh(bshow, nbpointhyd, nbpointsub, seedhyd=None, seedsub=None):
    '''
    Building 2 TIN (Triangular Irregular Network) one hydraulic the other substrate
    :param bshow: if True show using
    :param nbpointhyd: a given number of hydraulic nodes/points
    :param nbpointsub: a given number of substrate nodes/points
    :param seedhyd: a fixed seed for randomisation of hydraulic nodes
    :param seedsub:  a fixed seed for randomisation of substrate nodes
    :return:
        x,y for hydraulic nodes/points,
        TIN description of hydraulic meshes (3 indexes of nodes per line defining a mesh) ,
        x,y for substrate nodes/points,
        TIN description of substrate meshes (3 indexes of nodes per line defining a mesh) ,
        sub_data: substrate data for each substrate mesh
    '''
    if seedhyd != None:
        np.random.seed(seedhyd)
    xyhyd = np.random.rand(nbpointhyd, 2) * 100  # pavé [0,100[X[0,100[
    # print('seedhyd', np.random.get_state()[1][0])
    # TODO supprimer les doublons
    A = dict(vertices=xyhyd)  # A['vertices'].shape  : (4, 2)
    B = tr.triangulate(A)  # type(B)     class 'dict'>
    # eventuellement check si hyd_xy a changé.....
    if bshow:
        tr.compare(plt, A, B)
        plt.show()

    if seedsub != None:
        np.random.seed(seedsub)
    sub_xy = np.random.rand(nbpointsub, 2) * 100  # pavé [0,100[X[0,100[
    # print('seedsub', np.random.get_state()[1][0])
    # TODO supprimer les doublons
    C = dict(vertices=sub_xy)
    D = tr.triangulate(C)
    # eventuellement check si sub_xy a changé.....
    if bshow:
        tr.compare(plt, C, D)
        plt.show()
    if seedsub != None:
        np.random.seed(seedsub)
    datasub = np.random.randint(2, 9, size=(len(D['triangles']), 1))
    datasub = np.hstack((datasub, datasub))

    return B['vertices'], B['triangles'], D['vertices'], D['triangles'], datasub


def build_hyd_data(hyd_xy, hyd_tin, seedhyd1, seedhyd2, seedhyd3):
    '''
    Building hydraulic data for a hydraulic TIN (Triangular Irregular Network)
    :param hyd_xy: x,y for hydraulic nodes/points
    :param hyd_tin: TIN description of hydraulic meshes (3 indexes of nodes per line defining a mesh) ,
    :param seedhyd1: a fixed seed for randomisation of hydraulic nodes
    :param seedhyd2: a fixed seed for randomisation of hydraulic nodes
    :param seedhyd3: a fixed seed for randomisation of hydraulic nodes
    :return:
            hyd_data_node : hydraulic data for each node/point
            iwholeprofile : iwholeprofile: a two columns numpy array describing each hydraulic mesh:
                first column an index corresponding to the original hydraulic TIN (before taking away the dry part for instance)
                2nd column i_split 0 if the hydraulic original mesh have never been partitioned, 1 if it has been partitioned by taking away a dry part
            hyd_data_mesh : hydraulic data for each mesh
    '''
    nbnode = hyd_xy.size // 2
    nbmesh = hyd_tin.size // 3
    iwholeprofile = np.zeros((nbmesh, 2), dtype=np.int64)
    hyd_data_c = np.zeros((nbmesh, 2), dtype=np.float64)
    hyd_data = np.zeros((nbnode, 3), dtype=np.float64)
    iwholeprofile[:, 0] = np.arange(nbmesh)
    if seedhyd1 != None:
        np.random.seed(seedhyd1)
    iwholeprofile[:, 1] = np.random.randint(0, 2, nbmesh)
    if seedhyd2 != None:
        np.random.seed(seedhyd2)
    d2 = np.random.randint(0, 11, nbmesh)
    hyd_data_c[:, 0], hyd_data_c[:, 1] = d2, d2 + 10
    if seedhyd3 != None:
        np.random.seed(seedhyd3)
    d3 = np.random.randint(0, 11, nbnode)
    hyd_data[:, 0], hyd_data[:, 1], hyd_data[:, 2] = d3, d3 + 10, d3 + 20

    return hyd_data, iwholeprofile, hyd_data_c


if __name__ == '__main__':
    '''
    testing the merge program
    '''
    t = 0  # regarding this value different tests can be launched
    if t == 0:  # random nbpointhyd, nbpointsub are the number of nodes/points to be randomly generated respectively for hydraulic and substrate TIN
        nbpointhyd, nbpointsub, seedhyd, seedsub = 5000, 7000, 9, 32
        hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data = build_hyd_sub_mesh(False, nbpointhyd, nbpointsub, seedhyd, seedsub)
    elif t == 1:  # 1 hydraulic mesh  VS 1 substrate mesh
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1]])
        hyd_tin = np.array([[0, 1, 2]])
        sub_xy = np.array([[3, 3], [3, 5], [6, 3]])
        sub_tin = np.array([[0, 1, 2]])
        sub_data = np.array([[2, 2]])
    elif t == 2:  # 1 hydraulic mesh  VS 2 substrate mesh
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1]])
        hyd_tin = np.array([[0, 1, 2]])
        sub_xy = np.array([[3, 3], [3, 5], [6, 3], [3, 1]])
        sub_tin = np.array([[0, 1, 2], [3, 0, 2]])
        sub_data = np.array([[2, 2], [3, 3]])
    elif t == 3:  # 2 hydraulic mesh  VS 4 substrate mesh
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1], [14, 11], [15, 14], [16, 11]])
        hyd_tin = np.array([[0, 1, 2], [3, 4, 5]])
        sub_xy = np.array([[3, 3], [3, 5], [6, 3], [3, 1], [13, 13], [13, 15], [16, 13], [13, 11]])
        sub_tin = np.array([[0, 1, 2], [3, 0, 2], [4, 5, 6], [7, 4, 6]])
        sub_data = np.array([[2, 2], [3, 3], [4, 4], [5, 5]])
    elif t == 4:  # 1 hydraulic mesh  VS 1 substrate mesh containing the hydraulic mesh
        hyd_xy = np.array([[8, 5], [10, 5], [8, 7]])
        hyd_tin = np.array([[0, 1, 2]])
        sub_xy = np.array([[7, 4], [12, 4], [7, 10]])
        sub_tin = np.array([[0, 1, 2]])
        sub_data = np.array([[7, 7]])
    elif t == 5:  # 1 hydraulic mesh  VS 1 substrate mesh 1 substrate node inside the hydraulic mesh
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1]])
        hyd_tin = np.array([[0, 1, 2]])
        sub_xy = np.array([[4, 5], [6, 5], [5, 2]])
        sub_tin = np.array([[0, 1, 2]])
        sub_data = np.array([[2, 2]])
    elif t == 6:  # 2 hydraulic mesh  VS 2 substrate mesh 1 substrate node inside each hydraulic mesh
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1], [14, 11], [15, 14], [16, 11]])
        hyd_tin = np.array([[0, 1, 2], [3, 4, 5]])
        sub_xy = np.array([[4, 5], [6, 5], [5, 2], [14, 15], [16, 15], [15, 12]])
        sub_tin = np.array([[0, 1, 2], [3, 4, 5]])
        sub_data = np.array([[2, 2], [3, 3]])
    elif t == 7:  # Special case : 2 hydraulic mesh  VS 2 substrate mesh superimposed on the hydraulic ones
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1], [14, 11], [15, 14], [16, 11]])
        hyd_tin = np.array([[0, 1, 2], [3, 4, 5]])
        sub_xy =  np.array([[4, 1], [5, 4], [6, 1], [14, 11], [15, 14], [16, 11]])
        sub_tin = np.array([[0, 1, 2], [3, 4, 5]])
        sub_data = np.array([[2, 2], [3, 3]])
    elif t == 8:  # Specials cases : 3 hydraulic mesh  VS 3 substrate mesh : some points in common
        hyd_xy = np.array([[4, 1], [5, 4], [6, 1],[9, 1], [10, 4], [11, 1], [14, 11], [15, 14], [16, 11]])
        hyd_tin = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8]])
        sub_xy =  np.array([[5, 4], [5, 7], [7, 4],[10, 1], [10, 4], [12, 1], [15, 11], [15, 14], [16, 11]])
        sub_tin = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8]])
        sub_data = np.array([[2, 2], [3, 3],[4, 4]])
    elif t == 9:  # Special case : 1 hydraulic mesh  VS 2 substrate mesh with a numerical problem
        hyd_xy = np.array([[1430257.89333269, 7216692.15461854],[1430257.89333269, 7216691.46664975],[1430258.11039261, 7216692.24958983]])
        hyd_tin = np.array([[0, 1, 2]])
        sub_xy =  np.array([[1430258.1087, 7216692.248 ],[1430258.2823, 7216688.978 ],[1430259.067 , 7216692.7716],[1430258.1087, 7216692.248 ],[1430259.067 , 7216692.7716],[1430256.2278, 7216692.0946]])
        sub_tin = np.array([[0, 1, 2], [3, 4, 5]])
        sub_data = np.array([[2, 2], [3, 3]])
    defautsub = np.array([1, 1])
    coeffgrid = 1 / 2  # plus coeffgrid est grand plus la grille  de reperage sera fine

    hyd_data, iwholeprofile, hyd_data_c = build_hyd_data(hyd_xy, hyd_tin, 7, 22, 33)
    ti = datetime.now()
    merge_xy1, merge_data_node, merge_tin1, iwholeprofilemerge, merge_data_mesh, merge_data_sub_mesh = merge(hyd_xy,
                                                                                                             hyd_data,
                                                                                                             hyd_tin,
                                                                                                             iwholeprofile,
                                                                                                             hyd_data_c,
                                                                                                             sub_xy,
                                                                                                             sub_tin,
                                                                                                             sub_data,
                                                                                                             defautsub,
                                                                                                             coeffgrid)

    # areahyd,densityhyd=tinareadensity(hyd_xy,hyd_tin)
    # areamerge, densitymerge = tinareadensity(merge_xy1,merge_tin1)
    # print(areahyd,densityhyd,areamerge, densitymerge)

    # print(merge_xy1,merge_tin1,merge_data_sub_mesh)

    # print(sub_data[:,0])
    # print(np.array(merge_data_sub_mesh)[:,0])

    tf = datetime.now()
    print('finish', tf - ti)

    plot_to_check_mesh_merging(hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data[:, 0], merge_xy1,
                               merge_tin1, merge_data_sub_mesh[:, 0])
