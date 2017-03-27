import xml.dom.minidom
from src import load_hdf5
import numpy as np
import os
import base64


def habitat_to_vtu(file_name_base, path_out, path_hdf5, name_hdf5, vh_all_t_sp, height_c_data, vel_c_data, name_fish,
                   binary_data=False):
    """
    This function creates paraview input in the new, non-legacy xml format. This function is heavily inspired
    by the class given at the adress:
    https://github.com/cfinch/Shocksolution_Examples/blob/master/Visualization/vtktools.py. Because Element Tree
    was not used in the class from Shocksolution, we use minidom here instead of Element Tree.

    The format for paravier input file is decirbed in paraview_file_format.pdf in the doc folder of HABBY.

    The data of the paraview file created here  is usually not in a binary form, but it could be put in binary if the
    switch binary_data is True. However, this part just does not work for now. The idea of paraview for a binary file is
    to keep the same usual xml file. The data is encoding to base64 and adding in the tag in a binaray form in a CDATA
    element. However, somthing do not work yet.

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
    :param binary_data: If True will create binary data. DO NOT WORK YET, let it to FALSE

    """
    file_names_all = []
    file_name_base = os.path.join(path_out, file_name_base)

    # format thename of species and stage
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # load grid
    [ikle_all_t, point_all_t, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_hdf5, path_hdf5, True)
    if ikle_all_t == [-99]:
        return

    # create one group of files (pwd) by reach
    for r in range(0, len(ikle_all_t[0])):
        fileName = file_name_base + '_' + 'Reach' + str(r) + '_'

        # create one vtu file by time step
        # for the moment we do not show the time step zero with the full profile without data
        # to show it, change (1, to (0,
        for t in range(1, len(ikle_all_t)):
            ikle = ikle_all_t[t][0]
            if len(ikle) < 3:  # if something is wrong
                pass
            else:
                point = np.array(point_all_t[t][0])

                x = point[:, 0]
                y = point[:, 1]
                z = np.zeros(len(x), )

                # Document and root element
                doc = xml.dom.minidom.Document()
                root_element = doc.createElementNS("VTK", "VTKFile")
                root_element.setAttribute("type", "UnstructuredGrid")
                root_element.setAttribute("version", "0.1")
                root_element.setAttribute("byte_order", "LittleEndian")
                doc.appendChild(root_element)

                # Unstructured grid element
                unstructuredGrid = doc.createElementNS("VTK", "UnstructuredGrid")
                root_element.appendChild(unstructuredGrid)

                # Piece 0 (only one)
                piece = doc.createElementNS("VTK", "Piece")
                piece.setAttribute("NumberOfPoints", str(len(x)))
                piece.setAttribute("NumberOfCells", str(len(ikle)))
                unstructuredGrid.appendChild(piece)

                # Points
                points = doc.createElementNS("VTK", "Points")
                piece.appendChild(points)

                # Point location data
                point_coords = doc.createElementNS("VTK", "DataArray")
                point_coords.setAttribute("type", "Float32")
                point_coords.setAttribute("Name", "Position")
                if binary_data:
                    point_coords.setAttribute("format", "binary")
                else:
                    point_coords.setAttribute("format", "ascii")
                point_coords.setAttribute("NumberOfComponents", "3")
                points.appendChild(point_coords)

                # Point data (empty)
                string = coords_to_string(x, y, z)
                if binary_data:
                    string = base64.b64encode(bytes(string, 'utf8'))
                    cdata = doc.createCDATASection(string)
                    point_coords.appendChild(cdata)
                else:
                    point_coords_data = doc.createTextNode(string)
                    point_coords.appendChild(point_coords_data)
                point_data = doc.createElementNS("VTK", "PointData")
                piece.appendChild(point_data)

                # Cells
                cells = doc.createElementNS("VTK", "Cells")
                piece.appendChild(cells)

                # Cell connectivity (ikle)
                cell_connectivity = doc.createElementNS("VTK", "DataArray")
                cell_connectivity.setAttribute("type", "Int32")
                cell_connectivity.setAttribute("Name", "connectivity")
                if binary_data:
                    cell_connectivity.setAttribute("format", "binary")
                else:
                    cell_connectivity.setAttribute("format", "ascii")
                cells.appendChild(cell_connectivity)
                string = coords_to_string(ikle[:, 0], ikle[:, 1], ikle[:, 2])
                if binary_data:
                    string = str(base64.b64encode(bytes(string, 'utf8')))
                connectivity = doc.createTextNode(string)
                cell_connectivity.appendChild(connectivity)

                # offset for cells
                cell_offsets = doc.createElementNS("VTK", "DataArray")
                cell_offsets.setAttribute("type", "Int32")
                cell_offsets.setAttribute("Name", "offsets")
                if binary_data:
                    cell_offsets.setAttribute("format", "binary")
                else:
                    cell_offsets.setAttribute("format", "ascii")
                cells.appendChild(cell_offsets)
                offset = np.arange(3,len(ikle)*3+3, 3)
                offset = list(map(int, offset))
                string = array_to_string(offset)
                if binary_data:
                    string = base64.b64encode(bytes(string, 'utf8'))
                    cdata = doc.createCDATASection(string)
                    cell_offsets.appendChild(cdata)
                else:
                    offsets = doc.createTextNode(string)
                cell_offsets.appendChild(offsets)

                # type of cells
                cell_types = doc.createElementNS("VTK", "DataArray")
                cell_types.setAttribute("type", "UInt8")
                cell_types.setAttribute("Name", "types")
                if binary_data:
                    cell_types.setAttribute("format", "binary")
                else:
                    cell_types.setAttribute("format", "ascii")
                cells.appendChild(cell_types)
                types_cell = np.zeros(len(ikle), ) + 5  # triangle
                string = array_to_string(list(map(int, types_cell)))
                if binary_data:
                    string = str(base64.b64encode(bytes(string, 'utf8')))
                types = doc.createTextNode(string)
                cell_types.appendChild(types)

                if t > 0: # timestep 0 is whole prfile without data

                    # Data on Cell
                    cell_data = doc.createElementNS("VTK", "CellData")
                    piece.appendChild(cell_data)

                    # hhabitat suitability index for each speciace
                    for sp in range(0, len(vh_all_t_sp)):
                        forces = doc.createElementNS("VTK", "DataArray")
                        forces.setAttribute("Name", "HSI " + name_fish[sp])
                        forces.setAttribute("NumberOfComponents", "1")
                        forces.setAttribute("type", "Float32")
                        if binary_data:
                            forces.setAttribute("format", "binary")
                        else:
                            forces.setAttribute("format", "ascii")
                        cell_data.appendChild(forces)
                        string = array_to_string(vh_all_t_sp[sp][t][r])
                        if binary_data:
                            string = str(base64.b64encode(bytes(string, 'utf8')))
                        forces_Data = doc.createTextNode(string)
                        forces.appendChild(forces_Data)

                    # height
                    forces = doc.createElementNS("VTK", "DataArray")
                    forces.setAttribute("Name", "Water heigth [m]")
                    forces.setAttribute("NumberOfComponents", "1")
                    forces.setAttribute("type", "Float32")
                    if binary_data:
                        forces.setAttribute("format", "binary")
                    else:
                        forces.setAttribute("format", "ascii")
                    cell_data.appendChild(forces)
                    string = array_to_string(height_c_data[t][r])
                    if binary_data:
                        string = str(base64.b64encode(bytes(string, 'utf8')))
                    forces_Data = doc.createTextNode(string)
                    forces.appendChild(forces_Data)

                    # velocity
                    forces = doc.createElementNS("VTK", "DataArray")
                    forces.setAttribute("Name", "Velocity [m/s]")
                    forces.setAttribute("NumberOfComponents", "1")
                    forces.setAttribute("type", "Float32")
                    if binary_data:
                        forces.setAttribute("format", "binary")
                    else:
                        forces.setAttribute("format", "ascii")
                    cell_data.appendChild(forces)
                    string = array_to_string(vel_c_data[t][r])
                    if binary_data:
                        string = str(base64.b64encode(bytes(string, 'utf8')))
                    forces_Data = doc.createTextNode(string)
                    forces.appendChild(forces_Data)

                    # pg substrate
                    forces = doc.createElementNS("VTK", "DataArray")
                    forces.setAttribute("Name", "Coarser Substrate")
                    forces.setAttribute("NumberOfComponents", "1")
                    forces.setAttribute("type", "Float32")
                    if binary_data:
                        forces.setAttribute("format", "binary")
                    else:
                        forces.setAttribute("format", "ascii")
                    cell_data.appendChild(forces)
                    string = array_to_string(sub_pg_data[t][r])
                    if binary_data:
                        string = str(base64.b64encode(bytes(string, 'utf8')))
                    forces_Data = doc.createTextNode(string)
                    forces.appendChild(forces_Data)

                    # dominant substrate
                    forces = doc.createElementNS("VTK", "DataArray")
                    forces.setAttribute("Name", "Dominant Substrate")
                    forces.setAttribute("NumberOfComponents", "1")
                    forces.setAttribute("type", "Float32")
                    if binary_data:
                        forces.setAttribute("format", "binary")
                    else:
                        forces.setAttribute("format", "ascii")
                    cell_data.appendChild(forces)
                    string = array_to_string(sub_dom_data[t][r])
                    if binary_data:
                        string = str(base64.b64encode(bytes(string, 'utf8')))
                    forces_Data = doc.createTextNode(string)
                    forces.appendChild(forces_Data)

                # Write to file and exit
                outFile = open(fileName+str(t) + '.vtu', 'w')
                #        xml.dom.ext.PrettyPrint(doc, file)
                doc.writexml(outFile, newl='\n')
                outFile.close()
                file_names_all.append(fileName+str(t)+'.vtu')

        writePVD(fileName + '.pvd', file_names_all)


def writePVD(fileName, fileNames):
    outFile = open(fileName, 'w')
    import xml.dom.minidom

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

def coords_to_string(x, y, z):
    string = str()
    for i in range(len(x)):
        string = string + repr(x[i]) + ' ' + repr(y[i]) \
                 + ' ' + repr(z[i]) + ' '
    return string


def array_to_string(a):
    """
    Pass an array to a string. Taken from
    https://github.com/cfinch/Shocksolution_Examples/blob/master/Visualization/vtktools.py
    :param a: the arrat
    :return: a string
    """
    string = str()
    for i in range(len(a)):
        string = string + repr(a[i]) + ' '
    return string

def main():
    path_hdf5 = r'D:\Diane_work\dummy_folder\Projet1\fichier_hdf5'
    name_hdf5 = r'MERGE_Hydro_RUBAR2D_BS15a621_03_2017_at_10_15_45.h5'
    blob = None
    path_vtk = r'D:\Diane_work\dummy_folder\res_vtk'
    fileName = os.path.join(path_vtk,'test')

    habitat_to_vtu(fileName, path_hdf5, name_hdf5, blob, blob, blob)


if __name__ == '__main__':
    main()