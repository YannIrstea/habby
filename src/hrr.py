from src.hdf5_mod import Hdf5Management
import numpy as np

def connectivity_mesh_table(tin):
    #AIM finding  for each mesh the 3 neighbour meshes (ie sharing a segment)
    connex = np.zeros((len(tin), 3), dtype=np.float64)
    # 1 getteing the list of segment by couple of node index (sorted in order to be able to find dupilcate) 3rd column= origin mesh index
    aindex=np.arange(len(tin))
    segment= np.r_[np.c_[tin[:,0:2],aindex],np.c_[tin[:,1:],aindex],np.c_[tin[:,[0,2]],aindex]]
    segment = segment[np.lexsort((segment[:, 1], segment[:, 0]))]
    loca =np.full((len(tin), 3), -1, dtype=np.int64)
    posfree=np.zeros((len(tin), 1), dtype=np.int64)
    for j in range(3*len(tin)-1):
        if np.all(segment[j][0:2]==segment[j+1][0:2]):
            loca[segment[j][2]][posfree[segment[j][2]]]=segment[j+1][2]
            loca[segment[j+1][2]][posfree[segment[j+1][2]]] = segment[j][2]
            posfree[segment[j][2]]+=1
            posfree[segment[j+1][2]] += 1
            if posfree[segment[j][2]] >2 or posfree[segment[j+1][2]] >2:
                print ('anomalie majeure')
                return

    u, c = np.unique(segment[:,0:2], axis=0, return_counts=True)



    return connex




def c_mesh_max_slope_surface(tin,xy,z,h):
    '''

    :param tin: Triangular Irregular Network numpy array of 3 nodes index describing each mesh
    :param xy: numpy array of coordinate x,y of each node
    :param z:  numpy array of bottom altitude of each node
    :param h:  numpy array of height of water of each node
    :return: mesh_max_slope_surface of each mesh: numpy arraysrc/hrr.py:27
    '''
    xy1 = xy[tin[:, 0]]
    z1 = z[tin[:, 0]]
    h1 = h[tin[:, 0]]
    xy2 = xy[tin[:, 1]]
    z2 = z[tin[:, 1]]
    h2 = h[tin[:, 1]]
    xy3 = xy[tin[:, 2]]
    z3 = z[tin[:, 2]]
    h3 = h[tin[:, 2]]

    w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
    zz1, zz2, zz3 = z1 + h1 , z2 + h2 , z3 + h3
    u = (xy2[:, 1] - xy1[:, 1]) * (zz3 - zz1) - (zz2 - zz1) * (xy3[:, 1] - xy1[:, 1])
    v = (xy3[:, 0] - xy1[:, 0]) * (zz2 - zz1) - (zz3 - zz1) * (xy2[:, 0] - xy1[:, 0])
    with np.errstate(divide='ignore', invalid='ignore'):
        mesh_max_slope_surface = np.sqrt(u ** 2 + v ** 2) / np.abs(w)

    # change inf values to nan
    if np.inf in mesh_max_slope_surface:
        mesh_max_slope_surface[mesh_max_slope_surface == np.inf] = np.NaN

    # change incoherent values to nan
    # with np.errstate(invalid='ignore'):  # ignore warning due to NaN values
    #     mesh_max_slope_surface[mesh_max_slope_surface > 0.08] = np.NaN  # 0.08

    return mesh_max_slope_surface


if __name__ == '__main__':
    # set working directory to "C:\habby_dev\habby"
    path_prj = r"C:\Users\yann.lecoarer\Documents\HABBY_projects\DefaultProj"

    # first file
    input_filename_1 = "d1_d2_d3_d4.hyd"

    # load file
    hdf5_1 = Hdf5Management(path_prj, input_filename_1, new=False, edit=False)
    hdf5_1.load_hdf5(whole_profil=True)

    hdf5_1.data_2d.hyd_cuted_mesh_partialy_dry  # True if Cut2D

    #*****************TAF**********************
    #ToDo
    #Verifier que le whole profile est unique !!

    # for all reach
    for reach_number in range(0, hdf5_1.data_2d.reach_number):
        # for all units
        for unit_number in range(0, hdf5_1.data_2d[reach_number].unit_number):
            # c_mesh_height
            hdf5_1.data_2d[reach_number][unit_number].c_mesh_height()  # compute h mesh from h node (memory)

            # get tin first reach first unit
            tin = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"]



            connex = connectivity_mesh_table (tin[0:5,:])


            xy = hdf5_1.data_2d[reach_number][unit_number]["node"]["xy"]
            z_fond_node = hdf5_1.data_2d[reach_number][unit_number]["node"]["z"]
            h_node = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"]["h"]
            h_mesh = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["h"]
            i_whole_profile = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
            i_split = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["i_split"]

            # get tin first reach first unit whole_profile
            xy_whole_profile = hdf5_1.data_2d_whole[reach_number][unit_number]["node"]["xy"]
            tin_whole_profile = hdf5_1.data_2d_whole[reach_number][unit_number]["mesh"]["tin"]



            titi = 1

