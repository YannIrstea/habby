import sys
import os
import time
import glob
import matplotlib.pyplot as plt
from src import selafin_habby1
from src import mascaret
from src import Hec_ras06
from src import rubar
from src import func_for_cmd
from src import river2d
from src import load_hdf5
from shutil import copyfile
from src import hec_ras2D
from src import estimhab
from src import stathab_c
from src import substrate


def all_command(all_arg, name_prj, path_prj, path_bio):
    """
    This function is used to call HABBY from the command line. The general form is to call:
    habby_cmd command_name input1 input2 .. input n. The list of the command_name is given in the documentation and by
    calling the command "python habby_cmd.py LIST_COMMAND". This functiion is usually called direclty by the main()
    or it is called by the function restart which read a list of function line by line. Careful, new command cannot
    contain the symbol ":" as it is used by restart.

    :param all_arg: the list of argument (sys.argv more or less)
    :param name_prj: the name of the project, created by default by the main()
    :param path_prj: the path to the project created by default bu the main()
    :param path_bio: the path to the project

    """
    # all_arg[0] is the script name (habby_cmd.py)

    # ----------------------------------------------------------------------------------

    if all_arg[1] == 'LIST_COMMAND':
        print("Here are the available command for habby:")
        print('\n')
        print("LOAD_HECRAS_1D: load the hec-ras data in 1D. Input: name of .geo, name of the data file, interpolation "
              "choice,(number of profile to add), (output name)")
        print("LOAD_HECRAS_2D: load the hec-ras data in 2D. Input: name of the .h5 file, (output name)")
        print("LOAD_MASCARET: load the mascaret data. Input: name of the three inputs files - xcas, geo, opt, "
              "manning coefficient, interpolation choice, (number of profile to add), (output name), (nb_point_vel=x)")
        print("LOAD_RIVER_2D: load the river 2d data. Input folder containing the cdg file, (output name)")
        print("LOAD_RUBAR_1D: load the Rubar data in 1D. Input: name of input file .rbe, name of the profile input "
              "file, manning coefficient, interpolation choice, (number of profile to add), (output name),"
              "(nb_point_vel=x)")
        print("LOAD_RUBAR2D: load the Rubar data in 2D. Input: name of input file 1, name of input file 2, (output)")
        print("LOAD_TELEMAC: load the telemac data. Input: name of the .res file, (output name)")
        print('LOAD_HYDRO_HDF5: load an hydrological hdf5. Input: the name of the hdf5 (with the path)')

        print('\n')
        print('MERGE_GRID: merge the hydrological and substrate grid together. Input: the name of the hydrological hdf5'
              ', the name of the substrate hdf5, the default data for the substrate (in cemagref code), (output name)')
        print('LOAD_SUB_SHP: load the substrate from a shapefile. Input: filename of the shapefile,'
              'code_type as Cemagref or Sandre, (dominant_case as 1 or -1)')
        print('LOAD_SUB_TXT: load the substrate from a text file. Input: filename of the shapefile,'
              'code_type as Cemagref or Sandre')
        print('LOAD_SUB_HDF5: load the substrate data in an hdf5 form. Input: the name of the hdf5 file (with path)')

        print('\n')
        print("RUN_STATHAB: Run the stathab model. Need the path to the folder with the different input files.")
        print('RUN_ESTIMHAB: Run the estimhab model. Input: qmes1 qmes2 wmes1 wmes2 h1mes h2mes q50 qmin qmax sub'
              '- all data in float')

        print('\n')
        print("RESTART: Relauch HABBY based on a list of command in a text file (restart file) Input: the name of file"
              " (with the path).")

# ------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_TELEMAC':
        # check
        if not 2 < len(all_arg) < 5:
            print('The function LOAD_TELEMAC needs one or two inputs, the .res file name and the output name.')
            return
        # get filename
        filename = all_arg[2]
        pathfilet = os.path.dirname(filename)
        namefilet = os.path.basename(filename)

        # hdf5
        if len(all_arg) == 4:
            namepath_hdf5 = all_arg[3]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)
        else:
            name_hdf5 = 'Hydro_TELEMAC_' + namefilet
            path_hdf5 = '.'

        selafin_habby1.load_telemac_and_cut_grid(name_hdf5, namefilet, pathfilet, name_prj, path_prj, 'TELEMAC',2,
                                                 path_hdf5,[], True)

# ------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_HECRAS_1D':
        if not 4 < len(all_arg) < 8:
            print('The function LOAD_HECRAS needs three to five inputs. Call LIST_COMMAND for more '
                  'information.')
            return

        # get filename
        filename_geo = all_arg[2]
        filename_data = all_arg[3]
        pathfile = [os.path.dirname(filename_geo), os.path.dirname(filename_data)]
        namefile = [os.path.basename(filename_geo), os.path.basename(filename_data)]

        # hdf5 and pro_add
        pro_add_is_here = False
        if len(all_arg) == 5:  # .py com f1 f2 int_type
            name_hdf5 = 'Hydro_HECRAS1D_' + namefile[0]
            path_hdf5 = '.'
        if len(all_arg) == 6:  # .py com f1 f2 int_type pro_add or .py com f1 f2 int_type output
            try:
                pro_add_is_here = True
                pro_add = int(all_arg[5])
            except ValueError:
                pass
            if not pro_add_is_here:
                namepath_hdf5 = all_arg[5]
                name_hdf5 = os.path.basename(namepath_hdf5)
                path_hdf5 = os.path.dirname(namepath_hdf5)
            else:
                name_hdf5 = 'Hydro_HECRAS1D_' + namefile[0]
                path_hdf5 = '.'
        if len(all_arg) == 7:   # .py com f1 f2 int_type pro_add output
            pro_add_is_here = True
            pro_add = int(all_arg[5])
            namepath_hdf5 = all_arg[6]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)

        #interpo
        try:
            inter = int(all_arg[4])
        except ValueError:
            print('Error: Interpolation type should be 0, 1, 2')
            return

        if pro_add_is_here:
            Hec_ras06.open_hec_hec_ras_and_create_grid(name_hdf5, path_hdf5, name_prj, path_prj, 'HECRAS1D', namefile,
                                                       pathfile,inter , '.', False, pro_add,[], True)
        else:
            Hec_ras06.open_hec_hec_ras_and_create_grid(name_hdf5, path_hdf5, name_prj, path_prj, 'HECRAS1D', namefile,
                                                       pathfile, inter, '.', False, 5 , [] , True)

# --------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_HECRAS_2D':
        if not 2 < len(all_arg) < 5:
            print('The function LOAD_HECRAS_2D needs one or two inputs, the .res file name and the output name.')
            return
        # get filename
        filename = all_arg[2]
        pathfile = os.path.dirname(filename)
        namefile = os.path.basename(filename)

        if len(all_arg) == 4:
            namepath_hdf5 = all_arg[3]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)
        else:
            name_hdf5 = 'Hydro_HECRAS2D_' + namefile
            path_hdf5 = '.'
        hec_ras2D.load_hec_ras_2d_and_cut_grid(name_hdf5, filename, pathfile, name_prj, path_prj, 'HECRAS2D', 2,
                                               path_hdf5, [], False)

    # ------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_RUBAR_2D':
        if not 3 < len(all_arg) < 6:
            print('The function LOAD_RUBAR_2D needs two to three inputs. Call LIST_COMMAND for more '
                  'information.')
            return

        filename_geo = all_arg[2]
        filename_data = all_arg[3]
        pathgeo = os.path.dirname(filename_geo)
        pathtps= os.path.dirname(filename_data)
        geofile = os.path.basename(filename_geo)
        tpsfile = os.path.basename(filename_data)

        if len(all_arg) == 4:
            name_hdf5 = 'Hydro_RUBAR2D_' + geofile[0]
            path_hdf5 = '.'
        if len(all_arg) == 5:
            namepath_hdf5 = all_arg[4]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)

        rubar.load_rubar2d_and_create_grid(name_hdf5, geofile, tpsfile, pathgeo, pathtps, '.', name_prj, path_prj,
                                           'RUBAR2D', 2, path_hdf5,[], False)

# ------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_MASCARET':
        if not 6 < len(all_arg) < 11:
            print('The function LOAD_MASCARET needs five to eight inputs. Call LIST_COMMAND for more '
                  'information.')
            return

        # get filename
        filename_gen = all_arg[2]
        filename_geo = all_arg[3]
        filename_data = all_arg[4]
        pathfile = [os.path.dirname(filename_gen), os.path.dirname(filename_geo), os.path.dirname(filename_data)]
        namefile = [os.path.basename(filename_gen), os.path.basename(filename_geo), os.path.basename(filename_data)]

        # get nb_point_vel
        nb_point_vel = 70
        for i in range(5, len(all_arg)):
            if all_arg[i][:13] == 'nb_point_vel=':
                try:
                    nb_point_vel = str(all_arg[i][13:])
                except ValueError:
                    print('The number of velcoity point is not an int. Should be of the form nb_point_vel=x')
                    return
                del all_arg[i]
                break

        # get the manning data 9can be a float or the name of a text file
        manning_data = all_arg[5]
        try:
            manning_data = float(manning_data)
        except ValueError:
            if os.path.isfile(manning_data):
                manning_data = func_for_cmd.load_manning_txt(manning_data)
            else:
                print('Manning data should be a float or the name of text file')
                return

        # get the interpolatin type and hdf5 name
        if len(all_arg) == 6:  # .py com f1 f2 f3 int_type
            name_hdf5 = 'Hydro_HECRAS1D_' + namefile[0]
            path_hdf5 = '.'
        if len(all_arg) == 7:  # .py com f1 f2 f3 int_type pro_add or .py com f1 f2 f3 int_type output
            try:
                pro_add_is_here = True
                pro_add = int(all_arg[6])
            except ValueError:
                pass
            if not pro_add_is_here:
                namepath_hdf5 = all_arg[6]
                name_hdf5 = os.path.basename(namepath_hdf5)
                path_hdf5 = os.path.dirname(namepath_hdf5)
            else:
                name_hdf5 = 'Hydro_MASCARET_' + namefile[0]
                path_hdf5 = '.'
        if len(all_arg) == 8:
            pro_add_is_here = True
            pro_add = int(all_arg[6])
            namepath_hdf5 = all_arg[7]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)

        try:
            inter = int(all_arg[6])
        except ValueError:
            print('Error: Interpolation type should be 0, 1, 2')
            return

        # load mascaret
        mascaret.load_mascaret_and_create_grid(name_hdf5, path_hdf5, name_prj, path_prj, 'mascaret', namefile, pathfile,
                                    inter, manning_data, nb_point_vel, False, pro_add, [], path_hdf5, True)

# --------------------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_RIVER_2D':
        if not 2 < len(all_arg) < 5:
            print('The function LOAD_RIVER_2D needs one or two inputs. Call LIST_COMMAND for more '
                  'information.')
            return

        if os.path.isdir(all_arg[2]):
            filenames = load_hdf5.get_all_filename(all_arg[2], '.cdg')
        else:
            print('the input directory does not exist.')
            return

        paths = []
        for i in range(0, len(filenames)):
            paths.append(all_arg[2])

        if len(all_arg) == 3:
            name_hdf5 = 'Hydro_RIVER2D_' + filenames[0]
            path_hdf5 = '.'
        if len(all_arg) == 4:
            namepath_hdf5 = all_arg[3]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)

        river2d.load_river2d_and_cut_grid(name_hdf5, filenames, paths, name_prj, path_prj, 'RIVER2D', 2,
                                          path_hdf5, [], True)

# -------------------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_RUBAR_1D':
        if not 6 < len(all_arg) < 11:
            print('The function LOAD_RUBAR_1D needs five to eight inputs. Call LIST_COMMAND for more '
                  'information.')
            return

        # get filename
        filename_geo = all_arg[2]
        filename_data = all_arg[3]
        pathfile = [os.path.dirname(filename_geo), os.path.dirname(filename_data)]
        namefile = [os.path.basename(filename_geo), os.path.basename(filename_data)]

        # get nb_point_vel
        nb_point_vel = 70
        for i in range(5, len(all_arg)):
            if all_arg[i][:13] == 'nb_point_vel=':
                try:
                    nb_point_vel = str(all_arg[i][13:])
                except ValueError:
                    print('The number of velcoity point is not an int. Should be of the form nb_point_vel=x')
                    return
                del all_arg[i]
                break

        # get the manning data 9can be a float or the name of a text file
        manning_data = all_arg[5]
        try:
            manning_data = float(manning_data)
        except ValueError:
            if os.path.isfile(manning_data):
                manning_data = func_for_cmd.load_manning_txt(manning_data)
            else:
                print('Manning data should be a float or the name of text file')
                return

        # get the interpolatin type and hdf5 name
        if len(all_arg) == 5:  # .py com f1 f2 int_type
            name_hdf5 = 'Hydro_RUBAR1D_' + namefile[0]
            path_hdf5 = '.'
        if len(all_arg) == 6:  # .py com f1 f2 int_type pro_add or .py com f1 f2 int_type output
            try:
                pro_add_is_here = True
                pro_add = int(all_arg[5])
            except ValueError:
                pass
            if not pro_add_is_here:
                namepath_hdf5 = all_arg[5]
                name_hdf5 = os.path.basename(namepath_hdf5)
                path_hdf5 = os.path.dirname(namepath_hdf5)
            else:
                name_hdf5 = 'Hydro_MASCARET_' + namefile[0]
                path_hdf5 = '.'
        if len(all_arg) == 7:
            pro_add_is_here = True
            pro_add = int(all_arg[6])
            namepath_hdf5 = all_arg[6]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)

        try:
            inter = int(all_arg[5])
        except ValueError:
            print('Error: Interpolation type should be 0, 1, 2')
            return

        # load rubar
        rubar.load_rubar1d_and_create_grid(name_hdf5, path_hdf5, name_prj, path_prj, 'RUBAR1D', namefile, pathfile,
                                     inter, manning_data, nb_point_vel, False, pro_add, [], path_hdf5, True)
# ----------------------------------------------------------------------------------------
    elif all_arg[1] == 'RUN_ESTIMHAB':
        if not len(all_arg) == 12:
            print('RUN_ESTIMHAB needs 12 inputs. See LIST_COMMAND for more info.')
            return
        # input
        try:
            q = [float(all_arg[2]), float(all_arg[3])]
            w = [float(all_arg[4]), float(all_arg[5])]
            h = [float(all_arg[6]), float(all_arg[7])]
            q50 = float(all_arg[8])
            qrange  =[float(all_arg[9]), float(all_arg[10])]
            sub = float(all_arg[11])
        except ValueError:
            print('Error; Estimhab needs float as input')
            return

        # fish
        all_file = glob.glob(os.path.join(path_bio, r'*.xml'))
        for i in range(0, len(all_file)):
            all_file[i] = all_file[i].replace(path_bio, "")
            all_file[i] = all_file[i].replace("\\", "")
            all_file[i] = all_file[i].replace(".xml", "")
        fish_list = all_file

        # short check
        if q[0] == q[1]:
            print('Error: two different discharge are needed for estimhab')
            return
        if qrange[0] >= qrange[1]:
            print('Error: A range of dicharge is necessary')
            return
        if not fish_list:
            print('Error: no fish found for estimhab')
            return

        estimhab.estimhab(q, w, h, q50, qrange, sub, path_bio, fish_list, path_prj, True)
        plt.show()
    # --------------------------------------------------------------------------------------
    elif all_arg[1] == 'RUN_STATHAB':
        if not len(all_arg) == 3:
            print('RUN_STATHAB needs one argument: the path to the folder containing the input file.')
            return

        path_files = all_arg[2]
        if not os.path.isdir(path_files):
            print('Folder not found for Stathab.')
            return
        end_file_reach = ['deb.txt', 'qhw.txt', 'gra.txt', 'dis.txt']
        name_file_allreach = ['bornh.txt', 'bornv.txt', 'borng.txt', 'Pref.txt']

        # check than the files are there
        found_reach =0
        found_all_reach=0
        for file in os.listdir(path_files):
            file = file.lower()
            endfile = file[-7:]
            if endfile in end_file_reach:
                found_reach +=1
            if file in name_file_allreach:
                found_all_reach +=1
        if not 2 <found_all_reach <5:
            print('The files bornh.txt or bornv.txt or borng.txt could not be found.')
            return
        if found_reach % 4 !=0:
            print('The files deb.txt or qhw.txt or gra.txt or dis.txt could not be found.')
            return

        mystathab = stathab_c.Stathab(name_prj,path_prj)
        mystathab.load_stathab_from_txt('listriv.txt', end_file_reach, name_file_allreach, path_files)
        mystathab.stathab_calc(path_bio)
        mystathab.savetxt_stathab()
        mystathab.savefig_stahab()
        plt.show()

    # -----------------------------------------------------------------------------------
    elif all_arg[1] == 'RUN_FSTRESS':
        print('FSTRESS is not done yet on the command line.')

    # --------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_SUB_SHP':

        if not 3 < len(all_arg) < 6:
            print('LOAD_SUB_SHP needs between two and three inputs. See LIST_COMMAND for more information.')
            return

        filename = os.path.basename(all_arg[2])
        path = os.path.dirname(all_arg[2])
        code_type = all_arg[3]

        dominant_case = -1
        if len(all_arg) == 6:
            try:
                dominant_case = int(all_arg[5])
            except ValueError:
                print(' the dominant_case argument should -1 or 1 (1)')
                return
        if dominant_case ==1 or dominant_case == -1:
            pass
        else:
            print(' the dominant_case argument should -1 or 1 (1)')
            return

        [xy, ikle, sub_dom, sub_pg, blob] = substrate.load_sub_shp(filename, path, code_type, dominant_case)
        if ikle == [-99]:
            return
        load_hdf5.save_hdf5_sub(path_prj, path_prj, name_prj, sub_pg, sub_dom, ikle, xy, '', False, 'SUBSTRATE')

        # --------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_SUB_TXT':

        if not 3 < len(all_arg) < 6:
            print('LOAD_SUB_TXT needs between two and three inputs. See LIST_COMMAND for more information.')
            return

        filename = os.path.basename(all_arg[2])
        path = os.path.dirname(all_arg[2])
        code_type = all_arg[3]

        [xy, ikle, sub_dom2, sub_pg2, x, y, blob, blob] = substrate.load_sub_txt(filename, path, code_type)
        if ikle == [-99]:
            return
        load_hdf5.save_hdf5_sub(path_prj, path_prj, name_prj, sub_pg2, sub_dom2, ikle, xy, '', False, 'SUBSTRATE')

    # ----------------------------------------------------------------------------------------
    elif all_arg[1] == 'MERGE_GRID_SUB':

        if not 4 < len(all_arg) < 7:
            print('MERGE_GRID_SUB needs between three and four inputs. See LIST_COMMAND for more information.')
            return

        hdf5_name_hyd = all_arg[2]
        hdf5_name_sub = all_arg[3]
        try:
            default_data = int(all_arg[4])
        except ValueError:
            print('Default data should be an int between 1 and 8 (1).')
            return
        if not 0<default_data<9:
            print('Default data should be an int between 1 and 8 (2).')
            return

        # hdf5
        if len(all_arg) == 6:
            namepath_hdf5 = all_arg[5]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)
        else:
            name_hdf5 = 'Hydro_MERGE_cmd'
            path_hdf5 = '.'

        [ikle_both, point_all_both, sub_pg_all_both, sub_dom_all_both, vel_all_both, height_all_both] = substrate.merge_grid_hydro_sub(
            hdf5_name_hyd, hdf5_name_sub, default_data, path_prj)
        if ikle_both == [-99]:
            print('Error: data not merged.')
            return
        load_hdf5.save_hdf5(name_hdf5, name_prj, path_prj, 'SUBSTRATE', 2, path_hdf5, ikle_both,
                             point_all_both, [], vel_all_both, height_all_both, [], [], [], [], True, sub_pg_all_both,
                            sub_dom_all_both)

    # --------------------------------------------------------------------------------------------------------
    elif all_arg[1] == 'LOAD_HYDRO_HDF5':
        if len(all_arg) != 3:
            print('LOAD_HYDRO_HDF5 needs one input (the name of the hdf5 file).')
            return

        hdf5_name_hyd = all_arg[2]
        [ikle_all_t, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(hdf5_name_hyd, path_prj)

    # --------------------------------------------------------------
    elif all_arg[1] == 'LOAD_SUB_HDF5':
        if len(all_arg) != 3:
            print('LOAD_sub_HDF5 needs one input (the name of the hdf5 file).')
            return

        hdf5_name_sub = all_arg[1]
        [ikle_sub, point_all_sub, data_sub] = load_hdf5.load_hdf5_sub(hdf5_name_sub, path_prj)


    else:
        print('Command not recognized. Try LIST_COMMAND to see available commands.')


def habby_restart(file_comm,name_prj, path_prj, path_bio):
    """
    This function reads a list of command from a text file called file_comm. It then calls all_command one each line
    which does contain the symbol ":" . If the lines contains the symbol ":", it considered as an input.
    Careful, the intput should be in order!!!! The info on the left and sight of the symbol ":" are just there so
    an human can read them more easily. Space does not matters here. We try to write the restart file created
    automatically by HABBY in a "nice" layout, but it just to  read it more easily.

    :param file_comm: a string wehich gives the name of the restart file (with the path)
    :param name_prj: the name of the project, created by default by the main()
    :param path_prj: the path to the project created by default bu the main()
    :param path_bio: the path to the project

    """

    if not os.path.isfile(file_comm):
        print('Error: File for restart was not found. Check the name and path. \n')
        return

    # read file with all command
    with open(file_comm, 'rt') as f:
        all_data_restart = f.read()

    all_data_restart = all_data_restart.split('\n')

    if len(all_data_restart) < 1:
        print('Warning: No command found in the restart file')
        return

    l = 0
    for c in all_data_restart:
        if ":" not in c:
            print('-------------------------------------------------------------------')
            print(c)  # print in color
            c = c.strip()
            if len(c) < 1: # empty line
                pass
            elif c[0] == '#': # comment
                pass
            elif c == 'NAME_PROJECT': # manage project name
                arg1 = all_data_restart[l+1].split(':', 1)
                arg2 = all_data_restart[l+2].split(':', 1)
                if len(arg1) > 0 and len(arg2) > 0:
                    arg2[1] = arg2[1].strip()
                    if os.path.isdir(arg2[1]):
                        path_prj = os.path.join(arg2[1], 'restart')
                        if not os.path.isdir(path_prj):
                            os.mkdir(path_prj)
                            filename_empty = os.path.abspath('src_GUI/empty_proj.xml')
                            copyfile(filename_empty, os.path.join(path_prj, name_prj + '.xml'))
                        name_prj = arg1[1].strip()
                    else:
                        print('Error: the project folder is not found.\n')
                    print(os.path.join(path_prj, name_prj))
            else: # command
                all_arg_c = ['habby_cmd.py',c.strip()]
                lc = l+1
                while len(all_data_restart) > lc and ':' in all_data_restart[lc]:  # read argument
                    arg1 = all_data_restart[lc].split(':',1)
                    arg1 = arg1
                    if len(arg1) > 0:
                        all_arg_c.append(arg1[1].strip())
                    lc += 1
                all_command(all_arg_c, name_prj, path_prj, path_bio)
            print('DONE')
            print('-------------------------------------------------------------------')
        l +=1


def main():
    """
    This is the main for HABBY when called from the command line. It can call restart (read a list of command from a
    file) or read a command written on the cmd or apply a command to a type of file. For more complicated case, one can
    directly do a python script using the function from HABBY.
    """

    # create an empty project
    filename_empty = os.path.abspath('src_GUI/empty_proj.xml')
    copyfile(filename_empty, 'DefaultProj.xml')
    name_prj = 'DefaultProj'
    path_prj = '.'
    path_bio = './biology'

    if len(sys.argv) == 0 or len(sys.argv) == 1:
        print(" Not enough argument was given. At least one argument should be given")
        return

    if sys.argv[1] == 'RESTART':
        if len(sys.argv) != 3:
            print('Error: the RESTART command needs the name of the restart file as input.')
            return
        habby_restart(sys.argv[2],name_prj, path_prj, path_bio)
    else:
        all_arg = sys.argv
        all_command(all_arg, name_prj, path_prj, path_bio)


if __name__ == '__main__':
    main()