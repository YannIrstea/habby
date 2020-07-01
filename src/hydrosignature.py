import numpy as np

def hydrosignature_calculation(classhv,hyd_xy_node,hyd_tin,hyd_hv_node, hyd_data_node=None,  iwholeprofile=None, hyd_data_mesh=None, hyd_data_sub_mesh=None):
    """
    Merging an hydraulic TIN (Triangular Irregular Network) and a substrate TIN to obtain a merge TIN
    (based on the hydraulic one) by partitionning each hydraulic triangle/mesh if necessary into smaller
    triangles/meshes that contain a substrate from the substrate TIN or a default substrate. Additional nodes inside
    or on the edges of an hydraulic mesh will be given hydraulic data by interpolation of the hydraulic data from the
    hydraulic mesh nodes.Flat hydraulic or substrates triangles will not been taken inot account.
    TAKE CARE during the merge a translation is done to minimise numericals problems
     Using numpy arrays as entry and returning numpy arrays.
    :param classhv a list of two lists [[h0,h1,...,hn] , [v0,v1,...,vm]] defining the hydrosignature grid
    :param hyd_xy_node: The x,y nodes coordinates of a hydraulic TIN (Triangular Irregular Network)
    :param hyd_tin: The hydraulic TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a
            mesh/triangle
    :param hyd_hv_node: the wather depth, mean velocity of the verticals/nodes of a hydraulic TIN
    :param hyd_data_node: The hydraulic data of the hydraulic nodes (eg : z, temperature...)

    :param iwholeprofile: A two columns numpy array describing each hydraulic mesh:
            first column an index corresponding to the original hydraulic TIN (before taking away the dry part for
            instance) 2nd column i_split 0 if the hydraulic original mesh have never been partitioned, 1 if it has been
            partitioned by taking away a dry part
    :param hyd_data_mesh: hydraulic data affected to each hydraulic mesh
    :param hyd_data_sub_mesh  substrate data affected to each  mesh
    :return:
            hs_xy : the x,y nodes coordinates of a hydraulic TIN
            hs_data_node : the hydraulic data of the hs nodes (eg : z, wather depth, mean velocity...)
            hs_tin : the hs TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a
                        mesh/triangle
            iwholeprofilehs : similar to iwholeprofile describing each hydraulic mesh
                           i_split can also have the values :  2 if the mesh has been partioned by the merge : 3  if the mesh has been partioned previously by taking away a dry part and also a second time by the merge
                           a third column is added i_subdefaut marking by the value 1 when the defaut substrate has been assigned to the mesh, 0 otherwise
            hs_data_mesh : hydraulic data affected to each hs mesh
            hs_data_sub_mesh : substrate data affected to hs merge mesh
    """
    uncertainty=0.01 #a checking parameter for the algorithm
    translationxy = np.min(hyd_xy_node, axis=0)
    hyd_xy_node -= translationxy




    hs_xy_node=[]
    cl_h, cl_v, nb_cl_h, nb_cl_v=checkhydrosigantureclasses(classhv)

    areameso = np.zeros((nb_cl_h, nb_cl_v), dtype=np.int64)
    volumemeso = np.zeros((nb_cl_h, nb_cl_v), dtype=np.int64)


    for i in range(hyd_tin.size // 3):  # even if one single triangle for hyd_tin
        xyo, xya, xyb = hyd_xy_node[hyd_tin[i][0]], hyd_xy_node[hyd_tin[i][1]], hyd_xy_node[hyd_tin[i][2]]
        axy, bxy = xya - xyo, xyb - xyo
        deta = bxy[1] * axy[0] - bxy[0] * axy[1]
        if deta == 0:
            print('before hs an hydraulic triangle have an area=0 ')
        else:
            poly1={'x': [hyd_xy_node[hyd_tin[i][0]][0],hyd_xy_node[hyd_tin[i][1]][0],hyd_xy_node[hyd_tin[i][2]][0]] ,
                   'y': [hyd_xy_node[hyd_tin[i][0]][1], hyd_xy_node[hyd_tin[i][1]][1], hyd_xy_node[hyd_tin[i][2]][1]],
                'h': [hyd_hv_node[hyd_tin[i][0]][0],hyd_hv_node[hyd_tin[i][1]][0],hyd_hv_node[hyd_tin[i][2]][0]] ,
                   'v': [hyd_hv_node[hyd_tin[i][0]][1],hyd_hv_node[hyd_tin[i][1]][1],hyd_hv_node[hyd_tin[i][2]][1]] }
            area1, volume1 = areavolumepoly(poly1, 0, 1, 2)
            area12,volume12=0,0
            for j2 in range(nb_cl_h):
                if not(poly1['h'][0]==cl_h[j2+1] and poly1['h'][1]==cl_h[j2+1] and poly1['h'][2]==cl_h[j2+1] and j2+1!=nb_cl_h ):
                    poly2 = {'x': [], 'y': [], 'h': [], 'v': []}
                    ia ,ib,nbeltpoly2=0,1,0
                    while ia<=2:
                        if np.sign(poly1['h'][ia]-cl_h[j2])*np.sign(poly1['h'][ia]-cl_h[j2+1])!=1:
                            nbeltpoly2+=1
                            poly2['x'].append(poly1['x'][ia]);poly2['y'].append(poly1['y'][ia])
                            poly2['h'].append(poly1['h'][ia]);poly2['v'].append(poly1['v'][ia])
                        if np.sign(cl_h[j2]-poly1['h'][ia])*np.sign(cl_h[j2]-poly1['h'][ib])==-1:
                            nbeltpoly2 += 1
                            poly2['x'].append(interpol0(cl_h[j2],poly1['h'][ia],poly1['x'][ia],poly1['h'][ib],poly1['x'][ib]))
                            poly2['y'].append(
                                interpol0(cl_h[j2], poly1['h'][ia], poly1['y'][ia], poly1['h'][ib], poly1['y'][ib]))
                            poly2['h'].append(cl_h[j2])
                            poly2['v'].append(
                                interpol0(cl_h[j2], poly1['h'][ia], poly1['v'][ia], poly1['h'][ib], poly1['v'][ib]))
                        if np.sign(cl_h[j2+1]-poly1['h'][ia])*np.sign(cl_h[j2+1]-poly1['h'][ib])==-1:
                            nbeltpoly2 += 1
                            poly2['x'].append(interpol0(cl_h[j2+1],poly1['h'][ia],poly1['x'][ia],poly1['h'][ib],poly1['x'][ib]))
                            poly2['y'].append(
                                interpol0(cl_h[j2+1], poly1['h'][ia], poly1['y'][ia], poly1['h'][ib], poly1['y'][ib]))
                            poly2['h'].append(cl_h[j2+1])
                            poly2['v'].append(
                                interpol0(cl_h[j2+1], poly1['h'][ia], poly1['v'][ia], poly1['h'][ib], poly1['v'][ib]))
                            if poly1['h'][ib]<poly1['h'][ia] and np.sign(cl_h[j2]-poly1['h'][ia])*np.sign(cl_h[j2]-poly1['h'][ib])==-1:
                                poly2['x'][nbeltpoly2-2],poly2['x'][nbeltpoly2-1]=poly2['x'][nbeltpoly2-1],poly2['x'][nbeltpoly2-2]
                                poly2['y'][nbeltpoly2 - 2], poly2['y'][nbeltpoly2 - 1] = poly2['y'][nbeltpoly2 - 1], \
                                                                                         poly2['y'][nbeltpoly2 - 2]
                                poly2['h'][nbeltpoly2 - 2], poly2['h'][nbeltpoly2 - 1] = poly2['h'][nbeltpoly2 - 1], \
                                                                                         poly2['h'][nbeltpoly2 - 2]
                                poly2['v'][nbeltpoly2 - 2], poly2['v'][nbeltpoly2 - 1] = poly2['v'][nbeltpoly2 - 1], \
                                                                                         poly2['v'][nbeltpoly2 - 2]
                        ia+=1;ib+=1
                        if ib==3:
                            ib=0
                    if nbeltpoly2>5:
                        print("hydrosignature : polygonation contrary to the YLC theory while in phase poly2 MAJOR BUG !!!")
                    elif  nbeltpoly2>=3:

                        for k2 in range(1,nbeltpoly2-1):
                            area2, volume2 = areavolumepoly(poly1, 0, k2, k2+1)
                            area12+=area2
                            volume12+=volume2
                            area23, volume23 = 0, 0
                            for j3 in range(nb_cl_v):
                                if not (poly2['v'][0] == cl_v[j3 + 1] and poly2['v'][k2] == cl_v[j3 + 1] and poly2['v'][
                                    k2+1] == cl_v[j3 + 1] and j3 + 1 != nb_cl_v):
                                    poly3 = {'x': [], 'y': [], 'h': [], 'v': []}
                                    ic, id, nbeltpoly3 = 0, k2, 0
                                    while ic <= k2+1:
                                        if np.sign(poly2['v'][ic] - cl_v[j3]) * np.sign(
                                                poly2['v'][ic] - cl_v[j3 + 1]) != 1:
                                            nbeltpoly3 += 1
                                            poly3['x'].append(poly2['x'][ic]);
                                            poly3['y'].append(poly2['y'][ic])
                                            poly3['h'].append(poly2['h'][ic]);
                                            poly3['v'].append(poly2['v'][ic])
                                        if np.sign(cl_v[j3] - poly2['v'][ic]) * np.sign(
                                                cl_v[j3] - poly2['v'][id]) == -1:
                                            nbeltpoly3 += 1
                                            poly3['x'].append(
                                                interpol0(cl_v[j3], poly2['v'][ic], poly2['x'][ic], poly2['v'][id],
                                                          poly2['x'][id]))
                                            poly3['y'].append(
                                                interpol0(cl_v[j3], poly2['v'][ic], poly2['y'][ic], poly2['v'][id],
                                                          poly2['y'][id]))
                                            poly3['v'].append(cl_v[j3])
                                            poly3['h'].append(
                                                interpol0(cl_v[j3], poly2['v'][ic], poly2['h'][ic], poly2['v'][id],
                                                          poly2['h'][id]))
                                        if np.sign(cl_v[j3 + 1] - poly2['v'][ic]) * np.sign(
                                                cl_v[j3 + 1] - poly2['v'][id]) == -1:
                                            nbeltpoly3 += 1
                                            poly3['x'].append(
                                                interpol0(cl_v[j3 + 1], poly2['v'][ic], poly2['x'][ic], poly2['v'][id],
                                                          poly2['x'][id]))
                                            poly3['y'].append(
                                                interpol0(cl_v[j3 + 1], poly2['v'][ic], poly2['y'][ic], poly2['v'][id],
                                                          poly2['y'][id]))
                                            poly3['v'].append(cl_v[j3 + 1])
                                            poly3['h'].append(
                                                interpol0(cl_v[j3 + 1], poly2['v'][ic], poly2['h'][ic], poly2['v'][id],
                                                          poly2['h'][id]))
                                            if poly2['v'][id] < poly2['v'][ic] and np.sign(
                                                    cl_v[j3] - poly2['v'][ic]) * np.sign(
                                                    cl_v[j3] - poly2['v'][id]) == -1:
                                                poly3['x'][nbeltpoly3 - 2], poly3['x'][nbeltpoly3 - 1] = poly3['x'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['x'][
                                                                                                             nbeltpoly3 - 2]
                                                poly3['y'][nbeltpoly3 - 2], poly3['y'][nbeltpoly3 - 1] = poly3['y'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['y'][
                                                                                                             nbeltpoly3 - 2]
                                                poly3['h'][nbeltpoly3 - 2], poly3['h'][nbeltpoly3 - 1] = poly3['h'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['h'][
                                                                                                             nbeltpoly3 - 2]
                                                poly3['v'][nbeltpoly3 - 2], poly3['v'][nbeltpoly3 - 1] = poly3['v'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['v'][
                                                                                                             nbeltpoly3 - 2]
                                        if ic ==0:
                                            ic=k2
                                        else:
                                            ic+=1
                                        if id == k2:
                                            id = k2+1
                                        elif id==k2+1:
                                            id=0
                                    if nbeltpoly3 > 5:
                                        print(
                                            "hydrosignature : polygonation contrary to the YLC theory while in phase poly3 MAJOR BUG !!!")
                                    elif nbeltpoly3 >= 3:
                                        for k3 in range(1, nbeltpoly3 - 1):
                                            area3,volume3=areavolumepoly(poly3,0,k3,k3+1)
                                            areameso[j2][j3]+=area3;area23+=area3
                                            volumemeso[j2][j3]+=volume3;volume23+=volume3
                        #checking the partitioning poly3 checking area volume nothing lost by the algorithm

                        if area2!=0:
                            if np.abs(area23-area2)/area2> uncertainty and area2> uncertainty:
                                print('Uncertainty allowed on the area calculation, exceeded while in phase poly3 BUG ???')
                        if volume2 != 0:
                            if np.abs(volume23 - volume2) / volume2 > uncertainty and volume2 > uncertainty:
                                print('Uncertainty allowed on the volume calculation, exceeded while in phase poly3 BUG ???')
        #checking the partitioning poly2 checking area volume nothing lost by the algorithm
        if area1 != 0:
            if np.abs(area12 - area1) / area1 > uncertainty and area1 > uncertainty:
                print('Uncertainty allowed on the area calculation, exceeded while in phase poly2 BUG ???')
        if volume1 != 0:
            if np.abs(volume12 - volume1) / volume1 > uncertainty and volume1 > uncertainty:
                print('Uncertainty allowed on the volume calculation, exceeded while in phase poly2 BUG ???')














    hs_xy_node +=translationxy
    hyd_xy_node +=translationxy
    return hs_xy_node, hs_data_node, hs_tin, iwholeprofilehs, np.array(hs_data_mesh),hs_data_sub_mesh




def areavolumepoly(poly,ia,ib,ic):
    area=np.abs((poly[x][ib]-poly[x][ia])*(poly[y][ic]-poly[y][ia])-(poly[x][ic]-poly[x][ia])*(poly[y][ib]-poly[y][ia]))/2
    volume=area*np.mean((poly[h][ia],poly[h][ib],poly[h][ic]))
    return area,volume



def interpol0(x,xa,ya,xb,yb):
    return (x-xa)*(yb-ya)/(xb-xa)+ya

def checkhydrosigantureclasses(classhv):
    '''
    checking the validity of the definition of the two classes depth and velocity  defining the hydrosignature grid
    :param classhv: a list of two lists [[h0,h1,...,hn] , [v0,v1,...,vm]] defining the hydrosignature grid
    :return cl_h= [h0,h1,...,hn],cl_v=[v0,v1,...,vm] ,nb_cl_h= n,nb_cl_v=m
    '''
    if len(classhv) !=2:
        print("hydrosignature : there is not 2 classes h,v found")
    if isinstance(classhv[0], list)==False or isinstance(classhv[1], list)==False:
        print("hydrosignature : we have not 2 classes h,v found")

    cl_h,cl_v=classhv[0],classhv[1]
    nb_cl_h,nb_cl_v=len(cl_h)-1,len(cl_v)-1
    if nb_cl_h<1 or nb_cl_v<1:
        print("hydrosignature : a classe h,v found have less than 2 elements")
    if len(set(cl_h))!=nb_cl_h or len(set(cl_v))!=nb_cl_v:
        print("hydrosignature : there are duplicates in the classes  h,v")
    cl_h2, cl_v2=list(cl_h),list(cl_v)
    if cl_h2.sort()!=cl_h or cl_v2.sort()!=cl_v:
        print("hydrosignature : there  the classes  h,v are not sorted")
    return cl_h,cl_v,nb_cl_h,nb_cl_v




if __name__ == '__main__':
    '''
    testing the hydrosignature program
    '''