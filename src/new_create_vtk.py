"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import os
from src import load_hdf5
import numpy as np
# from src import calcul_hab  useful to test, but do not work with the whole programm
from src import hl
import time
import xml.dom.minidom


def habitat_to_vtu(file_name_base, path_out, path_hdf5, name_hdf5, vh_all_t_sp, height_c_data, vel_c_data, name_fish,
                   erase_id):
    """
    This function creates paraview input in the new, non-legacy xml format. This function called the evtk class
    written by Paulo Herrera, which is available at https://bitbucket.org/pauloh/pyevtk/downloads/

    The format for paravier input file is descirbed in paraview_file_format.pdf in the doc folder of HABBY.

    The data of the paraview file created here  is usually in binary form. The idea of paraview for a binary file is
    to keep the same usual xml file. The data is encoded to base64. Before the binary array, there is a 32-bits interger
    which contains the data length in bytes.
    More info: http://www.earthmodels.org/software/vtk-and-paraview/vtk-file-formats.

    Paraview can handle a group of file which compose an output with than one time step. This is the reason to create a
    pwd files which list the files composing all the time steps (one file by time step)

    :param file_name_base: the base to create the name of the vtu file
    :param path_hdf5: the path to the hdf5 hydro file (to load the grid)
    :param name_hdf5: the name of the hdf5 containing the grid
    :param vh_all_t_sp: the habitat data by reach, time step, species
    :param height_c_data: the height by cell by reach by time step
    :param vel_c_data: the velocity by cell by reach by time step
    :param name_fish: the name of fish and stage
    :param path_out: the path where to save the data
    :param erase_id: if True, previous paraview file from identical merge file are erased

    """

    file_names_all = []
    if len(file_name_base)>60:
        file_name_base = os.path.join(path_out, file_name_base)[:-25]
    else:
        file_name_base = os.path.join(path_out, file_name_base)
    # format the name of species and stage
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # load grid (could also be used if velcoity and height point data is needed)
    [ikle_all_t, point_all_t, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_hdf5, path_hdf5, True)
    if ikle_all_t == [-99]:
        return
    nb_time = len(ikle_all_t)

    for r in range(0, len(ikle_all_t[-1])):
        if not erase_id:
            fileName = file_name_base + '_' + 'Reach' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
        else:
            fileName = file_name_base + '_' + 'Reach' + str(r)

        # create one vtu file by time step
        # for the moment we do not show the time step zero with the full profile without data
        for t in range(1, nb_time):
            ikle = ikle_all_t[t][r]
            if len(ikle) < 3 or t > len(height_c_data):  # if something is wrong
                pass
                # print('Error: Connectivity table missing or illogical. One time step not created. \n')
            else:

                # grid data preparation for vtk
                point = np.array(point_all_t[t][r])

                x = np.array(point[:, 0])
                y = np.array(point[:, 1])
                z = np.zeros(len(x), )
                connectivity = np.reshape(ikle, (len(ikle) * 3,))

                offsets = np.arange(3, len(ikle) * 3 + 3, 3)
                offsets = np.array(list(map(int, offsets)))
                cell_types = np.zeros(len(ikle), ) + 5  # triangle
                cell_types = np.array(list((map(int, cell_types))))

                # data creation
                cellData = {}
                for sp in range(0, len(vh_all_t_sp)):
                    newkey = "HSI " + name_fish[sp]
                    cellData[newkey] = np.array(vh_all_t_sp[sp][t][r])

                cellData['height'] = height_c_data[t][r]
                cellData['velocity'] = vel_c_data[t][r]
                cellData['coarser sub'] = sub_pg_data[t][r]
                cellData['dominant sub'] = sub_dom_data[t][r]

                # create the grid and the vtu files
                name_here = fileName + '_t' + str(t) + '.vtu'
                if erase_id:
                    if os.path.isfile(name_here):
                        os.remove(name_here)
                file_names_all.append(name_here)
                hl.unstructuredGridToVTK(fileName + '_t' + str(t), x, y, z, connectivity, offsets, cell_types, cellData)


        # create the "grouping" file to read all time step together
        name_here = fileName + '.pvd'
        if erase_id:
            if os.path.isfile(name_here):
                os.remove(name_here)
        writePVD(name_here, file_names_all)
        file_names_all = []


def writePVD(fileName, fileNames):
    """
    This function write the file which indicates to paraview how to group the file. This "grouping" file is pvd file.
    With this file, paraview can open all the time steps together with one clic. This function is heavily inspired
    by the class given at the adress:
    https://github.com/cfinch/Shocksolution_Examples/blob/master/Visualization/vtktools.py. Because Element Tree
    was not used in the class from Shocksolution, we use minidom here instead of Element Tree.

    :param fileName: the name of the pvd file
    :param fileNames: the names of all the files for this time step (usually only for one reach but could be changed).

    """

    pvd = xml.dom.minidom.Document()
    pvd_root = pvd.createElementNS("VTK", "VTKFile")
    pvd_root.setAttribute("type", "Collection")
    pvd_root.setAttribute("version", "0.1")
    pvd_root.setAttribute("byte_order", "LittleEndian")
    pvd.appendChild(pvd_root)

    collection = pvd.createElementNS("VTK", "Collection")
    pvd_root.appendChild(collection)

    for i in range(len(fileNames)):
        dataSet = pvd.createElementNS("VTK", "DataSet")
        dataSet.setAttribute("timestep", str(i))
        dataSet.setAttribute("group", "")
        dataSet.setAttribute("part", "0")
        dataSet.setAttribute("file", str(fileNames[i]))
        collection.appendChild(dataSet)

    outFile = open(fileName, 'w')
    pvd.writexml(outFile, newl='\n')
    outFile.close()

def save_slf(name_hdf5, path_hdf5, path_slf, merge, output_name='', habitat = []):
    """
    This is a function to export slf.

    :param name_hdf5:
    :param path_hdf5:
    :param merge: a boolean to know if you have substrate or not
    :return:
    """
    print('export here')

    # load hdf5
    if not merge:
        [ikle_all_t, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(name_hdf5,
                                                                                           path_hdf5, merge)
    else:
        [ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom] \
            = load_hdf5.load_hdf5_hyd(name_hdf5, path_hdf5, merge)
    if isinstance(ikle_all_t[0][0], int) and  ikle_all_t[0][0]== -99:
        print('Error: Hdf5 file not loaded \n')
        return

    #print(ikle_all_t[1][0])
    if not output_name:
        filename=os.path.join(path_slf,name_hdf5[:-3] + '.slf')
    else:
        filename = os.path.join(path_slf, output_name + '.slf')
    f = open(filename, "w")
    f.write("ecriture du slf provisoire")
    f.close()


def main():
    """
    Used to test this module
    """
    path_hdf5 = r'D:\Diane_work\dummy_folder\Projet1\fichier_hdf5'
    name_hdf5 = r'MERGE_Hydro_RUBAR2D_BS15a621_03_2017_at_10_15_45.h5'
    blob = None
    path_vtk = r'D:\Diane_work\dummy_folder\res_vtk'
    fileName = os.path.join(path_vtk,'test')
    path_bio = r'C:\Users\diane.von-gunten\HABBY\biology'

    #[vh_all_t_sp, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t_sp] = calcul_hab.calc_hab(name_hdf5, path_hdf5, ['BAM01.xml'], ['juvenile'], path_bio, 0)
    #habitat_to_vtu(fileName, path_vtk, path_hdf5, name_hdf5, vh_all_t_sp, vel_c_att_t, height_c_all_t, ['BAM'], True)


if __name__ == '__main__':
    main()
