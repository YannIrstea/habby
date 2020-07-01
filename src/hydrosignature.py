import numpy as np

def hydrosignature_calculation(classhv,hyd_tin,hyd_xy_node,hyd_hv_node, hyd_data_node=None,  iwholeprofile=None, hyd_data_mesh=None, hyd_data_sub_mesh=None):
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
    g = 9.80665 #value of gravitational acceleration on Earth [m**2/s]
    uncertainty=0.01 #a checking parameter for the algorithm
    translationxy = np.min(hyd_xy_node, axis=0)
    hyd_xy_node -= translationxy

    # calculating the global hydraulic part of the hydrosignature
    #aire_totale	volume_total	hauteur_moyenne	vitesse_moyenne	Froude_moyen	hauteur_min	hauteur_max	vitesse_min	vitesse_max
    narea=0.5 * (np.abs(
        (hyd_xy_node[hyd_tin[:, 1]][:, 0] - hyd_xy_node[hyd_tin[:, 0]][:, 0]) * (hyd_xy_node[hyd_tin[:, 2]][:, 1] - hyd_xy_node[hyd_tin[:, 0]][:, 1]) - (
                hyd_xy_node[hyd_tin[:, 2]][:, 0] - hyd_xy_node[hyd_tin[:, 0]][:, 0]) * (hyd_xy_node[hyd_tin[:, 1]][:, 1] - hyd_xy_node[hyd_tin[:, 0]][:, 1])))

    nhmean=(hyd_hv_node[hyd_tin[:, 0]][:, 0]+hyd_hv_node[hyd_tin[:, 1]][:, 0]+hyd_hv_node[hyd_tin[:, 2]][:, 0])/3
    nvolume=narea*nhmean
    nvmean=(hyd_hv_node[hyd_tin[:, 0]][:, 1]+hyd_hv_node[hyd_tin[:, 1]][:, 1]+hyd_hv_node[hyd_tin[:, 2]][:, 1])/3
    #nfroudemean=np.abs(nvmean)/np.sqrt(np.abs(nhmean)*g)
    f0=np.abs(hyd_hv_node[hyd_tin[:, 0]][:, 1]) / np.sqrt(np.abs(hyd_hv_node[hyd_tin[:, 0]][:, 0]) * g)
    f1=np.abs(hyd_hv_node[hyd_tin[:, 1]][:, 1]) / np.sqrt(np.abs(hyd_hv_node[hyd_tin[:, 1]][:, 0]) * g)
    f2=np.abs(hyd_hv_node[hyd_tin[:, 2]][:, 1]) / np.sqrt(np.abs(hyd_hv_node[hyd_tin[:, 2]][:, 0]) * g)
    f0[np.isnan(f0)]=0
    f1[np.isnan(f1)] = 0
    f2[np.isnan(f2)] = 0
    nfroudemean = np.mean((f0,f1,f2))

    total_area = np.sum(narea)
    total_volume = np.sum(nvolume)
    mean_depth=total_volume/total_area
    mean_velocity= np.sum(nvolume*np.abs(nvmean))/total_volume
    mean_froude =np.sum(nvolume*np.abs(nfroudemean))/total_volume
    nhused=np.hstack((hyd_hv_node[hyd_tin[:, 0]][:, 0],hyd_hv_node[hyd_tin[:, 1]][:, 0],hyd_hv_node[hyd_tin[:, 2]][:, 0]))
    nvused=np.hstack((hyd_hv_node[hyd_tin[:, 0]][:, 1],hyd_hv_node[hyd_tin[:, 1]][:, 1],hyd_hv_node[hyd_tin[:, 2]][:, 1]))
    min_depth=np.min(nhused)  #np.min(hyd_hv_node[:, 0]) not used because some node cannot be called by the tin
    max_depth=np.max(nhused)
    min_velocity=np.min(nvused)
    max_velocity=np.max(nvused)


    hs_xy_node=[]
    bok,cl_h, cl_v, nb_cl_h, nb_cl_v=checkhydrosigantureclasses(classhv)
    #checking wether an hydrosignature can be calculated
    if bok==False:
        print("there is a problem in the class definition hydrosignature cannot be calculated")
        return
    if min_depth<np.min(cl_h) or max_depth>np.max(cl_h):
        print("there is a problem in the class definition  fo h some hydraulic values are off the definition hydrosignature cannot be calculated")
        return
    if min_velocity<np.min(cl_v) or max_velocity>np.max(cl_v):
        print("there is a problem in the class definition  fo v some hydraulic values are off the definition hydrosignature cannot be calculated")
        return

    areameso = np.zeros((nb_cl_h, nb_cl_v), dtype=np.float64)
    volumemeso = np.zeros((nb_cl_h, nb_cl_v), dtype=np.float64)


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
                        return
                    elif  nbeltpoly2>=3:

                        for k2 in range(1,nbeltpoly2-1):
                            area2, volume2 = areavolumepoly(poly2, 0, k2, k2+1)
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
                                        return
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

    #calculating percentages
    hsarea=100*areameso/np.sum(areameso)
    hsvolume = 100 * volumemeso / np.sum(volumemeso)





    hyd_xy_node += translationxy

    #TODO necessary for Horizontal Ramping Rate calculation
    # hs_xy_node +=translationxy
    # return hs_xy_node, hs_data_node, hs_tin, iwholeprofilehs, hs_data_mesh,hs_data_sub_mesh

    return total_area,total_volume,mean_depth,mean_velocity,mean_froude,min_depth,max_depth,min_velocity,max_velocity,hsarea,hsvolume

def hscomparison(classhv1,hs1,classhv2,hs2,k1=1,k2=1):
    #checking validity of the operation
    bok = False
    cl_h1, cl_v1 = classhv1[0], classhv1[1]
    cl_h2, cl_v2 = classhv2[0], classhv2[1]
    if len(cl_h1)!=len(cl_h2) or len(cl_h1)!=len(cl_h2):
        print("hydrosignatures comparison classes definitions must be identical to perform comparison")
        return
    if len([i for i, j in zip(cl_h2, cl_h1) if i != j]) != 0 or len([i for i, j in zip(cl_v2, cl_v1) if i != j]) != 0:
        print("hydrosignatures comparison classes definitions must be identical to perform comparison")
        return
    nb_cl_h, nb_cl_v = len(cl_h1) - 1, len(cl_v1) - 1
    if hs1.shape!=(nb_cl_h, nb_cl_v ) or hs2.shape!=(nb_cl_h, nb_cl_v ):
        print("hydrosignatures comparison at least one of the two hydrosignature to compare is not coherent with the classes definitions impossible to perform comparison")
        return
    hsf10 = np.zeros((nb_cl_h+2, nb_cl_v+2), dtype=np.float64)
    hsf20 = np.zeros((nb_cl_h + 2, nb_cl_v + 2), dtype=np.float64)
    hsf1 = np.zeros((nb_cl_h+2, nb_cl_v+2), dtype=np.float64)
    hsf2 = np.zeros((nb_cl_h + 2, nb_cl_v + 2), dtype=np.float64)
    hsf10[1:nb_cl_h + 1, 1:nb_cl_v + 1] = hs1
    hsf20[1:nb_cl_h + 1, 1:nb_cl_v + 1] = hs2
    for ih in range(nb_cl_h+2):
        for iv in range(nb_cl_v+2):
            hsf1[ih][iv]=hsf10[ih][iv]*k1;hsf2[ih][iv] = hsf20[ih][iv] * k1
            if ih > 0 and iv > 0:
                hsf1[ih][iv] += hsf10[ih - 1][iv - 1] * k2
                hsf2[ih][iv] += hsf20[ih - 1][iv - 1] * k2
            if iv > 0:
                hsf1[ih][iv] += hsf10[ih][iv - 1] * k2
                hsf2[ih][iv] += hsf20[ih][iv - 1] * k2
            if ih < nb_cl_h + 1 and iv > 0:
                hsf1[ih][iv] += hsf10[ih + 1][iv - 1] * k2
                hsf2[ih][iv] += hsf20[ih + 1][iv - 1] * k2
            if ih < nb_cl_h + 1:
                hsf1[ih][iv] += hsf10[ih + 1][iv] * k2
                hsf2[ih][iv] += hsf20[ih + 1][iv] * k2
            if ih < nb_cl_h + 1 and iv < nb_cl_v + 1:
                hsf1[ih][iv] += hsf10[ih + 1][iv + 1] * k2
                hsf2[ih][iv] += hsf20[ih + 1][iv + 1] * k2
            if iv < nb_cl_v + 1:
                hsf1[ih][iv] += hsf10[ih][iv + 1] * k2
                hsf2[ih][iv] += hsf20[ih][iv + 1] * k2
            if ih > 0 and iv < nb_cl_v + 1:
                hsf1[ih][iv] += hsf10[ih - 1][iv + 1] * k2
                hsf2[ih][iv] += hsf20[ih - 1][iv + 1] * k2
            if ih > 0:
                hsf1[ih][iv] += hsf10[ih - 1][iv] * k2
                hsf2[ih][iv] += hsf20[ih - 1][iv] * k2
    hsf1 = hsf1 / (k1 + 8 * k2)
    hsf2 = hsf2 / (k1 + 8 * k2)
    hsc=np.sum(np.abs(hsf1-hsf2))/2


    bok = True
    return bok, hsc

def hsexporttxt(pathexport,total_area,total_volume,mean_depth,mean_velocity,mean_froude,min_depth,max_depth,min_velocity,max_velocity,hsarea,hsvolume):
    return


def areavolumepoly(poly,ia,ib,ic):
    area=np.abs((poly['x'][ib]-poly['x'][ia])*(poly['y'][ic]-poly['y'][ia])-(poly['x'][ic]-poly['x'][ia])*(poly['y'][ib]-poly['y'][ia]))/2
    volume=area*np.mean((poly['h'][ia],poly['h'][ib],poly['h'][ic]))
    return area,volume



def interpol0(x,xa,ya,xb,yb):
    return (x-xa)*(yb-ya)/(xb-xa)+ya

def checkhydrosigantureclasses(classhv):
    '''
    checking the validity of the definition of the two classes depth and velocity  defining the hydrosignature grid
    :param classhv: a list of two lists [[h0,h1,...,hn] , [v0,v1,...,vm]] defining the hydrosignature grid
    :return cl_h= [h0,h1,...,hn],cl_v=[v0,v1,...,vm] ,nb_cl_h= n,nb_cl_v=m
    '''
    bok=True
    if len(classhv) !=2:
        print("hydrosignature : there is not 2 classes h,v found")
    if isinstance(classhv[0], list)==False or isinstance(classhv[1], list)==False:
        print("hydrosignature : we have not 2 classes h,v found")

    cl_h,cl_v=classhv[0],classhv[1]
    nb_cl_h,nb_cl_v=len(cl_h)-1,len(cl_v)-1
    if nb_cl_h<1 or nb_cl_v<1:
        print("hydrosignature : a classe h,v found have less than 2 elements")
        bok = False
    if len(set(cl_h))-1!=nb_cl_h or len(set(cl_v))-1!=nb_cl_v:
        print("hydrosignature : there are duplicates in the classes  h,v")
        bok = False
    cl_h2, cl_v2=list(cl_h),list(cl_v)
    cl_h2.sort();cl_v2.sort()
    if len([i for i,j in zip(cl_h2,cl_h) if i!=j])!=0 or len([i for i,j in zip(cl_v2,cl_v) if i!=j])!=0 :
        print("hydrosignature : the classes  h,v are not sorted")
        bok = False
    return bok,cl_h,cl_v,nb_cl_h,nb_cl_v




if __name__ == '__main__':
    '''
    testing the hydrosignature program
    '''
    t = 0  # regarding this value different tests can be launched
    if t == 0:  # random nbpointhyd, nbpointsub are the number of nodes/points to be randomly generated respectively for hydraulic and substrate TIN
        classhv=[[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 3],[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 5]]
        hyd_tin=np.array([[0,1,3],[0,3,4],[1,2,3],[3,4,6],[3,6,7],[4,5,6]])
        hyd_xy_node=np.array([[821128.213280755,1867852.71720679],[821128.302459342,1867853.34262438],[821128.314753232,1867854.93690708],[821131.385434587,1867854.6662084],[821132.187889633,1867852.67553172],[821136.547596803,1867851.73984275],[821136.717311027,1867853.21858062],[821137.825096539,1867853.68]])
        hyd_hv_node=np.array([[1.076,0.128],[0.889999985694885,0.155],[0,0],[0,0],[0.829999983310699,0.145],[1.127,0.143],[0.600000023841858,0.182],[0,0]])

    total_area,total_volume,mean_depth,mean_velocity,mean_froude,min_depth,max_depth,min_velocity,max_velocity,hsarea,hsvolume=hydrosignature_calculation(classhv, hyd_tin, hyd_xy_node, hyd_hv_node)
    print(total_area,total_volume,mean_depth,mean_velocity,mean_froude,min_depth,max_depth,min_velocity,max_velocity,hsarea,hsvolume)
    print()
    print()
    bok, hsc=hscomparison(classhv,hsarea,classhv,hsvolume)
    print(hsc)

