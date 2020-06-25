import numpy as np

def hydrosignature_calculation(hyd_xy_node,hyd_hv_node, hyd_data_node, hyd_tin, iwholeprofile, hyd_data_mesh, hyd_data_sub_mesh):
    """
    Merging an hydraulic TIN (Triangular Irregular Network) and a substrate TIN to obtain a merge TIN
    (based on the hydraulic one) by partitionning each hydraulic triangle/mesh if necessary into smaller
    triangles/meshes that contain a substrate from the substrate TIN or a default substrate. Additional nodes inside
    or on the edges of an hydraulic mesh will be given hydraulic data by interpolation of the hydraulic data from the
    hydraulic mesh nodes.Flat hydraulic or substrates triangles will not been taken inot account.
    TAKE CARE during the merge a translation is done to minimise numericals problems
     Using numpy arrays as entry and returning numpy arrays.
    :param hyd_xy_node: The x,y nodes coordinates of a hydraulic TIN (Triangular Irregular Network)
    :param hyd_hv_node: the wather depth, mean velocity of the verticals/nodes of a hydraulic TIN
    :param hyd_data_node: The hydraulic data of the hydraulic nodes (eg : z, temperature...)
    :param hyd_tin: The hydraulic TIN (Triangular Irregular Network) 3 columns of nodes indexes each line is a
            mesh/triangle
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
    translationxy = np.min(hyd_xy_node, axis=0)
    hyd_xy_node -= translationxy

    hs_xy_node=[]


    for i in range(hyd_tin.size // 3):  # even if one single triangle for hyd_tin
        xyo, xya, xyb = hyd_xy_node[hyd_tin[i][0]], hyd_xy_node[hyd_tin[i][1]], hyd_xy_node[hyd_tin[i][2]]
        axy, bxy = xya - xyo, xyb - xyo
        deta = bxy[1] * axy[0] - bxy[0] * axy[1]
        if deta == 0:
            print('before hs an hydraulic triangle have an area=0 ')
        else:














    hs_xy_node +=translationxy
    hyd_xy_node +=translationxy
    return hs_xy_node, hs_data_node, hs_tin, iwholeprofilehs, np.array(hs_data_mesh),hs_data_sub_mesh














if __name__ == '__main__':
    '''
    testing the hydrosignature program
    '''