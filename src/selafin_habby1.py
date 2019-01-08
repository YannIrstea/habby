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
from struct import unpack, pack
import numpy as np
import os
import sys
import warnings
import matplotlib.pyplot as plt
import time
from io import StringIO
from src import load_hdf5
from src_GUI import output_fig_GUI
from src import manage_grid_8


def load_telemac_and_cut_grid(name_hdf5, namefilet, pathfilet, name_prj, path_prj, model_type, nb_dim, path_hdf5,
                              progress_value,
                              units_index=None, q=[],
                              print_cmd=False, fig_opt={}):
    """
    This function calls the function load_telemac and call the function cut_2d_grid(). Orginally, this function
    was part of the TELEMAC class in Hydro_GUI_2.py but it was separated to be able to have a second thread, which
    is useful to avoid freezing the GUI.

    :param name_hdf5: the base name of the created hdf5 (string)
    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param units_index : List of integer values representing index of units (timestep or discharge). If not specify,
            all timestep are selected (from cmd command).
    :param q: used by the second thread to get the error back to the GUI at the end of the thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param fig_opt: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    """
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    minwh = fig_opt['min_height_hyd']

    # progress
    progress_value.value = 10

    # load data
    if not units_index:  # all timestep are selected
        [v, h, coord_p, ikle, coord_c, timestep] = load_telemac(namefilet, pathfilet)
        units_index = list(range(len(timestep)))
    if units_index:  # timestep selected by user are selected
        [v, h, coord_p, ikle, coord_c, timestep] = load_telemac(namefilet, pathfilet)
        timestep = timestep[units_index]

    if isinstance(v, int) and v == [-99]:
        print('Error: Telemac data not loaded.')
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # cut the grid to have the precise wet area and put data in new form
    point_all_t = [[coord_p]]
    ikle_all_t = [[ikle]]
    point_c_all_t = [[coord_c]]
    inter_h_all_t = [[]]
    inter_vel_all_t = [[]]

    # from 10 to 90
    # from 0 to len(units_index)
    delta = 80 / len(units_index)
    if len(units_index) == 1:
        delta = 80 / 2
    prog = 10
    for t in units_index:
        prog += delta
        progress_value.value = int(prog)
        [ikle2, point_all, water_height, velocity] = manage_grid_8.cut_2d_grid(ikle, coord_p, h[t], v[t], minwh)
        point_all_t.append([point_all])  # only one reach
        ikle_all_t.append([ikle2])
        point_c_all_t.append([[]])
        inter_vel_all_t.append([velocity])
        inter_h_all_t.append([water_height])

    # progress
    progress_value.value = 90

    # save data
    timestep_str = list(map(str, timestep))
    load_hdf5.save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5, ikle_all_t,
                                      point_all_t, point_c_all_t,
                                      inter_vel_all_t, inter_h_all_t, sim_name=timestep_str, hdf5_type="hydraulic")

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_telemac(namefilet, pathfilet):
    """
    A function which load the telemac data using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: the velocity, the height, the coordinate of the points of the grid, the connectivity table.
    """
    faiload = [-99], [-99], [-99], [-99], [-99], [-99]

    filename_path_res = os.path.join(pathfilet, namefilet)
    # load the data and do some test
    if not os.path.isfile(filename_path_res):
        print('Error: The telemac file does not exist. Cannot be loaded.')
        return faiload
    blob, ext = os.path.splitext(namefilet)
    if ext != '.res' and ext != '.slf':
        print('Warning: The extension of the telemac file is not .res or .slf')
    try:
        telemac_data = Selafin(filename_path_res)
    except ValueError or KeyError:
        print('Error: The telemac file cannot be loaded.')
        return faiload

    # time step name
    nbtimes = telemac_data.tags['times'].size
    timestep = telemac_data.tags['times']

    # put the velocity and height data in the array and list
    v = []
    h = []
    for t in range(0, nbtimes):
        foundu = foundv = False
        val_all = telemac_data.getvalues(t)
        vt = []
        ht = []

        # load variable based on their name (english or french)
        for id, n in enumerate(telemac_data.varnames):
            n = n.decode('utf-8')
            if 'VITESSE MOY' in n or 'MEAN VELOCITY' in n:
                vt = val_all[:, id]
            if 'VITESSE U' in n or 'VELOCITY U' in n:
                vu = val_all[:, id]
                foundu = True
            if 'VITESSE V' in n or 'VELOCITY V' in n:
                vv = val_all[:, id]
                foundv = True
            if 'WATER DEPTH' in n or "HAUTEUR D'EAU" in n:
                ht = val_all[:, id]
            if 'FOND' in n or 'BOTTOM' in n:
                bt = val_all[:, id]

        if foundu and foundv:
            vt = np.sqrt(vu ** 2 + vv ** 2)

        if len(vt) == 0:
            print('Error: The variable name of the telemec file were not recognized. (1) \n')
            return faiload
        if len(ht) == 0:
            print('Error: The variable name of the telemec file were not recognized. (2) \n')
            return faiload
        v.append(vt)
        h.append(ht)
    coord_p = np.array([telemac_data.meshx, telemac_data.meshy])
    coord_p = coord_p.T
    ikle = telemac_data.ikle2

    # get the center of the cell
    # center of element
    p1 = coord_p[ikle[:, 0], :]
    p2 = coord_p[ikle[:, 1], :]
    p3 = coord_p[ikle[:, 2], :]
    coord_c_x = 1.0 / 3.0 * (p1[:, 0] + p2[:, 0] + p3[:, 0])
    coord_c_y = 1.0 / 3.0 * (p1[:, 1] + p2[:, 1] + p3[:, 1])
    coord_c = np.array([coord_c_x, coord_c_y]).T

    del telemac_data
    return v, h, coord_p, ikle, coord_c, timestep


def get_time_step(namefilet, pathfilet):
    """
    A function which load the telemac time step using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: timestep
    """
    faiload = [-99], [-99], [-99], [-99], [-99], [-99]

    filename_path_res = os.path.join(pathfilet, namefilet)
    # load the data and do some test
    if not os.path.isfile(filename_path_res):
        print('Error: The telemac file does not exist. Cannot be loaded.')
        return faiload
    blob, ext = os.path.splitext(namefilet)
    if ext != '.res' and ext != '.slf':
        print('Warning: The extension of the telemac file is not .res or .slf')
    try:
        telemac_data = Selafin(filename_path_res)
    except ValueError or KeyError:
        print('Error: The telemac file cannot be loaded.')
        return faiload

    # time step name
    nbtimes = telemac_data.tags['times'].size
    timestep = telemac_data.tags['times']
    timestep_string = []
    for i in range(len(timestep)):
        timestep_string.append(str(timestep[i]))

    return nbtimes, timestep_string


def plot_vel_h(coord_p2, h, v, path_im, timestep=[-1]):
    """
     a function to plot the velocity and height which are the output from TELEMAC. It is used to debug.
     It is not used direclty by HABBY.

     :param coord_p2: the coordinates of the point forming the grid
     :param h: the  water height
     :param v: the velocity
     :param path_im: the path where the image should be saved (string)
     :param timestep: which time step should be plotted
    """
    # plt.rcParams['figure.figsize'] = 7, 3
    # plt.close()
    plt.rcParams['font.size'] = 10

    for i in timestep:
        plt.figure()
        cm = plt.cm.get_cmap('terrain')
        sc = plt.scatter(coord_p2[:, 0], coord_p2[:, 1], c=h[i], vmin=np.nanmin(h[i]), vmax=np.nanmax(h[i]), s=6,
                         cmap=cm,
                         edgecolors='none')
        # sc = plt.tricontourf(coord_p2[:,0], coord_p2[:,1], ikle_all[r], h[i], min=0, max=np.nanmax(h[i]), cmap=cm)
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Telemac data - water height at time step ' + str(i))
        cbar = plt.colorbar()
        cbar.ax.set_ylabel('Water height [m]')
        plt.savefig(os.path.join(path_im, "telemac_height_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'))
        plt.savefig(os.path.join(path_im, "telemac_height_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'))
        # plt.close()

        plt.figure()
        cm = plt.cm.get_cmap('terrain')
        sc = plt.scatter(coord_p2[:, 0], coord_p2[:, 1], c=v[i], vmin=np.nanmin(v[i]), vmax=np.nanmax(v[i]), s=6,
                         cmap=cm,
                         edgecolors='none')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Telemac data - velocity at time step ' + str(i))
        cbar = plt.colorbar()
        cbar.ax.set_ylabel('Velocity [m/s]')
        plt.savefig(os.path.join(path_im, "telemac_vel_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'))
        plt.savefig(os.path.join(path_im, "telemac_vel_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'))
        # plt.close()
    # plt.show()


def getendianfromchar(fileslf, nchar):
    """
    Get the endian encoding
        "<" means little-endian
        ">" means big-endian
    """
    pointer = fileslf.tell()
    endian = ">"
    l, c, chk = unpack(endian + 'i' + str(nchar) + 'si', \
                       fileslf.read(4 + nchar + 4))
    if chk != nchar:
        endian = "<"
        fileslf.seek(pointer)
        l, c, chk = unpack(endian + 'i' + str(nchar) + 'si', \
                           fileslf.read(4 + nchar + 4))
    if l != chk:
        print('Error: ... Cannot read ' + str(nchar) + \
              ' characters from your binary file')
        print('     +> Maybe it is the wrong file format ?')
    fileslf.seek(pointer)
    return endian


def getfloattypefromfloat(fileslf, endian, nfloat):
    """
    Get float precision
    """
    pointer = fileslf.tell()
    ifloat = 4
    cfloat = 'f'
    l = unpack(endian + 'i', fileslf.read(4))
    if l[0] != ifloat * nfloat:
        ifloat = 8
        cfloat = 'd'
    r = unpack(endian + str(nfloat) + cfloat, fileslf.read(ifloat * nfloat))
    chk = unpack(endian + 'i', fileslf.read(4))
    if l != chk:
        print('Error: ... Cannot read ' + str(nfloat) + ' floats from your binary file')
        print('     +> Maybe it is the wrong file format ?')
    fileslf.seek(pointer)
    return cfloat, ifloat


class Selafin(object):
    """
    Selafin file format reader for Telemac 2D. Create an object for reading data from a slf file.
    Adapted from the original script 'parserSELAFIN.py' from the open Telemac distribution.

    :param filename: the name of the binary Selafin file
    """

    def __init__(self, filename):
        self.file = {}
        self.file.update({'name': filename})
        # "<" means little-endian, ">" means big-endian
        self.file.update({'endian': ">"})
        self.file.update({'float': ('f', 4)})  # 'f' size 4, 'd' = size 8
        self.datetime = [0, 0, 0, 0, 0, 0]
        if filename != '':
            self.file.update({'hook': open(filename, 'rb')})
            # ~~> checks endian encoding
            self.file['endian'] = getendianfromchar(self.file['hook'], 80)
            # ~~> header parameters
            self.tags = {'meta': self.file['hook'].tell()}
            self.getheadermetadataslf()
            # ~~> sizes and connectivity
            self.getheaderintegersslf()
            # ~~> checks float encoding
            self.file['float'] = getfloattypefromfloat(self.file['hook'], \
                                                       self.file['endian'], self.npoin3)
            # ~~> xy mesh
            self.getheaderfloatsslf()
            # ~~> time series
            self.tags = {'cores': [], 'times': []}
            self.gettimehistoryslf()
        else:
            self.title = ''
            self.nbv1 = 0
            self.nbv2 = 0
            self.nvar = self.nbv1 + self.nbv2
            self.varindex = range(self.nvar)
            self.iparam = []
            self.nelem3 = 0
            self.npoin3 = 0
            self.ndp3 = 0
            self.nplan = 1
            self.nelem2 = 0
            self.npoin2 = 0
            self.ndp2 = 0
            self.nbv1 = 0
            self.varnames = []
            self.varunits = []
            self.nbv2 = 0
            self.cldnames = []
            self.cldunits = []
            self.ikle3 = []
            self.ikle2 = []
            self.ipob2 = []
            self.ipob3 = []
            self.meshx = []
            self.meshy = []
            self.tags = {'cores': [], 'times': []}
        self.fole = {}
        self.fole.update({'name': ''})
        self.fole.update({'endian': self.file['endian']})
        self.fole.update({'float': self.file['float']})
        self.tree = None
        self.neighbours = None
        self.edges = None

    def getheadermetadataslf(self):
        """
        Get header information
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        # ~~ Read title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        l, self.title, chk = unpack(endian + 'i80si', fileslf.read(4 + 80 + 4))
        # ~~ Read NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        l, self.nbv1, self.nbv2, chk = \
            unpack(endian + 'iiii', fileslf.read(4 + 8 + 4))
        self.nvar = self.nbv1 + self.nbv2
        self.varindex = range(self.nvar)
        # ~~ Read variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.varnames = []
        self.varunits = []
        for _ in range(self.nbv1):
            l, vn, vu, chk = unpack(endian + 'i16s16si', \
                                    fileslf.read(4 + 16 + 16 + 4))
            self.varnames.append(vn)
            self.varunits.append(vu)
        self.cldnames = []
        self.cldunits = []
        for _ in range(self.nbv2):
            l, vn, vu, chk = unpack(endian + 'i16s16si', \
                                    fileslf.read(4 + 16 + 16 + 4))
            self.cldnames.append(vn)
            self.cldunits.append(vu)
        # ~~ Read iparam array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        d = unpack(endian + '12i', fileslf.read(4 + 40 + 4))
        self.iparam = np.asarray(d[1:11])
        # ~~ Read DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if self.iparam[9] == 1:
            d = unpack(endian + '8i', fileslf.read(4 + 24 + 4))
            self.datetime = np.asarray(d[1:9])

    def getheaderintegersslf(self):
        """
        Get dimensions and descritions (mesh)
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        # ~~ Read nelem3, npoin3, ndp3, nplan ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        l, self.nelem3, self.npoin3, self.ndp3, self.nplan, chk = \
            unpack(endian + '6i', fileslf.read(4 + 16 + 4))
        self.nelem2 = self.nelem3
        self.npoin2 = self.npoin3
        self.ndp2 = self.ndp3
        self.nplan = max(1, self.nplan)
        if self.iparam[6] > 1:
            self.nplan = self.iparam[6]  # /!\ How strange is that ?
            self.nelem2 = self.nelem3 / (self.nplan - 1)
            self.npoin2 = self.npoin3 / self.nplan
            self.ndp2 = self.ndp3 / 2
        # ~~ Read the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        fileslf.seek(4, 1)
        self.ikle3 = np.array(unpack(endian + str(self.nelem3 * self.ndp3) \
                                     + 'i', fileslf.read(4 * self.nelem3 * self.ndp3))) - 1
        fileslf.seek(4, 1)
        self.ikle3 = self.ikle3.reshape((self.nelem3, self.ndp3))
        if self.nplan > 1:
            self.ikle2 = np.compress(np.repeat([True, False], self.ndp2), \
                                     self.ikle3[0:self.nelem2], axis=1)
        else:
            self.ikle2 = self.ikle3
        # ~~ Read the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        fileslf.seek(4, 1)
        self.ipob3 = np.asarray(unpack(endian + str(self.npoin3) + 'i', \
                                       fileslf.read(4 * self.npoin3)))
        fileslf.seek(4, 1)
        self.ipob2 = self.ipob3[0:self.npoin2]

    def getheaderfloatsslf(self):
        """
        Get the mesh coordinates
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        # ~~ Read the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
        ftype, fsize = self.file['float']
        fileslf.seek(4, 1)
        self.meshx = np.asarray(unpack(endian + str(self.npoin3) + ftype, \
                                       fileslf.read(fsize * self.npoin3))[0:self.npoin2])
        fileslf.seek(4, 1)
        # ~~ Read the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
        fileslf.seek(4, 1)
        self.meshy = np.asarray(unpack(endian + str(self.npoin3) + ftype, \
                                       fileslf.read(fsize * self.npoin3))[0:self.npoin2])
        fileslf.seek(4, 1)

    def gettimehistoryslf(self):
        """
        Get the timesteps
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        ftype, fsize = self.file['float']
        ats = []
        att = []
        while True:
            try:
                att.append(fileslf.tell())
                # ~~ Read AT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                fileslf.seek(4, 1)
                ats.append(unpack(endian + ftype, fileslf.read(fsize))[0])
                fileslf.seek(4, 1)
                # ~~ Skip Values ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                fileslf.seek(self.nvar * (4 + fsize * self.npoin3 + 4), 1)
            except:
                att.pop(len(att) - 1)  # since the last record failed the try
                break
        self.tags.update({'cores': att})
        self.tags.update({'times': np.asarray(ats)})

    def getvariablesat(self, frame, varindexes):
        """
        Get the values for the variables at a particular time step
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        ftype, fsize = self.file['float']
        if fsize == 4:
            z = np.zeros((len(varindexes), self.npoin3), dtype=np.float32)
        else:
            z = np.zeros((len(varindexes), self.npoin3), dtype=np.float64)
        # if tags has 31 frames, len(tags)=31 from 0 to 30,
        # then frame should be >= 0 and < len(tags)
        if frame < len(self.tags['cores']) and frame >= 0:
            fileslf.seek(self.tags['cores'][frame])
            fileslf.seek(4 + fsize + 4, 1)
            for ivar in range(self.nvar):
                fileslf.seek(4, 1)
                if ivar in varindexes:
                    z[varindexes.index(ivar)] = unpack(endian + \
                                                       str(self.npoin3) + ftype, \
                                                       fileslf.read(fsize * self.npoin3))
                else:
                    fileslf.seek(fsize * self.npoin3, 1)
                fileslf.seek(4, 1)
        return z

    def getvalues(self, t):
        """
        Get the values for the variables at time t
        """
        varsor = self.getvariablesat(t, self.varindex)
        return varsor.transpose()

    def appendheaderslf(self):
        """
        Write the header file
        """
        f = self.fole['hook']
        endian = self.fole['endian']
        ftype, fsize = self.fole['float']
        # ~~ Write title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i80si', 80, self.title, 80))
        # ~~ Write NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'iiii', 4 + 4, self.nbv1, self.nbv2, 4 + 4))
        # ~~ Write variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for i in range(self.nbv1):
            f.write(pack(endian + 'i', 32))
            f.write(pack(endian + '16s', self.varnames[i]))
            f.write(pack(endian + '16s', self.varunits[i]))
            f.write(pack(endian + 'i', 32))
        for i in range(self.nbv2):
            f.write(pack(endian + 'i', 32))
            f.write(pack(endian + '16s', self.cldnames[i]))
            f.write(pack(endian + '16s', self.cldunits[i]))
            f.write(pack(endian + 'i', 32))
        # ~~ Write IPARAM array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', 4 * 10))
        for i in range(len(self.iparam)):
            f.write(pack(endian + 'i', self.iparam[i]))
        f.write(pack(endian + 'i', 4 * 10))
        # ~~ Write DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if self.iparam[9] == 1:
            f.write(pack(endian + 'i', 4 * 6))
            for i in range(6):
                f.write(pack(endian + 'i', self.datetime[i]))
            f.write(pack(endian + 'i', 4 * 6))
        # ~~ Write NELEM3, NPOIN3, NDP3, NPLAN ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + '6i', 4 * 4, self.nelem3, self.npoin3, \
                     self.ndp3, 1, 4 * 4))  # /!\ where is NPLAN ?
        # ~~ Write the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', 4 * self.nelem3 * self.ndp3))
        f.write(pack(endian + str(self.nelem3 * self.ndp3) + 'i', *(self.ikle3.ravel() + 1)))
        f.write(pack(endian + 'i', 4 * self.nelem3 * self.ndp3))
        # ~~ Write the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', 4 * self.npoin3))
        f.write(pack(endian + str(self.npoin3) + 'i', *(self.ipob3)))
        f.write(pack(endian + 'i', 4 * self.npoin3))
        # ~~ Write the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', fsize * self.npoin3))
        # f.write(pack(endian+str(self.NPOIN3)+ftype,*(np.tile(self.MESHX,self.NPLAN))))
        for i in range(self.nplan):
            f.write(pack(endian + str(self.npoin2) + ftype, *(self.meshx)))
        f.write(pack(endian + 'i', fsize * self.npoin3))
        # ~~ Write the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', fsize * self.npoin3))
        # f.write(pack(endian+str(self.NPOIN3)+ftype,*(np.tile(self.MESHY,self.NPLAN))))
        for i in range(self.nplan):
            f.write(pack(endian + str(self.npoin2) + ftype, *(self.meshy)))
        f.write(pack(endian + 'i', fsize * self.npoin3))

    def appendcoretimeslf(self, t):
        f = self.fole['hook']
        endian = self.fole['endian']
        ftype, fsize = self.fole['float']
        # Print time record
        # if type(t) == type(0.0):
        f.write(pack(endian + 'i' + ftype + 'i', fsize, t, fsize))
        # else:
        #    f.write(pack(endian + 'i' + ftype + 'i', fsize, self.tags['times'][t], fsize))

    def appendcorevarsslf(self, varsor):
        f = self.fole['hook']
        endian = self.fole['endian']
        ftype, fsize = self.fole['float']
        # Print variable records
        for v in varsor.transpose():
            f.write(pack(endian + 'i', fsize * self.npoin3))
            f.write(pack(endian + str(self.npoin3) + ftype, *(v)))
            f.write(pack(endian + 'i', fsize * self.npoin3))

    def putcontent(self, fileName, times, values):
        self.fole.update({'name': fileName})
        self.fole.update({'hook': open(fileName, 'wb')})
        self.appendheaderslf()
        npoin = self.npoin2
        nbrow = values.shape[0]
        if nbrow % npoin != 0:
            raise Exception(u'The number of values is not equal to the number of nodes : %d' % npoin)
        for i in range(times.size):
            self.appendcoretimeslf(times[i])
            self.appendcorevarsslf(values[i * npoin:(i + 1) * npoin, :])
        self.fole.update({'hook': self.fole['hook'].close()})

    def addcontent(self, fileName, times, values):
        self.fole.update({'hook': open(fileName, 'ab')})
        npoin = self.npoin2
        nbrow = values.shape[0]
        if nbrow % npoin != 0:
            raise Exception(u'The number of values is not equal to the number of nodes : %d' % npoin)
        for i in range(times.size):
            self.appendcoretimeslf(times[i])
            self.appendcorevarsslf(values[i * npoin:(i + 1) * npoin, :])
        self.fole.update({'hook': self.fole['hook'].close()})

    def __del__(self):
        """
        Destructor method
        """
        if self.file['name'] != '':
            self.file.update({'hook': self.file['hook'].close()})


if __name__ == "__main__":
    namefile = 'mersey.res'
    pathfile = r'D:\Diane_work\output_hydro\telemac_py'
    [v, h, coord_p, ikle, coord_c] = load_telemac(namefile, pathfile)
    plot_vel_h(coord_p, h, v)
