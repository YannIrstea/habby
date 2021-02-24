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
import filecmp
import glob
import os
import time
from copy import deepcopy
import h5py
import matplotlib
import numpy as np
matplotlib.use("qt5agg")
import matplotlib.pyplot as plt
from multiprocessing import Process, Value, Queue, Event
from shutil import copyfile

from src.hydraulic_results_manager_mod import HydraulicModelInformation
from src import hdf5_mod
from src import estimhab_mod
from src import stathab_mod
from src import substrate_mod
from src import fstress_mod
from src.variable_unit_mod import HydraulicVariableUnitList
from src.bio_info_mod import get_biomodels_informations_for_database, check_if_habitat_variable_is_valid
from src import lammi_mod
from src import hydraulic_process_mod
from src.hydrosignature import hydraulic_class_from_file
from src.project_properties_mod import create_project_structure, enable_disable_all_exports, \
    create_default_project_properties_dict, load_project_properties, change_specific_properties
import src.calcul_hab_mod
import src.hydraulic_process_mod
import src.merge
import src.substrate_mod


def all_command(all_arg, name_prj, path_prj, HABBY_VERSION, option_restart=False, erase_id=True):
    """
    This function is used to call HABBY from the command line. The general form is to call:
    habby_cmd command_name input1 input2 .. input n. The list of the command_name is given in the documentation and by
    calling the command "python habby_cmd.py LIST_COMMAND". This function is usually called directly by the main()
    or it is called by the function restart which read a list of function line by line. Careful, new command cannot
    contain the symbol ":" as it is used by restart.

    For the restart function, it is also important that the input folder is just in the folder "next" to the restart
    path. So the folder should not be moved randomly inside the project folder or renamed.

    :param all_arg: the list of argument (sys.argv more or less)
    :param name_prj: the name of the project, created by default by the main()
    :param path_prj: the path to the project created by default by the main()
    :param path_bio: the path to the project
    :param option_restart: If True the command are coming from a restart log (which have an impact on file name and
           location)
    :param erase_id: If True, the files with the same name are erased in merge. If False, they are kept with a
           time stamp
    """
    # all_arg[0] is the script name (habby_cmd.py)

    # manage the folders for the restart case
    input_file = False
    path_input = ''
    if option_restart:
        path_input = os.path.join(os.path.dirname(path_prj), 'input')
        if not os.path.isdir(path_input):
            input_file = False
            print('Warning: Input folder not found for the restart function. We will use the absolute path given in the'
                  'restart file.')
        else:
            input_file = True
            print('Input folder found for the restart function.')

    # check if the path given are ok
    file_prof = os.path.join(path_prj, name_prj + '.habby')
    # create project
    if not os.path.isdir(path_prj) or not os.path.isfile(file_prof):
        if not all_arg[0] == 'CREATE_PROJECT':
            # print("Warning: Specified project_path does not exist, the latter is created.")
            # cli_create_project(path_prj, name_prj, False, HABBY_VERSION_STR)
            # project_preferences = load_project_properties(path_prj)
            print("Error: Specified project_path does not exist. Project creation with CREATE_PROJECT argument.")
            return
    # load project preferences
    else:
        project_preferences = load_project_properties(path_prj)

    # ----------------------------------------------------------------------------------
    if all_arg[0] == 'LIST_COMMAND':
        print("Here are the available command for habby:")
        print('\n')
        print("LOAD_HECRAS_1D: load the hec-ras data in 1D. Input: name of .geo, name of the data file, interpolation "
              "choice,(number of profile to add), (output name)")
        print("LOAD_HECRAS_2D: load the hec-ras data in 2D. Input: name of the .h5 file, (output name)")
        print('LOAD_HYDRO_HDF5: load an hydrological hdf5. Input: the name of the hdf5 (with the path)')
        print("LOAD_MASCARET: load the mascaret data. Input: name of the three inputs files - xcas, geo, opt, "
              "manning coefficient, interpolation choice, (number of profile to add), (output name), (nb_point_vel=x)")
        print("LOAD_RIVER_2D: load the river 2d data. Input: folder containing the cdg file, (output name)")
        print("LOAD_RUBAR_1D: load the Rubar data in 1D. Input: name of input file .rbe, name of the profile input "
              "file, manning coefficient, interpolation choice, (number of profile to add), (output name),"
              "(nb_point_vel=x)")
        print("LOAD_RUBAR_2D: load the Rubar data in 2D. Input: name of .dat or .mai file, name of input .tps file "
              "(output name)")
        print("LOAD_SW2D: load the SW2D dataD. Input: name of .geo file, name of input .res file "
              "(output name)")
        print("LOAD_IBER2D: load the IBER2D dataD. Input: name of .dat file, name of input .rep files "
              "(output name)")
        print("LOAD_TELEMAC: load the telemac data in hdf5")
        print("\tinputfile: input file (telemac file absolute path with extension).")
        print("\tunits (optional): desired units index (0,1,2,3..). If not specify, all units all loaded.")
        print("\toutputfilename (optional): filename_output.hab. If not specify, automatic name from input name.")
        print("LOAD_LAMMI: load lammi data. Input: the name of the folder containing transect.txt and facies.txt and "
              "the name of the folder with the HydroSim result, (output name)")

        print('\n')
        print('MERGE_GRID_SUB: merge the hydrological and substrate grid together')
        print("\thydrauhdf5: input file (shapefile absolute path with extension).")
        print("\tcode_type: type of substrate (Cemagref or Sandre).")
        print("\tdominant_case (optional): type of substrate (Cemagref or Sandre). "
              "If not specify, dominant_case as 1 or -1")
        print("\toutputfilename (optional): filename_output.hab. If not specify, automatic name from input name.")
        print('LOAD_SUB: load the substrate (polygon, point or constant) from a shp, gpkg or txt in .sub')
        print("\tinputfile: input file (shapefile absolute path with extension).")
        print("\tcode_type: type of substrate (Cemagref or Sandre).")
        print("\tdominant_case (optional): type of substrate (Cemagref or Sandre). "
              "If not specify, dominant_case as 1 or -1")
        print("\toutputfilename (optional): filename_output.hab. If not specify, automatic name from input name.")
        print('\n')
        print('RUN_ESTIMHAB: Run the estimhab model. Input: qmes1 qmes2 wmes1 wmes2 h1mes h2mes q50 qmin qmax sub'
              '- all data in float')
        print('RUN_HABITAT: Estimate the habitat value from an hdf5 merged files. It used the coarser substrate '
              'as the substrate layer if the parameter run_choice is 0. We can also choose to make the calculation'
              'on the dominant substrate (run_choice:1) or the substrate by percentage (run_choice:2). The chosen stage'
              'should be separated by a comma. If the keyword all is given as the chosen stage, all available stage '
              'will be used. To get the calculation on more than one fish species, separate the names of '
              'the xml biological files by a comma without a space between the command and the filenames. '
              'Input: pathname of merge file, name of xml prefence file with no path, stage_chosen,'
              ' run_choice.')
        print('RUN_FSTRESS: Run the fstress model. Input: the path to the files list_riv, deb, and qwh.txt and'
              ' (path where to save output)')
        print("RUN_STATHAB: Run the stathab model. Input: the path to the folder with the different input files, "
              "(the river type, 0 by default, 1, or 2 for tropical rivers).")
        print('\n')
        print("RESTART: Relauch HABBY based on a list of command in a text file (restart file) Input: the name of file"
              " (with the path).")
        print("ALL: if the keywork ALL is followed by a command from HABBY, the command will be applied to all file"
              " in a folder. The name of the input file should be in the form: path_to_folder/*.ext with the "
              "right extension as ext. No output name should be given.")
        print("COMPARE_TEST: Call the small function which compare the files in two folders. Useful to test habby "
              "output. Input: The path to the folder with the reference file, the path to the folder with the "
              "files to check")
        print("COMPARE_FILE: Compares a test file to a reference file according to the values of their datasets. "
              "Input: ref_file= the path and filename of the reference file, test_file= the path and filename of the "
              "test file")
        print("COMPARE_DIR: Compares the files in a test directory and a reference directory according to the values "
              "of their datasets. Input: ref_path= the path to the reference directory, test_path= the path to the "
              "test directory")

        print('\n')
        print('list of options which can be added after the command: (1) path_prj= path to project, (2) '
              'name_prj= name of the project, (3) path_bio: the path to the biological files')

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'CREATE_PROJECT':


        all_export_enabled = False
        ##As a test measure, we may need to enable all_export_enabled, to be able to test exports
        for arg in all_arg:
            if arg[:19]=="all_export_enabled=":
                if arg[19:]=="False":
                    all_export_enabled=False
                else:
                    all_export_enabled = True

        if not os.path.exists(path_prj):
            create_project_structure(path_prj,
                                     save_log=False,
                                     version_habby=HABBY_VERSION,
                                     user_name="CLI",
                                     description="CLI-mode",
                                     mode="CLI")
            change_specific_properties(path_prj,
                                       preference_names=["physic_tabs", "stat_tabs"],
                                       preference_values=[True, True])
            enable_disable_all_exports(path_prj, enabled=all_export_enabled)
            print("# CREATE_PROJECT finished")
        else:
            print("Warning: The project " + name_prj + " already exists. The latter is not erased.")
            print("# CREATE_PROJECT finished")

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'CREATE_HYD':
        # remove the first arg CREATE_HYD
        all_arg = all_arg[1:]


        cli_load_hyd(all_arg, project_preferences)

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'LOAD_LAMMI':

        if not 3 < len(all_arg) < 6:
            print('The function LOAD_LAMMI needs two to three inputs. Call LIST_COMMAND for more '
                  'information.')
            return

        facies_path = all_arg[2]
        transect_path = all_arg[2]
        new_dir = all_arg[3]

        if len(all_arg) == 4:
            name_hdf5 = 'Merge_LAMMI_'
            path_hdf5 = path_prj
        elif len(all_arg) == 5:
            namepath_hdf5 = all_arg[3]
            name_hdf5 = os.path.basename(namepath_hdf5)
            path_hdf5 = os.path.dirname(namepath_hdf5)
        else:
            print('Error: Wrong number of intput')
            return

        lammi_mod.open_lammi_and_create_grid(facies_path, transect_path, path_prj, name_hdf5, name_prj, path_prj, path_hdf5,
                                             new_dir, [], False, 'Transect.txt', 'Facies.txt', True, [], 1, 'LAMMI')

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'RUN_ESTIMHAB':
        if not len(all_arg) == 12:
            print('RUN_ESTIMHAB needs 12 inputs. See LIST_COMMAND for more info.')
            return
        # path bio
        path_bio2 = os.path.join(path_bio, 'estimhab')
        # input
        try:
            q = [float(all_arg[2]), float(all_arg[3])]
            w = [float(all_arg[4]), float(all_arg[5])]
            h = [float(all_arg[6]), float(all_arg[7])]
            q50 = float(all_arg[8])
            qrange = [float(all_arg[9]), float(all_arg[10])]
            sub = float(all_arg[11])
        except ValueError:
            print('Error; Estimhab needs float as input')
            return

        # fish
        all_file = glob.glob(os.path.join(path_bio2, r'*.xml'))
        for i in range(0, len(all_file)):
            all_file[i] = os.path.basename(all_file[i])
        fish_list = all_file

        # short check
        if q[0] == q[1]:
            print('Error: two different discharge are needed for estimhab')
            return
        if qrange[0] >= qrange[1]:
            print('Error: A range of discharge is necessary')
            print(qrange)
            return
        if not fish_list:
            print('Error: no fish found for estimhab')
            return
        estimhab_mod.estimhab(q, w, h, q50, qrange, sub, path_bio2, fish_list, path_prj, True, {}, path_prj)
        # plt.show()  # should we let it? It stops the function butit shows the results

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'RUN_STATHAB':
        if not 2 < len(all_arg) < 5:
            print('RUN_STATHAB needs one or two arguments: the path to the folder containing the input file and the '
                  'river type.')
            return

        path_files = all_arg[2]
        if not os.path.isdir(path_files):
            print('Folder not found for Stathab.')
            return

        # river type
        if len(all_arg) == 3:
            riv_int = 0
        else:
            try:
                riv_int = int(all_arg[3])
            except ValueError:
                print('Error: The river type should be an int between 0 and 2.')
                return
            if riv_int > 2 or riv_int < 0:
                print('Error: The river type should be an int between 0 and 2 (1).')
                return

        # check taht the needed file are there for temperate and tropical rivers
        if riv_int == 0:
            end_file_reach = ['deb.txt', 'qhw.txt', 'gra.txt', 'dis.txt']
            name_file_allreach = ['bornh.txt', 'bornv.txt', 'borng.txt', 'Pref.txt']

            # check than the files are there
            found_reach = 0
            found_all_reach = 0
            for file in os.listdir(path_files):
                file = file.lower()
                endfile = file[-7:]
                if endfile in end_file_reach:
                    found_reach += 1
                if file in name_file_allreach:
                    found_all_reach += 1
            if not 2 < found_all_reach < 5:
                print('The files bornh.txt or bornv.txt or borng.txt could not be found.')
                return
            if found_reach % 4 != 0:
                print('The files deb.txt or qhw.txt or gra.txt or dis.txt could not be found.')
                return

        else:
            end_file_reach = ['deb.csv', 'qhw.csv', 'ii.csv']
            name_file_allreach = []

            # check than the files are there
            found_reach = 0
            found_all_reach = 0
            for file in os.listdir(path_files):
                file = file.lower()
                endfile = file[-7:]
                if endfile in end_file_reach:
                    found_reach += 1
                endfile = file[-6:]
                if endfile in end_file_reach:
                    found_reach += 1
            if found_reach % 3 != 0:
                print('The files deb.csv or qhw.csv or ii.csv could not be found.')
                return

        # load the txt data
        path_bio2 = os.path.join(path_bio, 'stathab')
        mystathab = stathab_mod.Stathab(name_prj, path_prj)
        mystathab.load_stathab_from_txt('listriv', end_file_reach, name_file_allreach, path_files)
        mystathab.path_im = path_prj

        # get fish name and run stathab
        if riv_int == 0:
            [mystathab.fish_chosen, coeff_all] = stathab_mod.load_pref('Pref_latin.txt', path_bio2)
            mystathab.stathab_calc(path_bio2)
            project_preferences = create_default_project_properties_dict()
            project_preferences['erase_id'] = True
            mystathab.project_preferences = project_preferences
            mystathab.savetxt_stathab()
            mystathab.savefig_stahab()
        elif riv_int == 1:
            name_fish = []
            filenames = hdf5_mod.get_all_filename(path_bio2, '.csv')
            for f in filenames:
                if 'uni' in f and f[-7:-4] not in name_fish:
                    name_fish.append(f[-7:-4])
            mystathab.fish_chosen = name_fish
            mystathab.riverint = 1
            mystathab.stathab_trop_univ(path_bio2, True)
            mystathab.savetxt_stathab()
            mystathab.savefig_stahab(False)
        elif riv_int == 2:
            name_fish = []
            filenames = hdf5_mod.get_all_filename(path_bio2, '.csv')
            for f in filenames:
                if 'biv' in f:
                    name_fish.append(f[-7:-4])
            mystathab.fish_chosen = name_fish
            mystathab.riverint = 2
            mystathab.stathab_trop_biv(path_bio2)
            mystathab.savetxt_stathab()
            mystathab.savefig_stahab(False)

        plt.show()

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'RUN_FSTRESS':

        if not 2 < len(all_arg) < 5:
            print('RUN_FSTRESS needs between one and two inputs. See LIST_COMMAND for more information.')
            return

        path_fstress = all_arg[2]
        if len(all_arg) == 3:
            path_hdf5 = path_prj
        else:
            path_hdf5 = all_arg[3]
        # do not change the name from this file which should be in the biology folder.
        name_bio = 'pref_fstress.txt'

        # get the data from txt file
        [riv_name, qhw, qrange] = load_fstress_text(path_fstress)

        if qhw == [-99]:
            return

        # get the preferences curve, all invertebrate are selected by default
        [pref_inver, inv_name] = fstress_mod.read_pref(path_bio, name_bio)

        # save input data in hdf5
        fstress_mod.save_fstress(path_hdf5, path_prj, name_prj, name_bio, path_bio, riv_name, qhw, qrange, inv_name)

        # run fstress
        [vh_all, qmod_all, inv_name] = fstress_mod.run_fstress(qhw, qrange, riv_name, inv_name, pref_inver, inv_name,
                                                               name_prj, path_prj)

        # write output in txt
        # no timestamp
        fstress_mod.write_txt(qmod_all, vh_all, inv_name, path_prj, riv_name, False)

        # plot output in txt
        fstress_mod.figure_fstress(qmod_all, vh_all, inv_name, path_prj, riv_name)
        # plt.show()

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'LOAD_SUB':
        # remove the first arg LOAD_SUB
        all_arg = all_arg[1:]

        cli_load_sub(all_arg, project_preferences)

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'MERGE_GRID_SUB':
        # remove the first arg MERGE_GRID_SUB
        all_arg = all_arg[1:]

        cli_merge(all_arg, project_preferences)

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'RUN_HABITAT':
        # remove the first arg MERGE_GRID_SUB
        all_arg = all_arg[1:]

        cli_calc_hab(all_arg, project_preferences)

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'RUN_HS':
        # remove the first arg MERGE_GRID_SUB
        all_arg = all_arg[1:]

        cli_compute_hs(all_arg, project_preferences)

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'ADD_HYDRO_HDF5':
        if len(all_arg) < 4:
            print('ADD_HYDRO_HDF5 needs at least two arguments. See LIST_COMMAND for more information.')
            return
        filepath1 = ''
        new_name = ''
        for i in range(2, len(all_arg) - 1):
            if i == 2:
                filepath1 = all_arg[2]
            else:
                old_name = new_name
            filepath2 = all_arg[i + 1]
            if not os.path.isfile(filepath1):
                print('Error: The first hdf5 file was not found')
                return
            if not os.path.isfile(filepath2):
                print('Error: The second hdf5 file was not found')
                return
            path1 = os.path.dirname(filepath1)
            path2 = os.path.dirname(filepath2)
            hdf51 = os.path.basename(filepath1)
            hdf52 = os.path.basename(filepath2)

            model_type = 'Imported_hydro'
            new_name = hdf5_mod.addition_hdf5(path1, hdf51, path2, hdf52, name_prj, path_prj, model_type, path_prj,
                                              False, True, True, 'ADD_HYDRO_CMD_LAST_' + hdf52[:-3])
            filepath1 = os.path.join(path_prj, new_name + '.hab')
            if 2 < i < len(all_arg) - 1:
                try:
                    os.remove(os.path.join(path_prj, old_name + '.hab'))
                except FileNotFoundError:
                    print('Error: File not found ' + os.path.join(path_prj, old_name + '.hab'))
                    pass
        # ---------------------------------------------------------------------------

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'ADD_MERGE_HDF5':
        if len(all_arg) < 4:
            print('ADD_MERGE_HDF5 needs at least two arguments. See LIST_COMMAND for more information.')
            return
        filepath1 = ''
        new_name = ''
        for i in range(2, len(all_arg) - 1):
            if i == 2:
                filepath1 = all_arg[2]
            else:
                old_name = new_name
            filepath2 = all_arg[i + 1]
            if not os.path.isfile(filepath1):
                print('Error: The first hdf5 file was not found')
                return
            if not os.path.isfile(filepath2):
                print('Error: The second hdf5 file was not found')
                return
            path1 = os.path.dirname(filepath1)
            path2 = os.path.dirname(filepath2)
            hdf51 = os.path.basename(filepath1)
            hdf52 = os.path.basename(filepath2)

            model_type = 'Imported_hydro'
            new_name = hdf5_mod.addition_hdf5(path1, hdf51, path2, hdf52, name_prj, path_prj, model_type, path_prj,
                                              True, True, True, 'ADD_MERGE_CMD_LAST_' + hdf52[:-3])
            filepath1 = os.path.join(path_prj, new_name + '.hab')
            if 2 < i < len(all_arg) - 1:
                if old_name != new_name:
                    try:
                        os.remove(os.path.join(path_prj, old_name + '.hab'))
                    except FileNotFoundError:
                        print('Error: File not found ' + os.path.join(path_prj, old_name + '.hab'))
                        pass

    # ----------------------------------------------------------------------------------
    elif all_arg[0] == 'COMPARE_TEST':
        # remove the first arg COMPARE_TEST
        all_arg = all_arg[1:]



        # get args
        for arg in all_arg:
            # ref_path
            if arg[:9] == 'ref_path=':
                folder1 = arg[9:]
            # test_path
            if arg[:10] == 'test_path=':
                folder2 = arg[10:]
            if arg[:9] in ['path_prj=','path_bio=','name_prj=']:
                all_arg.remove(arg)

        if len(all_arg) != 2:
            print('COMPARE_TEST needs two arguments, which are the two paths to the folders to be compared.')
            return

        # get folder name
        if not os.path.isdir(folder1):
            print('Error: the first folder is not found')
            return
        if not os.path.isdir(folder2):
            print('Error: the second folder is not found')
            return

        # get the names of the files in the folder with the expected files
        filenames_exp = hdf5_mod.get_all_filename(folder1, '.txt')

        # check that the expected files exists and have the same content in the folder with the results files
        num_wrong = 0
        for f in filenames_exp:
            # check that file exists
            new_file = os.path.join(folder2, f)
            if not os.path.isfile(new_file):
                print('One file was not created by habby during testing. name of the file: ' + os.path.basename(f))
                num_wrong += 1
            else:
                # check if identical
                if filecmp.cmp(new_file, os.path.join(folder1, f), shallow=False):
                    pass
                else:
                    num_wrong += 1
                    print("One file created by habby during testing was not identical to reference file " +
                          os.path.basename(f))

        # result
        if num_wrong == 0:
            print('TEST ALL GOOD!')
        else:
            print('PROBLEMS WERE FOUND ON ' + str(num_wrong) + ' OUT OF ' + str(len(filenames_exp)) + ' FILES.')
        print('-----------------END TEST -------------------------')

    # ----------------------------------------------------------------------------------
    elif all_arg[0]=='COMPARE_FILE':
        #Compares a test file to a reference file, and determines whether they contain the same data


        for arg in all_arg:
            if arg[:9]=='ref_file=':
                ref_name=arg[9:]

            if arg[:10]=='test_file=':
                test_name=arg[10:]

            if arg[:9] in ['path_prj','name_prj','path_bio']:
                all_arg.remove(arg)

        try:
            if not os.path.exists(ref_name):
                print('Error: the reference file does not exist or there is a typo in the file path provided')
                return
        except NameError:
            print('Error: you have not given the argument ref_file')
            return
        try:
            if not os.path.exists(test_name):
                print('Error: the test file does not exist or there is a typo in the file path provided')
                return
        except NameError:
            print('Error: you have not given the argument test_file')
            return

        if len(all_arg) !=3:
            #If there are any arguments other than the command name, ref_file, test_file, path_prj, name_prj and
            # path_bio, the program should give an error message
            print('COMPARE_FILE takes 2 arguments: ref_file and test_file, as well as the options path_prj, '
                  'name_prj and path_bio')
            return

        file1 = h5py.File(ref_name, 'r')
        file2 = h5py.File(test_name, 'r')
        dataset_names1=hdf5_mod.get_dataset_names(file1)
        dataset_names2=hdf5_mod.get_dataset_names(file2)
        if dataset_names1!=dataset_names2:
            print("The files contain different datasets")
        else:
            if hdf5_mod.datasets_are_equal(file1,file2):
                print("The files are equal")
            else:
                print("The files are different")

    # ----------------------------------------------------------------------------------
    elif all_arg[0]=="COMPARE_DIR":
        #Compares a test folder to a reference folder, and determines whether the test folder contains all the hdf5 files
        #of the reference folder, and if the corresponding files are identical
        for arg in all_arg:
            if arg[:9]=='ref_path=':
                ref_path=arg[9:]
                if ref_path[-1]=='\\':
                    ref_path=ref_path[:-1]
            if arg[:10]=='test_path=':
                test_path=arg[10:]
                if test_path[-1]=='\\':
                    test_path=test_path[:-1]
            if arg[:9] in ['path_prj','name_prj','path_bio']:
                all_arg.remove(arg)

        try:
            if not os.path.isdir(ref_path):
                print("The path provided for the reference folder does not exist, or it has a typo")
                return
        except NameError:
            print("Error: you have not given the argument ref_path")
            return
        try:
            if not os.path.isdir(test_path):
                print("The path provided for the test folder does not exist, or it has a typo")
                return
        except NameError:
            print("Error: you have not given the argument test_path")
            return

        if len(all_arg) !=3:
            #If there are too many arguments or not enough, this message should be displayed
            print('COMPARE_DIR takes 2 arguments: ref_path and test_path, as well as the options path_prj, '
                  'name_prj and path_bio')
            return

        ref_filenames=(hdf5_mod.get_all_filename(ref_path,".hyd")+hdf5_mod.get_all_filename(ref_path,".sub")+
                       hdf5_mod.get_all_filename(ref_path,".hab")+hdf5_mod.get_all_filename(ref_path,".h5"))
        #files with the above extensions are assumed to be hdf5 files

        n_total=len(ref_filenames)
        n_missing=0
        n_different=0
        for filename in ref_filenames:

            if not os.path.exists(test_path +'/'+ filename):
                n_missing+=1
            else:
                test_file=h5py.File(test_path +'/'+ filename,'r')
                ref_file=h5py.File(ref_path +'/'+ filename,'r')
                dataset_names1 = hdf5_mod.get_dataset_names(ref_file)
                dataset_names2 = hdf5_mod.get_dataset_names(test_file)
                if not hdf5_mod.datasets_are_equal(ref_file,test_file):
                    n_different+=1

        if n_missing==0 and n_different==0:
            print("Good! Every hdf5 file from the reference folder has an equal file in the test folder.")

        else:
            print("There is a divergence between the test and reference folders. Out of "
                  ,n_total,"files in the reference folder, ",n_missing," are missing from the test folder, and "
                  ,n_different," have different values in the test and reference folders")

    # ----------------------------------------------------------------------------------
    elif all_arg[0]=="EXPORT":
        # Given a project folder, takes as entry an hdf5 file, which should be in the hdf5 folder of the project
        # directory, and exports its content
        # Works for .hyd files, but gives error messages related to rtree module
        # Does not work for .sub files

        for arg in all_arg:
            if arg[:10]=="file_name=":
                file_name=arg[10:]
            if arg[:7]=="format=":
                format=arg[7:]

        try:
            file_name
            format
        except NameError:
            print("Error: the EXPORT command takes as arguments path_prj, file_name and format")
            return

        # if not file_name or not format:
        #     print("Error: the EXPORT command takes as arguments path_prj, file_name and format")

        if not os.path.exists(path_prj+"\\hdf5\\"+file_name):
            print("Error: the file ", file_name, " does not exist, or is not located in the path_prj\\hdf5 folder.")
            return

        try:
            data = hdf5_mod.Hdf5Management(path_prj, file_name, new=False, edit=False)
            data.project_preferences = project_preferences
            hdf5_mod.simple_export(data, format)
            print("Success!")
        except ValueError:
            print("The EXPORT command only allows as input hdf5 files with a .hyd or .hab extension.")





    # ----------------------------------------------------------------------------------
    else:
        #print(all_arg, name_prj, path_prj, path_bio)
        print('Command not recognized. Try LIST_COMMAND to see available commands.')


def habby_restart(file_comm, name_prj, path_prj, path_bio):
    """
    This function reads a list of command from a text file called file_comm. It then calls all_command one each line
    which does contain the symbol ":" . If the lines contains the symbol ":", it considered as an input.
    Careful, the intput should be in order!!!! The info on the left and right of the symbol ":" are just there so
    an human can read them more easily. Space does not matters here. We try to write the restart file created
    automatically by HABBY in a "nice" layout, but it just to  read it more easily.

    :param file_comm: a string wehich gives the name of the restart file (with the path)
    :param name_prj: the name of the project, created by default by the main()
    :param path_prj: the path to the project created by default bu the main()
    :param path_bio: the path to the project

    """
    # get args
    if file_comm[:12] == 'restartfile=':
        file_comm = file_comm[12:]

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
    a = time.time()
    for c in all_data_restart:
        if ":" not in c:
            print('-------------------------------------------------------------------')
            print(c)
            c = c.strip()
            if len(c) < 1:  # empty line
                pass
            elif c[0] == '#':  # comment
                pass
            elif c == 'NAME_PROJECT':  # manage project name
                arg1 = all_data_restart[l + 1].split(':', 1)
                arg2 = all_data_restart[l + 2].split(':', 1)
                if len(arg1) > 0 and len(arg2) > 0:
                    arg2[1] = arg2[1].strip()
                    print(arg2[1])
                    if os.path.isdir(arg2[1]):
                        path_prj = os.path.join(arg2[1], 'restart')
                        name_prj = arg1[1].strip()
                        if not os.path.isdir(path_prj):
                            os.mkdir(path_prj)
                        if not os.path.isfile(os.path.join(path_prj, name_prj + '.habby')):
                            filename_empty = os.path.abspath(os.path.join('files_dep', 'empty_proj.habby'))
                            copyfile(filename_empty, os.path.join(path_prj, name_prj + '.habby'))

                    else:
                        print('Error: the project folder is not found.\n')
                    print(os.path.join(path_prj, name_prj))
            elif c[:3] == 'ALL':  # all command together
                all_arg_c = ['habby_cmd.py', c[3:].strip()]
                lc = l + 1
                while len(all_data_restart) > lc and ':' in all_data_restart[lc]:  # read argument
                    arg1 = all_data_restart[lc].split(':', 1)
                    arg1 = arg1
                    if len(arg1) > 0:
                        all_arg_c.append(arg1[1].strip())
                    lc += 1
                habby_on_all(all_arg_c, name_prj, path_prj, path_bio)
            else:  # command
                all_arg_c = ['habby_cmd.py', c.strip()]
                lc = l + 1
                while len(all_data_restart) > lc and ':' in all_data_restart[lc]:  # read argument
                    arg1 = all_data_restart[lc].split(':', 1)
                    arg1 = arg1
                    if len(arg1) > 0:
                        all_arg_c.append(arg1[1].strip())
                    lc += 1
                all_command(all_arg_c, name_prj, path_prj, path_bio, True)
                plt.close()
            print('DONE')
            print('-------------------------------------------------------------------')
        l += 1
    b = time.time()
    print(str(l) + ' commands executed in ' + str(b - a) + 'sec')


def habby_on_all(all_arg, name_prj, path_prj, path_bio, option_restart=False):
    """
    This function is used to execute a command from habby_cmd on all files in a folder. The form of the command should
    be something like "habby_cmd ALL COMMAND path_to_file/\*.ext arg2 ag3" with the arguments adapted to the specific
    command.

    In other words, the command should be the usual command with the keyword ALL before and with the name of
    the input files remplace by \*.ext . where ext is the extension of the files.
    It is better to not add an output name. Indeed default name for output includes the input file name, which
    is practical if different files are given as input. If the default
    is overridden, the same name will be applied, only the units will be different. To be sure to not overwrite a
    file, this function waits one second between each command. Only the input argument should containts the string '\*'.
    Otherwise, other commands would be treated as input files.

    If there is more than one type of input, it is important that the name of the file are the same (or at least
    that there are in the same alphabetical order). If the variable # is used instead of \*, the function will be
    applied to all second file one by one. So if we have two substrate file and two hydro file, name with \* will result
    in two merged files while # will result in four merge file.

    If more than one extension is possible (example g01, g02, g03, etc. in hec-ras), replace the changing part of the
    extension with the symbol \* (so path_to_folder/\*.g0\* arg1 argn). If the name of the file changed in the extension
    as in RUBAR (where the file have the name PROFIL.file), just change for PROFIL.\* or something similar. Generally
    the matching is done using the function glob, so the shell-type wildcard can be used.

    As there are a lot of hdf5 intput, one should be careful to avoid mixing between the different type of hdf5 files.
    For example, it is better to write 'MERGE\*.hab' as just '\*.hab' if the folder contains hydraulic and merge files.

    :param all_arg: the list of argument (sys.argv without the argument ALL so [sys.argv[0], sys.argv[2], sys.argv[n]])
    :param name_prj: the name of the project, created by default by the main()
    :param path_prj: the path to the project created by default bu the main()
    :param path_bio: the path to the project
    :param option_restart: If True the command are coming from a restart log (which have an impact on file name and
           location)
    """

    # if you just read the docstring here, do not forgot that \ is an espcae character for sphinx and * is a special
    # character: \* = *

    # get argv with *. (input name)
    input_folder = []
    place_ind = []
    use_file_one_by_one = False
    for idx, a in enumerate(all_arg):
        if '#' in a:
            a = a.replace('#', '*')
            use_file_one_by_one = True
        if '*' in a:
            input_folder.append(a)
            place_ind.append(idx)
    nb_type = len(place_ind)

    # get all input name
    all_files = []
    dirname = '.'
    for f in input_folder:
        files = glob.glob(f)
        # dirname = os.path.dirname(f)
        # basename = os.path.basename(f)
        # blob,ext = os.path.splitext(basename)
        # if "*" not in ext:
        #     files = load_hdf5.get_all_filename(dirname, ext)
        # else:
        #     pattern = basename
        all_files.append(files)
        if not files:
            print('Warning: No files found for the current ALL command.')

    if len(all_files) == 0:
        print('No file found in the selected folder')
        return

    # if we want to use all files with all file, we will have to correct the file order
    if use_file_one_by_one:
        nb_dim = sum(len(x) for x in all_files[1:])
        all_files_old = deepcopy(all_files)
        if nb_dim > 0:
            all_files = [all_files_old[0] * nb_dim]  # fist dim
        else:
            all_files = [all_files_old[0]]  # fist dim
        for i in range(1, len(all_files_old)):
            new_files = [val for val in all_files_old[i] for _ in range(0, len(all_files_old[i - 1]))]
            all_files.append(new_files)

    # check that each input type has the same length
    if not all(len(i) == len(all_files[0]) for i in all_files):
        print('The number of each type of input file is not equal. Please check the name of the file below')
        print(all_files)
        return

    # now get through each files
    for i in range(0, len(all_files[0])):
        all_arg_here = all_arg

        # get the file for this command
        # careful files should be in order
        for j in range(0, nb_type):
            all_arg_here[place_ind[j]] = os.path.join(dirname, all_files[j][i])

        # just to check
        print('Execute command ' + all_arg_here[1] + ' on:')
        for i in place_ind:
            print(all_arg_here[i])

        # execute the command
        a = time.time()
        all_command(all_arg_here, name_prj, path_prj, path_bio, option_restart, erase_id=True)
        t = time.time() - a
        print('Command executed in {:.0f} sec.'.format(t))
        print('----------------------------------------------------------------------')

        # avoid risk of over-wrting
        time.sleep(1)


def load_manning_txt(filename_path):
    """
    This function loads the manning data in case where manning number is not simply a constant. In this case, the manning
    parameter is given in a .txt file. The manning parameter used by 1D model such as mascaret or Rubar BE to distribute
    velocity along the profiles. The format of the txt file is "p, dist, n" where  p is the profile number (start at zero),
    dist is the distance along the profile in meter and n is the manning value (in SI unit). White space is neglected
    and a line starting with the character # is also neglected.

    There is a very similar function as a method in the class Sub_HydroW() in hydro_GUI.py but it used by the GUI
    and it includes a way to select the file using the GUI and it used a lot of class attribute. So it cannot be used
    by the command line. Changes should be copied in both functions if necessary.

    :param filename_path: the path and the name of the file containing the manning data
    :return: the manning as an array form
    """

    try:
        with open(filename_path, 'rt') as f:
            data = f.read()
    except IOError:
        print('Error: The selected file for manning can not be open.')
        return
    # create manning array (to pass to dist_vitess)
    data = data.split('\n')
    manning = np.zeros((len(data), 3))
    com = 0
    for l in range(0, len(data)):
        data[l] = data[l].strip()
        if len(data[l]) > 0:
            if data[l][0] != '#':
                data_here = data[l].split(',')
                if len(data_here) == 3:
                    try:
                        manning[l - com, 0] = np.int(data_here[0])
                        manning[l - com, 1] = np.float(data_here[1])
                        manning[l - com, 2] = np.float(data_here[2])
                    except ValueError:
                        print('Error: The manning data could not be converted to float or int.'
                              ' Format: p,dist,n line by line.')
                        return
                else:
                    print('Error: The manning data was not in the right format.'
                          ' Format: p,dist,n line by line.')
                    return

            else:
                manning = np.delete(manning, -1, 0)
                com += 1

    return manning


def load_fstress_text(path_fstress):
    """
    This function loads the data for fstress from text files. The data is composed of the name of the rive, the
    discharge range, and the [discharge, height, width]. To read the files, the files listriv.txt is given. Form then,
    the function looks for the other files in the same folder. The other files are rivdeb.txt and rivqwh.txt. If more
    than one river is given in listriv.txt, it load the data for all rivers.

    There is a very similar function as a method in the class FStressW() in fstress_GUI.py but it ised by the GUI
    and it includes a way to select the file using the GUI. Changes should be copied in both functions if necessary.

    :param path_fstress: the path to the listriv.txt function (the other fil should be in the same folder)

    """

    found_file = []
    riv_name = []

    # filename_path
    filename = 'listriv.txt'
    filename_path = os.path.join(path_fstress, filename)

    if not os.path.isfile(filename_path):
        print('Error: listriv.txt could not be found.')
        return [-99], [-99], [-99]

    # get the river name
    with open(filename_path, 'rt') as f:
        for line in f:
            riv_name.append(line.strip())

    # add the file names (deb and qhw.txt)
    for r in riv_name:
        f_found = [None, None]
        # discharge range
        debfilename = r + 'deb.txt'
        if os.path.isfile(os.path.join(path_fstress, debfilename)):
            f_found[1] = debfilename
        elif os.path.isfile(os.path.join(path_fstress, r + 'DEB.TXT')):
            debfilename = r[:-7] + 'DEB.TXT'
            f_found[1] = debfilename
        else:
            f_found[1] = None
        # qhw
        qhwname = r + 'qhw.txt'
        if os.path.isfile(os.path.join(path_fstress, qhwname)):
            f_found[0] = qhwname
        elif os.path.isfile(os.path.join(path_fstress, r + 'QHW.TXT')):
            qhwname = r + 'QHW.TXT'
            f_found[0] = qhwname
        else:
            print('Error: qhw file not found for river ' + r + '.')
            return
        found_file.append(f_found)

    # if not river found
    if len(riv_name) == 0:
        print('Warning: No river found in files')
        return [-99], [-99], [-99]

    # load the data for each river
    qrange = []
    qhw = []
    for ind in range(0, len(found_file)):
        fnames = found_file[ind]

        # discharge range
        if fnames[1] is not None:
            fname_path = os.path.join(path_fstress, fnames[1])
            if os.path.isfile(fname_path):
                with open(fname_path, 'rt') as f:
                    data_deb = f.read()
                data_deb = data_deb.split()
                try:
                    data_deb = list(map(float, data_deb))
                except ValueError:
                    print('Error: Data cannot be converted to float in deb.txt')
                    return
                qmin = min(data_deb)
                qmax = max(data_deb)

                qrange.append([qmin, qmax])
            else:
                print('Error: deb.txt file not found.(1)')
                return [-99], [-99], [-99]
        else:
            print('Error: deb.txt file not found.(2)')
            return [-99], [-99], [-99]

        # qhw
        fname_path = os.path.join(path_fstress, fnames[0])
        if os.path.isfile(fname_path):
            with open(fname_path, 'rt') as f:
                data_qhw = f.read()
            data_qhw = data_qhw.split()
            # useful to pass in float to check taht we have float
            try:
                data_qhw = list(map(float, data_qhw))
            except ValueError:
                print('Error: Data cannot be concerted to float in qhw.txt')
                return [-99], [-99], [-99]
            if len(data_qhw) < 6:
                print('Error: FStress needs at least two discharge measurement.')
                return [-99], [-99], [-99]
            if len(data_qhw) % 3 != 0:
                print('Error: One discharge measurement must be composed of three data (q,w, and h).')
                return [-99], [-99], [-99]

            qhw.append([[data_qhw[0], data_qhw[1], data_qhw[2]], [data_qhw[3], data_qhw[4], data_qhw[5]]])
        else:
            print('Error: qwh.txt file not found.(2)')
            return [-99], [-99], [-99]

    return riv_name, qhw, qrange


""" HYD """


def cli_load_hyd(arguments, project_preferences):
    # optionnal args
    units_string = None
    outputfilename = None

    # get args
    for arg in arguments:
        # model
        model_arg_name = 'model='
        if arg[:len(model_arg_name)] == model_arg_name:
            model_name = arg[len(model_arg_name):]
        # inputfile
        inputfile_arg_name = 'inputfile='
        if arg[:len(inputfile_arg_name)] == inputfile_arg_name:
            filename_path = arg[len(inputfile_arg_name):]
            if "," in filename_path:
                path = os.path.dirname(filename_path)
                filename = os.path.basename(filename_path)
                filename_path = []
                for filename in filename.split(","):
                    filename_path.append(os.path.join(path, filename))
            else:
                filename_path = [filename_path]
        # outputfilename
        outputfilename_arg_name = 'outputfilename='
        if arg[:len(outputfilename_arg_name)] == outputfilename_arg_name:
            outputfilename = arg[len(outputfilename_arg_name):]
        # cut
        cut_arg_name = 'cut='
        if arg[:len(cut_arg_name)] == cut_arg_name:
            cut = eval(arg[len(cut_arg_name):])
            project_preferences['cut_mesh_partialy_dry'] = cut

    # # get_hydrau_description_from_source
    hydraulic_model_information = HydraulicModelInformation()
    hsra_value = hydraulic_process_mod.HydraulicSimulationResultsAnalyzer(filename_path,
                                                                          project_preferences["path_prj"],
                                                                          hydraulic_model_information.get_attribute_name_from_name_models_gui(
                                                                              model_name),
                                                                          2)

    # outputfilename
    if outputfilename:
        hsra_value.hydrau_description_list[0]["hdf5_name"] = outputfilename
    else:
        # change suffix
        if not project_preferences["cut_mesh_partialy_dry"]:
            namehdf5_old, exthdf5_old = os.path.splitext(hsra_value.hydrau_description_list[0]["hdf5_name"])
            hsra_value.hydrau_description_list[0]["hdf5_name"] = namehdf5_old + "_no_cut" + exthdf5_old

    # warnings
    if hsra_value.warning_list:
        for warn in hsra_value.warning_list:
            print(warn)

    # error
    if type(hsra_value.hydrau_description_list[0]) == str:
        print("Error")
        return

    # run process
    progress_value = Value("d", 0)
    q = Queue()
    p = Process(target=hydraulic_process_mod.load_hydraulic_cut_to_hdf5,
                args=(hsra_value.hydrau_description_list[0],
                      progress_value,
                      q,
                      True,
                      project_preferences),
                name=hsra_value.hydrau_description_list[0]["hdf5_name"] + " creation")

    cli_start_process_and_print_progress(p, progress_value)


""" SUB """


def cli_load_sub(arguments, project_preferences):
    # check
    # if not 1 < len(all_arg) < 5:
    #     print('LOAD_SUB_SHP needs between two and three inputs. See LIST_COMMAND for more information.')
    #     return

    # optionnal args
    outputfilename = None

    # get args
    for arg in arguments:
        # inputfile
        if arg[:10] == 'inputfile=':
            filename = os.path.basename(arg[10:])
            abs_path_file = arg[10:]
        # substrate_mapping_method
        if arg[:25] == "substrate_mapping_method=":
            substrate_mapping_method = arg[25:]
        # outputfilename
        if arg[:15] == 'outputfilename=':
            outputfilename = arg[15:]

    if outputfilename:
        name_hdf5 = outputfilename
    else:
        name_hdf5 = os.path.splitext(filename)[0] + ".sub"

    # get_sub_description_from_source
    sub_description, warning_list = src.substrate_mod.get_sub_description_from_source(abs_path_file,
                                                                                      substrate_mapping_method,
                                                                                      project_preferences["path_prj"])

    # error
    if not sub_description:
        for warn in warning_list:
            print(warn)

    # ok
    if sub_description:
        # outputfilename
        if outputfilename:
            sub_description["hdf5_name"] = outputfilename

        # but warnings
        if warning_list:
            for warn in warning_list:
                print(warn)

        # change hdf5_name
        sub_description["name_hdf5"] = name_hdf5

        # if shape data valid : load and save
        stop = Event()
        q = Queue()
        progress_value = Value("d", 0)
        p = Process(target=substrate_mod.load_sub,
                    args=(sub_description,
                          progress_value,
                          q,
                          True,
                          project_preferences,
                          stop),
                    name="LOAD_SUB")
        cli_start_process_and_print_progress(p, progress_value)


def cli_merge(arguments, project_preferences):
    if not 1 < len(arguments) < 6:
        print('MERGE_GRID_SUB needs between three and four inputs. See LIST_COMMAND for more information.')
        return

    # optionnal args
    outputfilename = None

    # get args
    for arg in arguments:
        # hdf5_name_hyd
        if arg[:4] == 'hyd=':
            hdf5_name_hyd = os.path.basename(arg[4:])
        # hdf5_name_sub
        if arg[:4] == 'sub=':
            hdf5_name_sub = arg[4:]
        # outputfilename
        if arg[:15] == 'outputfilename=':
            outputfilename = arg[15:]

    if not outputfilename:
        outputfilename = os.path.splitext(hdf5_name_hyd)[0] + "_" + os.path.splitext(hdf5_name_sub)[0] + ".hab"

    # run the function
    q = Queue()
    progress_value = Value("d", 0)
    p = Process(target=src.hydraulic_process_mod.merge_grid_and_save,
                args=(hdf5_name_hyd,
                      hdf5_name_sub,
                      outputfilename,
                      project_preferences["path_prj"],
                      progress_value,
                      q,
                      True,
                      project_preferences),
                name="MERGE_GRID_SUB")
    cli_start_process_and_print_progress(p, progress_value)


""" HAB """


def cli_calc_hab(arguments, project_preferences):
    # if len(all_arg) != 4:
    #     print('RUN_HABITAT needs between four and five inputs. See LIST_COMMAND for more information.')
    #     return

    run_choice = dict()

    # get args
    for arg in arguments:
        # hab
        if arg[:4] == 'hab=':
            hab_filename = arg[4:]
        # pref_file_list
        if arg[:15] == 'pref_file_list=':
            run_choice["pref_file_list"] = arg[15:].split(",")
        # stage_list
        if arg[:11] == 'stage_list=':
            run_choice["stage_list"] = arg[11:].split(",")
        # hyd_opt
        if arg[:8] == 'hyd_opt=':
            run_choice["hyd_opt"] = arg[8:].split(",")
        # sub_opt
        if arg[:8] == 'sub_opt=':
            run_choice["sub_opt"] = arg[8:].split(",")

    user_target_list = HydraulicVariableUnitList()

    for i in range(len(run_choice["pref_file_list"])):
        # options
        pref_file = run_choice["pref_file_list"][i]
        stage = run_choice["stage_list"][i]
        hyd_opt = run_choice["hyd_opt"][i]
        sub_opt = run_choice["sub_opt"][i]

        # check_if_habitat_variable_is_valid
        if check_if_habitat_variable_is_valid(pref_file, stage, hyd_opt, sub_opt):
            # append_new_habitat_variable
            information_model_dict = get_biomodels_informations_for_database(pref_file)
            user_target_list.append_new_habitat_variable(information_model_dict["CdBiologicalModel"],
                                                         stage,
                                                         hyd_opt,
                                                         sub_opt,
                                                         information_model_dict["aquatic_animal_type"],
                                                         information_model_dict["ModelType"],
                                                         pref_file)

    if user_target_list:
        # run calculation
        progress_value = Value("d", 0)
        stop = Event()
        q = Queue()
        p = Process(target=src.calcul_hab_mod.calc_hab_and_output,
                    args=(hab_filename,
                          user_target_list,
                          progress_value,
                          q,
                          True,
                          project_preferences),
                    name="RUN_HABITAT")
        cli_start_process_and_print_progress(p, progress_value)


""" HS """


def cli_compute_hs(arguments, project_preferences):
    # if len(all_arg) != 4:
    #     print('RUN_HABITAT needs between four and five inputs. See LIST_COMMAND for more information.')
    #     return

    # get args
    for arg in arguments:

        arg_v1 = 'input_file='
        if arg[:len(arg_v1)] == arg_v1:
            hdf5_name = arg[len(arg_v1):]

        arg_v2 = 'input_class_file='
        if arg[:len(arg_v2)] == arg_v2:
            input_class_file = arg[len(arg_v2):]

        arg_v3 = 'export_mesh='
        if arg[:len(arg_v3)] == arg_v3:
            export_mesh = eval(arg[len(arg_v3):])

        arg_v4 = 'export_txt='
        if arg[:len(arg_v4)] == arg_v4:
            export_txt = eval(arg[len(arg_v4):])

    if hdf5_name and input_class_file:
        hydrosignature_description = dict(hs_export_mesh=export_mesh,
                                          hdf5_name=hdf5_name,
                                          hs_export_txt=export_txt,
                                          classhv=hydraulic_class_from_file(input_class_file))
        q = Queue()
        progress_value = Value("d", 0)
        # run calculation
        p = Process(target=hydraulic_process_mod.load_data_and_compute_hs,
                         args=(hydrosignature_description,
                               progress_value,
                               q,
                               False,
                               project_preferences),
                    name="hydrosignature computing")
        cli_start_process_and_print_progress(p, progress_value)


""" PROCESS """


def cli_start_process_and_print_progress(process, progress_value):
    start_time = time.time()
    process.start()
    while process.is_alive():
        running_time = time.time() - start_time
        print(process.name + " running " + str(round(progress_value.value, 1)) + " %, since " + str(round(running_time)) + " s.\r", end="")
    process.join()
    print("                                                                         \r", end="")  # clean line
    running_time = time.time() - start_time
    if progress_value.value == 100:
        print("# " + process.name + " finished (" + str(round(running_time)) + "s)")
    else:
        print("# Error : " + process.name + " crashed (" + str(round(running_time)) + "s)")




