
import numpy as np
import matplotlib.pyplot as plt
import triangle as tr
import math

#for testing
from datetime import datetime
import plot_merge_check




def merge (xyhyd,iklehyd,xysub,iklesub,datasub,defautsub,coeffgrid):
    gridelt=griddef(xyhyd, xysub,iklehyd,iklesub,coeffgrid) #building the grid
    # print(gridelt)
    # print ("titi")
    celltriangleindexsub,celltrianglelistsub=gridikle(xysub, iklesub, gridelt) #indexing the substrate ikle (list of mesh/triangles) in reference to the grid
    decalnewpointmerge=0
    xymerge=[]
    iklemerge=[]
    datasubmerge=[]
    xymergepointlinkstohydr=[]
    #merging each hydraulic mesh/triangle with the substrate mesh/triangles that can be found in the same part of the grid
    for i in range(iklehyd.size // 3):  # even if one single triangle for iklehyd
        xyo,xya,xyb=xyhyd[iklehyd[i][0]], xyhyd[iklehyd[i][1]], xyhyd[iklehyd[i][2]]
        axy,bxy=xya-xyo,xyb-xyo
        deta=bxy[1]*axy[0]-bxy[0]*axy[1]
        xymesh = np.vstack((xyo,xya,xyb))
        xymeshydmax, xymeshydmin = np.max(xymesh, axis=0), np.min(xymesh, axis=0)
        listcells=intragridcells(xymesh, gridelt) # list of the grid cells containing the surrounding of the hydraulic mesh/triangle

        # finding the edges of substrate mesh/triangles able to be in the hydraulic triangle or to cut it eliminating duplicate edges
            #determining the list of substrate mesh that are in the same grid area of the hydraulic triangle
        setofmeshsubindex=set() #the list of substrate mesh that are in the same grid area of the hydraulic triangle
        for c in listcells:
            if celltriangleindexsub[c][0] != -1:  # the surrounding of a substrate mesh/triangle is in a grid cell (that is surrounding our hydraulic mesh)
                for k in range(celltriangleindexsub[c][0],celltriangleindexsub[c][1]+1):
                    isub=celltrianglelistsub[k][1]
                    setofmeshsubindex.add(isub)




        listofsubedges=[] #the list of substrate edges in the surrounding of the hydraulic mesh/triangle
        listofsubedgesindex=[] # the list of substrate mesh indexes corresponding to substrate edges
        for isub in setofmeshsubindex:
            # eliminating substrate mesh out of the very surrounding of the hydraulic mesh
            xymeshsub=np.vstack((xysub[iklesub[isub][0]],xysub[iklesub[isub][1]],xysub[iklesub[isub][2]]))
            if not((np.min(xymeshsub,axis=0)>xymeshydmax).any() or (np.max(xymeshsub,axis=0)<xymeshydmin).any()):
                listofsubedges.extend([[iklesub[isub][0],iklesub[isub][1]],[iklesub[isub][1],iklesub[isub][2]],[iklesub[isub][2],iklesub[isub][0]]])
                listofsubedgesindex.extend([isub,isub,isub])
        if len(listofsubedgesindex) != 0:
            subedges = np.array(listofsubedges) #array of substrate edges in the surrounding of the hydraulic mesh/triangle
            subedgesindex=np.array(listofsubedgesindex) # array of substrate mesh indexes corresponding to substrate edges
            #removing duplicate edges
            subedges.sort(axis=1) # in order to be able in the following : to consider (1,4) and (4,1) as the same edge (we have here at least 3 edges)
            subedgesunique, indices = np.unique(subedges, axis=0, return_inverse=True) #subedgesunique the edges of substrate mesh/triangles able to be in the hydraulic triangle or to cut it whith no duplicates
            subedgesuniqueindex=np.stack((indices,subedgesindex),axis=-1)
            subedgesuniqueindex = subedgesuniqueindex[subedgesuniqueindex[:, 0].argsort()]
            lsubedgesuniqueindex=[]
            j0=-3
            for j in range(len(indices)):
                if subedgesuniqueindex[j][0] != j0:
                    if j0 !=-3:
                        lsubedgesuniqueindex.append(l)
                    l=[subedgesuniqueindex[j][1]]
                    j0=subedgesuniqueindex[j][0]
                else:
                    l.append(subedgesuniqueindex[j][1])
            lsubedgesuniqueindex.append(l) # we have now for each edge of subedgesunique a corresponding list of substrate mesh/triangles (lsubedgesuniqueindex) wich are using that edge one edge can belong to two substrate mesh

            # finding the edges of substrate mesh/triangles that are inside the hydraulic triangle
            xynewpoint=[] #the points we are creating
            xynewpointlinkstohydr=[] # for each point of xynewpoint a sublist of 2 or 3 hydraulic points indexes in order to interpolate hydraulics values
            inewpoint=-1
            segin=[] #list of segments by reference to two newpoint index that are in
                #checking if points defining the substrate segment are inside or not in the hydraulic triangle and what exact edge of this triangle can be crossed
            lsubmeshin=[]#list of list of substrate mesh wich are in the hydraulic triangle (to flatten and duplicates have to be eliminated)
            #the vertices of our hydraulic triangle are stored because we will used them for segment definition given to Triangle library
            xynewpoint.extend ([xyo, xya, xyb])
            xynewpointlinkstohydr.extend ([[iklehyd[i][0], -1, -1], [iklehyd[i][1], -1, -1], [iklehyd[i][2], -1, -1]])
            inewpoint += 3

            # seaching for each substrate segment if we can extract a sub-segment inside the hydraulic triangle
            sidecontact1,sidecontact2,sidecontact4=[],[],[]
            for j in range(len(subedgesunique)):
                xyp,xyq=xysub[subedgesunique[j][0]],xysub[subedgesunique[j][1]]
                xyaffp = [(bxy[1] * (xyp[0] - xyo[0]) - bxy[0] * (xyp[1] - xyo[1])) / deta,
                          (-axy[1] * (xyp[0] - xyo[0]) + axy[0] * (xyp[1] - xyo[1])) / deta]
                xyaffq = [(bxy[1] * (xyq[0] - xyo[0]) - bxy[0] * (xyq[1] - xyo[1])) / deta,
                          (-axy[1] * (xyq[0] - xyo[0]) + axy[0] * (xyq[1] - xyo[1])) / deta]
                sidecontact=[0,0] # 2 numbers defining the position regarding the hydraulic triangle of repectively  P and Q (the points defining the subtrate segment )
                for k,xyaff in enumerate([xyaffp,xyaffq]):
                    if xyaff[1]<=0:
                        sidecontact[k]+=1
                    if xyaff[0]<=0:
                        sidecontact[k]+=2
                    if xyaff[1] >= -xyaff[0]+1:
                        sidecontact[k] += 4
                # both points of the substrate segment are inside the hydraulic triangle
                if sidecontact[0]==0 and sidecontact[1]==0 :
                    xynewpoint.extend([xyp,xyq])
                    xynewpointlinkstohydr.extend([[iklehyd[i][0], iklehyd[i][1], iklehyd[i][2]],[iklehyd[i][0], iklehyd[i][1], iklehyd[i][2]]])
                    segin.append([inewpoint + 1, inewpoint + 2])
                    inewpoint += 2
                    lsubmeshin.append(lsubedgesuniqueindex[j])
                # one point of the substrate segment is inside the hydraulic triangle
                elif (sidecontact[0] !=0 and sidecontact[1]==0) or (sidecontact[1] !=0 and sidecontact[0]==0):
                    xypq = [xyp, xyq]
                    kin,kout=0,1 #index of the xypq coordinates of the points defining the segment that are inside and outside the hydraulic triangle
                    if sidecontact[1] == 0:
                        kin,kout=1,0
                    xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][1], iklehyd[i][2]])
                    bok1, bok2,bok4=False,False,False
                    if sidecontact[kout] == 1:
                        bok1,xycontact1,distsqr1 =intersection2segmentsdistsquare(xyo,xya,xyp, xyq)
                    elif sidecontact[kout] == 2:
                        bok2,xycontact2,distsqr2 =intersection2segmentsdistsquare(xyb, xyo,xyp, xyq)
                    elif sidecontact[kout] == 4:
                        bok4,xycontact4,distsqr4 =intersection2segmentsdistsquare(xya, xyb,xyp, xyq)
                    else:
                        if sidecontact[kout] == 3:
                            bok1, xycontact1, distsqr1 = intersection2segmentsdistsquare(xyo, xya, xyp, xyq)
                            bok2, xycontact2, distsqr2 = intersection2segmentsdistsquare(xyb, xyo, xyp, xyq)
                        elif sidecontact[kout] == 5:
                            bok1, xycontact1, distsqr1 = intersection2segmentsdistsquare(xyo, xya, xyp, xyq)
                            bok4,xycontact4,distsqr4 =intersection2segmentsdistsquare(xya, xyb,xyp, xyq)
                        elif sidecontact[kout] == 6:
                            bok4,xycontact4,distsqr4 =intersection2segmentsdistsquare(xya, xyb,xyp, xyq)
                            bok2, xycontact2, distsqr2 = intersection2segmentsdistsquare(xyb, xyo, xyp, xyq)
                    if bok1 + bok2 + bok4 !=1 :
                        print("Mathematical problem please contact a programmer")
                    else:
                        if bok1:
                            xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][1], -1])
                            sidecontact1.append([distsqr1,inewpoint + 2])
                            xynewpoint.extend([xypq[kin], xycontact1])
                        elif bok2:
                            xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][2], -1])
                            sidecontact2.append([distsqr2, inewpoint + 2])
                            xynewpoint.extend([xypq[kin], xycontact2])
                        elif bok4:
                            xynewpointlinkstohydr.append([iklehyd[i][1], iklehyd[i][2], -1])
                            sidecontact4.append([distsqr4, inewpoint + 2])
                            xynewpoint.extend([xypq[kin], xycontact4])
                    segin.append([inewpoint + 1, inewpoint + 2])
                    inewpoint += 2
                    lsubmeshin.append(lsubedgesuniqueindex[j])


                        # print(subedgesunique[j])

                # seaching if the substrate segment cut 2 edges of the the hydraulic triangle
                else:
                    bok1,xycontact1,distsqr1=intersection2segmentsdistsquare(xyo,xya,xyp, xyq)
                    bok2,xycontact2,distsqr2=intersection2segmentsdistsquare(xyb, xyo,xyp, xyq)
                    bok4,xycontact4,distsqr4=intersection2segmentsdistsquare(xya, xyb,xyp, xyq)
                    if bok1 + bok2+bok4 ==2:
                        if bok1 and bok2 :
                            xynewpoint.extend([xycontact1, xycontact2])
                            xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][1], -1])
                            xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][2], -1])
                            sidecontact1.append([distsqr1, inewpoint + 1])
                            sidecontact2.append([distsqr2, inewpoint + 2])
                        if bok1 and bok4 :
                            xynewpoint.extend([xycontact1, xycontact4])
                            xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][1], -1])
                            xynewpointlinkstohydr.append([iklehyd[i][1], iklehyd[i][2], -1])
                            sidecontact1.append([distsqr1, inewpoint + 1])
                            sidecontact4.append([distsqr4, inewpoint + 2])
                        if bok4 and bok2 :
                            xynewpoint.extend([xycontact4, xycontact2])
                            xynewpointlinkstohydr.append([iklehyd[i][1], iklehyd[i][2], -1])
                            xynewpointlinkstohydr.append([iklehyd[i][0], iklehyd[i][2], -1])
                            sidecontact4.append([distsqr4, inewpoint + 1])
                            sidecontact2.append([distsqr2, inewpoint + 2])
                        segin.append([inewpoint + 1, inewpoint + 2])
                        inewpoint += 2
                        lsubmeshin.append(lsubedgesuniqueindex[j])

            #using Triangle library to build a triangular mesh based on substrate segments inside the hydraulic triangle
            if inewpoint != 2:
                #adding all partials segments along the edges of the hydraulical triangle
                if len(sidecontact1) != 0:
                    sidecontact1.sort()
                    sidecontact1 = [y[1] for y in sidecontact1]
                if len(sidecontact2) != 0:
                    sidecontact2.sort()
                    sidecontact2 = [y[1] for y in sidecontact2]
                if len(sidecontact4) != 0:
                    sidecontact4.sort()
                    sidecontact4 = [y[1] for y in sidecontact4]
                sidecontact1=[0]+sidecontact1+[1]
                sidecontact2=[2]+sidecontact2+[0]
                sidecontact4 =[1]+sidecontact4+[2]
                for sidecontactx in (sidecontact1, sidecontact2, sidecontact4):
                    for y in range(len(sidecontactx)-1):
                        segin.append([sidecontactx[y], sidecontactx[y+1]])

                # A = {'vertices': xynewpoint, 'segments': segin}

                #eliminating duplicate points for using Triangle library
                nxynewpoint=np.array(xynewpoint) #[xypq[kin], xycontact,......])
                nsegin=np.array(segin)#[inewpoint + 1, inewpoint + 2]
                nxynewpointlinkstohydr=np.array(xynewpointlinkstohydr) #[iklehyd[i][0], iklehyd[i][1], iklehyd[i][2]],[iklehyd[i][0], iklehyd[i][1], -1],.

                try:
                    nxynewpoint2, indices2 = np.unique(nxynewpoint, axis=0 ,return_inverse=True)
                except TypeError:
                    aa=1

                nsegin2=indices2[nsegin]
                nxynewpoint2, indices3 = np.unique(nxynewpoint, axis=0, return_index=True) #nxynewpoint2 doesnt change
                nxynewpointlinkstohydr2=nxynewpointlinkstohydr[indices3]
                # Using Triangle library to build a mesh from our segments
                A = {'vertices': nxynewpoint2,'segments': nsegin2}
                t = tr.triangulate(A, 'p')

                # tr.compare(plt, A, t)
                # plt.show()
                # print(nxynewpoint2)
                # print(t['vertices'],t['triangles'])

                # check if Triangle library has added new points at the end of our original list of 'vertices'
                nxynewpoint, iklenew = t['vertices'], t['triangles']
                newpointtrianglevalidate=len(t['vertices'])-len(nxynewpoint2)
                if newpointtrianglevalidate!=0: #Triangle library has added new points at the end of our original list of 'vertices'
                    nxynewpointlinkstohydr=np.vstack(nxynewpointlinkstohydr2 ,np.array ([iklehyd[i][0], iklehyd[i][1], iklehyd[i][2]]*newpointtrianglevalidate))
                else:
                    nxynewpointlinkstohydr = nxynewpointlinkstohydr2

                #affecting substrate values to meshes merge
                ssubmeshin2 = set([item for sublist in lsubmeshin for item in
                                   sublist])  # set of substrate mesh that can be in the hydraulic triangle
                # testing meshes merge centers regarding substrate mesh  to affect substrate values to meshes merge
                datasubnew = [defautsub.tolist()]*(iklenew.size // 3) # even if one single triangle for iklenew
                for ii,ikle in enumerate(iklenew):
                    xyc=(nxynewpoint[ikle[0]]+nxynewpoint[ikle[1]]+nxynewpoint[ikle[2]])/3
                    for jj in ssubmeshin2:
                            if point_inside_polygon(xyc[0],xyc[1],[xysub[iklesub[jj][0]].tolist(),xysub[iklesub[jj][1]].tolist(),xysub[iklesub[jj][2]].tolist()]):
                                datasubnew[ii]=datasub[jj].tolist()
                                break

            else: #no substrate edges in the hydraulic triangle
                nxynewpoint=np.array([xyo, xya, xyb])
                nxynewpointlinkstohydr=np.array([[iklehyd[i][0], -1, -1], [iklehyd[i][1], -1, -1], [iklehyd[i][2], -1, -1]])
                iklenew=np.array([[0,1,2]])
                datasubnew=[defautsub.tolist()]
                # checking if a substrate mesh contain the hydraulic mesh
                xyc = (xyo+ xya+ xyb) / 3
                for jj in setofmeshsubindex:
                    if point_inside_polygon(xyc[0], xyc[1], [xysub[iklesub[jj][0]].tolist(),xysub[iklesub[jj][1]].tolist(),xysub[iklesub[jj][2]].tolist()]):
                        datasubnew[0] = datasub[jj]
                        break
        else: #no substrate mesh around the hydraulic triangle
            nxynewpoint = np.array([xyo, xya, xyb])
            nxynewpointlinkstohydr = np.array(
                [[iklehyd[i][0], -1, -1], [iklehyd[i][1], -1, -1], [iklehyd[i][2], -1, -1]])
            iklenew = np.array([[0, 1, 2]])
            datasubnew = [defautsub.tolist()]

        # merges accumulation
        # ++++ datahydc inside hydraulic mesh to all triangles

        xymerge.extend(nxynewpoint.tolist())
        iklemerge.extend((iklenew+decalnewpointmerge).tolist())
        datasubmerge.extend(datasubnew)
        xymergepointlinkstohydr.extend(nxynewpointlinkstohydr.tolist())
        decalnewpointmerge += len(nxynewpoint)
    #+++get rid of duplicate points
    nxymerge=np.array(xymerge)
    niklemerge=np.array(iklemerge)
    nxymergepointlinkstohydr=np.array(xymergepointlinkstohydr)
    nxymerge1, indices2 = np.unique(nxymerge, axis=0, return_inverse=True)
    niklemerge1 = indices2[niklemerge]
    nxymerge1, indices3 = np.unique(nxymerge, axis=0, return_index=True)  # nxynewpoint2 doesnt change
    nxymergepointlinkstohydr1 = nxymergepointlinkstohydr[indices3]
    #++++interpolate datahyd

    return nxymerge1,niklemerge1,datasubmerge


def intersection2segmentsdistsquare(xya,xyb,xyc,xyd):
    bok=False
    xycontact = [0, 0]
    dist_square_to_a=0
    u1,u2=xyb[1]-xya[1],xyd[1]-xyc[1]
    v1,v2 = xya[0] - xyb[0],xyc[0] - xyd[0]
    w1,w2=xya[1]*xyb[0]-xya[0]*xyb[1],xyc[1]*xyd[0]-xyc[0]*xyd[1]
    xycontact=[None,None]
    det= u1*v2-u2*v1
    if det!=0:
        # valeur 0 acceptée car l'on admet que l'un des points A,B,C,D peut être sur les 2 segments
        if (u2*xya[0]+v2*xya[1]+w2)*((u2*xyb[0]+v2*xyb[1]+w2))<=0 and (u1*xyc[0]+v1*xyc[1]+w1)*((u1*xyd[0]+v1*xyd[1]+w1))<=0 :
            bok=True
            xycontact = [(-w1 * v2 + w2 * v1) / det, (-u1 * w2 + u2 * w1) / det]
            dist_square_to_a=(xycontact[0]-xya[0])**2+(xycontact[1]-xya[1])**2
    return bok,xycontact,dist_square_to_a

def gridikle(xysub,iklesub,gridelt):
    '''
    building the table : for each cell of the grid  determining the list of triangles from the ikle that have at least a part in the cell
    :param xysub:
    :param iklesub:
    :param gridelt:
    :return:
    '''
    table0= []
    for i in range(iklesub.size//3): # even if one single triangle for iklesub
        xymesh = np.vstack((xysub[iklesub[i][0]], xysub[iklesub[i][1]], xysub[iklesub[i][2]]))
        listcells=intragridcells(xymesh, gridelt)
        for j in listcells:
            table0.append([j,i])
    # print(table0)
    celltrianglelist=np.array(table0)  # to avoid topoligical problem  eventually set(table0) if orignal ikle contains double ....
    # print()
    # print( celltrianglelist)
    celltrianglelist=celltrianglelist[celltrianglelist[:, 0].argsort()]
    celltriangleindex=np.empty((gridelt['nbcell'][0] *gridelt['nbcell'][1] +1,2))# WARNING  +1 the first line index 0 in python is not used the first cell of the grid began to one
    celltriangleindex.fill(-1)
    j0=-3
    for i,j in enumerate(celltrianglelist):
        if j[0]!=j0:
            celltriangleindex[j[0]][0]=i
            celltriangleindex[j[0]][1] = i #in case of one single triangle
            j0= j[0]
        else :
            celltriangleindex[j[0]][1] = i   #TODO improve...

    # print(celltriangleindex)
    # print()
    # print( celltrianglelist)
    return  celltriangleindex.astype(np.int64),celltrianglelist  #the first column of celltrianglelist will not be used after

def intragridcells(xymesh, gridelt):
    '''
    how to extract the cells numbers of the intra-grid(sub grid) that contains the triangle
    :param xymesh:
    :param gridelt:
    :return:
    '''
    xymaxmesh = np.max(xymesh, axis=0)
    xyminmesh = np.min(xymesh, axis=0)
    rectangle= np.array([[xyminmesh[0],xyminmesh[1]],[xymaxmesh[0],xyminmesh[1]],[xyminmesh[0],xymaxmesh[1]],[xymaxmesh[0],xymaxmesh[1]]])
    listcells0=[]
    for j in range(4):
        xx=(rectangle[j] [0]-gridelt['xymin'][0])/gridelt['deltagrid']
        xx1=math.floor(xx)
        if xx-xx1 !=0:
            xx1+=1
        if xx1==0:
            xx1=1
        yy = (rectangle[j][1] - gridelt['xymin'][1])/gridelt['deltagrid']
        yy1=math.floor(yy)*gridelt['nbcell'][0]  #gridelt['nbcell'][0] = number of columns of the grid
        listcells0.append(int(xx1+yy1))
    listcells = []
    nbcolx=listcells0[1]-listcells0[0]+1
    if listcells0[3]-listcells0[2]+1 !=nbcolx:
        print('Error in extracting intra-grid')
    intragridx=[listcells0[0]+y*gridelt['nbcell'][0] for y in range((listcells0[2]-listcells0[0])//gridelt['nbcell'][0]+1)] #(listcells0[3]-listcells0[0])//gridelt['nbcell'][0]+1 = nblines of the intragrid
    listcells=[y for k in intragridx for y in range(k,k+nbcolx)]
    return listcells

def griddef(xyhyd,xysub,iklehyd,iklesub,coeffgrid):
    '''
    defining the grid
    :param xyhyd:
    :param xysub:
    :param iklehyd:
    :param iklesub:
    :param coeffgrid:
    :return:
    '''
    gridelt={}
    xyall=np.concatenate((xyhyd, xysub), axis=0)
    xymax0=np.ceil(np.max(xyall,axis=0)+0.1)# +0.1 to avoid point with xmax or ymax beign out of the constructed grid
    xymin = np.floor(np.min(xyall, axis=0))
    dxygrid = xymax0 - xymin
    totalarea=dxygrid[0]*dxygrid[1]



    areahyd,densityhyd=tinareadensity(xyhyd,iklehyd)
    areasub, densitysub = tinareadensity(xysub, iklesub)
    nbgrid = math.ceil(max(densityhyd, densitysub) *totalarea* coeffgrid)


    # nbmeshhyd,nbmeshsub=iklehyd.size // 3,iklesub.size // 3
    # nbgrid=math.ceil(max(nbmeshhyd,nbmeshsub)*coeffgrid)

    #nbgrid = math.ceil(math.sqrt(63 + 0.0005 * (len(xyhyd) + len(xysub)) / 2))


    if nbgrid==0 :
        return False #TODO Gerer ce cas ou les maillages sont vides
    deltagrid=math.ceil(math.sqrt(totalarea/nbgrid))
    nbcell=np.ceil(dxygrid/deltagrid)
    gridelt['xymax']=xymin+nbcell*deltagrid
    gridelt['xymin'] =xymin
    gridelt['deltagrid'] =deltagrid
    gridelt['nbcell'] =nbcell.astype(np.int64)
    return gridelt



def point_inside_polygon(x,y,poly):
    """
    http://www.ariel.com.au/a/python-point-int-poly.html
    To know if point is inside or outsite of a polygon (without holes)
    :param x: coordinate x in float
    :param y: coordinate y in float
    :param poly: list of coordinates [[x1, y1], ..., [xn, yn]]
    :return: True (inside), False (not inseide)
    """
    n = len(poly)
    inside =False
    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y
    return inside

def tinareadensity(xy,ikle):
    '''
    Calculating the total area and the density (total_mesh_area/number_of_meshes) of a Triangular Irregular Network
    :param xy: a numpy array of x and y coordinate
    :param ikle: a tin description of the TIN given by lines of 3 indexes (xy)  corresponding to the 3 nodes f each triangle/mesh
    :return: total_area ,density (total_area/number_of_meshes)
    '''
    total_area=np.sum(0.5*(np.abs((xy[ikle[:,1]][:,0] - xy[ikle[:,0]][:,0]) * (xy[ikle[:,2]][:,1] - xy[ikle[:,0]][:,1])- (xy[ikle[:,2]][:,0] - xy[ikle[:,0]][:,0]) * (xy[ikle[:,1]][:,1] - xy[ikle[:,0]][:,1]))))
    return total_area, total_area/(ikle.size//3)



####################################TEST PART ########################################################################################
def build_hyd_sub_mesh(bshow,nbpointhyd,nbpointsub,seedhyd=None,seedsub=None,rectangles=((0,0,100,100),),hull=None,emptypoints=None):
    if seedhyd!=None:
        np.random.seed(seedhyd)
    rectangles=np.array(rectangles)
    vertices=rectangles[:,0:2]
    shapes=rectangles[:,2:4]


    # xyhyd = np.random.rand(nbpointhyd, 2)*100 #pavé [0,100[X[0,100[
    ##divide nbpointhyd and nbpointsub proportionate to rectangle area
    rectangle_areas=np.prod(shapes,axis=1)
    totalarea=np.sum(rectangle_areas)
    A={}
    if hull != None and emptypoints != None:  # hull should be a n×2 np array containing the (x,y) coordinates of the vertices of the intended convex hull of the hyd and sub meshes
        xyhyd = np.array(hull)
        xysub = np.array(hull)
        hullsegments = np.array([list(range(0, len(hull))), list(range(1, len(hull))) + [0]])
        A["segments"], A["holes"] = hullsegments.T, emptypoints
        for i in range(0, len(rectangles)):
            xyhydi = vertices[i] + np.random.rand(int((rectangle_areas[i] / totalarea) * nbpointhyd), 2) * shapes[i]
            xyhyd = np.concatenate((xyhyd, xyhydi), axis=0)
    else:
        xyhyd = vertices[0] + np.random.rand(int((rectangle_areas[0] / totalarea) * nbpointhyd), 2) * shapes[0]
        for i in range(1,len(rectangles)):
            xyhydi = vertices[i] + np.random.rand(int((rectangle_areas[i]/totalarea) * nbpointhyd),2) * shapes[i]
            xyhyd=np.concatenate((xyhyd,xyhydi),axis=0)

    # xyhyd=vertex+np.random.rand(nbpointhyd,2)*shape #rectangle a×b, where shape=(a,b)
    # print('seedhyd', np.random.get_state()[1][0])
    # TODO supprimer les doublons
    # A = dict(vertices=xyhyd)  # A['vertices'].shape  : (4, 2)
    A["vertices"]=xyhyd
    if hull!=None and emptypoints!=None: #hull should be a n×2 np array containing the (x,y) coordinates of the vertices of the intended convex hull of the hyd and sub meshes
        xyhyd=np.array(hull)
        xysub=np.array(hull)
        hullsegments=np.array([list(range(0,len(hull))),list(range(1,len(hull)))+[0]])
        A["segments"],A["holes"]=hullsegments.T,emptypoints
        print(A)
    B = tr.triangulate(A)  # type(B)     class 'dict'>
    # eventuellement check si xyhyd a changé.....
    if bshow:
        tr.compare(plt, A, B)
        plt.show()

    if seedsub!=None:
        np.random.seed(seedsub)
    xysub = vertices[0] + np.random.rand(int((rectangle_areas[0] / totalarea) * nbpointsub), 2) * shapes[0]
    for i in range(len(rectangles)):
        xysubi = vertices[i] + np.random.rand(int((rectangle_areas[i]/totalarea) * nbpointsub), 2) * shapes[i]
        xysub = np.concatenate((xysub, xysubi), axis=0)

    # xysub=np.random.rand(nbpointsub,2)*100 #pavé [0,100[X[0,100[
    # xysub=vertex+np.random.rand(nbpointsub,2)*shape
    # print('seedsub', np.random.get_state()[1][0])
    # TODO supprimer les doublons
    C = dict(vertices=xysub)
    D = tr.triangulate(C)
    # eventuellement check si xysub a changé.....
    if bshow:
        tr.compare(plt, C, D)
        plt.show()
    if seedsub!=None:
        np.random.seed(seedsub)
    datasub= np.random.randint(2,9, size=(len(D['triangles']), 1))
    datasub=np.hstack((datasub, datasub))

    return B['vertices'],B['triangles'],D['vertices'],D['triangles'],datasub


if __name__ == '__main__':
    t=0
    if t==0: #aleatoire
        nbpointhyd, nbpointsub, seedhyd , seedsub = 5000,7000, 9, 32
        xyhyd,iklehyd,xysub,iklesub,datasub =build_hyd_sub_mesh(False,nbpointhyd, nbpointsub, seedhyd , seedsub, rectangles=((0,0,100,40),(60,40,40,60),(100,60,60,40)),hull=[[0,0],[0,40],[60,40],[60,100],[160,100],[160,60],[100,60],[100,0]],emptypoints=[[59,41],[101,59],[15,15]]) ##############)
    elif t==1:
        xyhyd=np.array([[4,1],[5,4],[6,1] ])
        iklehyd=np.array([[0,1,2]])
        xysub=np.array([[3,3],[3,5],[6,3] ])
        iklesub=np.array([[0,1,2]])
        datasub=np.array([[2,2]])
    elif t==2:
        xyhyd=np.array([[4,1],[5,4],[6,1] ])
        iklehyd=np.array([[0,1,2]])
        xysub=np.array([[3,3],[3,5],[6,3],[3,1] ])
        iklesub=np.array([[0,1,2],[3,0,2]])
        datasub=np.array([[2,2],[3,3]])
    elif t==3:
        xyhyd=np.array([[4,1],[5,4],[6,1],[14,11],[15,14],[16,11] ])
        iklehyd=np.array([[0,1,2],[3,4,5]])
        xysub=np.array([[3,3],[3,5],[6,3],[3,1],[13,13],[13,15],[16,13],[13,11] ])
        iklesub=np.array([[0,1,2],[3,0,2],[4,5,6],[7,4,6]])
        datasub=np.array([[2,2],[3,3],[4,4],[5,5]])
    elif t==4:
        xyhyd=np.array([[8,5],[10,5],[8,7]])
        iklehyd=np.array([[0,1,2]])
        xysub=np.array([[7,4],[12,4],[7,10]])
        iklesub=np.array([[0,1,2]])
        datasub=np.array([[7,7]])
    defautsub=np.array([1,1])
    coeffgrid=1/2  # plus coeffgrid est grand plus la grille  de reperage sera fine



    ti = datetime.now()
    ######
    print(xyhyd, iklehyd, xysub, iklesub, datasub)
    ######
    nxymerge1,niklemerge1,datasubmerge=merge(xyhyd,iklehyd,xysub,iklesub,datasub ,defautsub,coeffgrid)

    # areahyd,densityhyd=tinareadensity(xyhyd,iklehyd)
    # areamerge, densitymerge = tinareadensity(nxymerge1,niklemerge1)
    # print(areahyd,densityhyd,areamerge, densitymerge)

    # print(nxymerge1,niklemerge1,datasubmerge)

    # print(datasub[:,0])
    # print(np.array(datasubmerge)[:,0])

    tf = datetime.now()
    print('finish', tf - ti)

    plot_merge_check.plot_to_check_mesh_merging(xyhyd,iklehyd,xysub,iklesub,datasub[:,0], nxymerge1,niklemerge1,np.array(datasubmerge)[:,0])

