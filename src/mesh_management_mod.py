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
import numpy as np


def quadrangles_to_triangles(ikle4, xy, z, h, v):
    """
    this fucntion call the quadrangles hydraulic description and transforme it into a triangular description
    a new node is added in the center of each quadrangle, and we take care for the partially wet quadrangle
    for the calculation of the depth and the velocity of theses new points.


    :param ikle4: the connectivity table of the quadrangles
    :param xy: the coordinates of the nodes
    :param z: the bottom altitude of the nodes
    :param h: the height of water of the nodes
    :param v: the mean velocity of the nodes
    :return: ikle3 the connectivity table of the triangles, and the 'coordinates' of the additional nodes xy,z,h,v multilines numpy array
    """
    # TODO verifier que len(ikle4)!=0
    # TODO verifier que les elements des noeuds ont la même longueur len(xy)=len(v)=len(z)=len(h)
    nbnodes0 = len(xy)
    nbnodes = nbnodes0
    ikle3 = np.empty(shape=[0, 3], dtype=int)
    # transforming v<0 in abs(v) ; hw<0 in hw=0 and where hw=0 v=0
    v = np.abs(v)
    hwneg = np.where(h < 0)
    h[hwneg] = 0
    hwnul = np.where(h == 0)
    v[hwnul] = 0
    # essential for return value data in multiple lines
    if z.ndim == 1:
        z = z.reshape(np.size(z), 1)
    if h.ndim == 1:
        h = h.reshape(np.size(h), 1)
    if v.ndim == 1:
        v = v.reshape(np.size(v), 1)

    for i in range(len(ikle4)):
        nbnodes += 1
        q0, q1, q2, q3 = ikle4[i][0], ikle4[i][1], ikle4[i][2], ikle4[i][3]
        ikle3 = np.append(ikle3, np.array([[q0, nbnodes - 1, q3], [q0, q1, nbnodes - 1],
                                           [q1, q2, nbnodes - 1], [nbnodes - 1, q2, q3]]),
                          axis=0)
        xyi = np.mean(xy[[q0, q1, q2, q3], :], axis=0)
        zi = np.mean(z[[q0, q1, q2, q3], :], axis=0)
        hi = np.mean(h[[q0, q1, q2, q3], :], axis=0)
        vi = np.mean(v[[q0, q1, q2, q3], :], axis=0)
        xy = np.append(xy, np.array([xyi]), axis=0)
        z = np.append(z, np.array([zi]), axis=0)
        h = np.append(h, np.array([hi]), axis=0)
        v = np.append(v, np.array([vi]), axis=0)
        # chek whether the quadrangle is partially wet
        h4 = h[[q0, q1, q2, q3]]
        bhw = (h4 > 0).astype(np.int)
        n4_type = np.sum(bhw)  # 0=dry 4=wet 1,2 or 3 = partially wet
        if n4_type != 0 and n4_type != 4:  # the quadrangle is partially wet
            hi, vi = 0, 0
            z4 = z[[q0, q1, q2, q3]]
            v4 = v[[q0, q1, q2, q3]]
            for j in range(2):  # working successively on the 2 diagonals/ edges
                za, ha, va = z4[j], h4[j], v4[j]
                zb, hb, vb = z4[j + 2], h4[j + 2], v4[j + 2]
                if ha != 0 and hb != 0:
                    hi += (ha + hb) / 2
                    vi += (va + vb) / 2
                elif ha == 0 and hb == 0:
                    pass
                else:
                    if ha == 0:  # swap A & B
                        za, ha, va, zb, hb, vb = zb, hb, vb, za, ha, va
                    # at this step hwB/hb=0
                    if za + ha >= zb or za >= zb:  # it is possible in that case that the hydraulic given is incorrect
                        hi += (ha + hb) / 2
                        vi += (va + vb) / 2
                    else:  # ha/(zb-za)<1
                        lama = ha / (zb - za)
                        if lama <= 0.5:  # the middle/center is dry
                            pass
                        else:
                            hi += ha - (zb - za) / 2
                            vi += hi * va / ha
            # affecting the mean result from the 2 diagonals/ edges
            h[nbnodes - 1] = hi / 2
            v[nbnodes - 1] = vi / 2
    return ikle3, xy[nbnodes0 - nbnodes:, :], z[nbnodes0 - nbnodes:], h[nbnodes0 - nbnodes:], v[nbnodes0 - nbnodes:]

