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
import os
import os.path
import sys
from time import sleep
from io import StringIO
import numpy as np
from pandas import DataFrame
from multiprocessing import Pool, Lock
from shutil import copy as sh_copy


from src.merge_mod import merge, setup
from src.hydrosignature_mod import hscomparison
from src.translator_mod import get_translator
from src.project_properties_mod import create_default_project_properties_dict, load_project_properties
from src import hdf5_mod
from src.hydraulic_results_manager_mod import HydraulicSimulationResultsSelector, create_or_copy_index_hydrau_text_file
from src.data_2d_mod import Data2d


def load_hydraulic_cut_to_hdf5(hydrau_description, progress_value, q, print_cmd=False, project_preferences={}):
    """
    This function calls the function load_hydraulic and call the function cut_2d_grid()

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
    :param project_preferences: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    """
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_properties_dict()

    # progress
    progress_value.value = 10

    filename_source = hydrau_description["filename_source"].split(", ")

    delta_file = 80 / len(filename_source)

    data_2d = Data2d()  # data_2d
    hydrau_description["hyd_unit_correspondence"] = []  # always one reach by file ?
    # for each filename source
    for i, file in enumerate(filename_source):
        # get file informations
        hsr = HydraulicSimulationResultsSelector(file,
                                         hydrau_description["path_filename_source"],
                                         hydrau_description["model_type"],
                                         hydrau_description["path_prj"])
        # get timestep_name_list
        if hydrau_description["hydrau_case"] in {"1.a", "2.a"}:
            timestep_wish_list = [hsr.timestep_name_list]
        elif hydrau_description["hydrau_case"] in {"1.b"}:
            timestep_wish_list = [hydrau_description["timestep_list"]]
        elif hydrau_description["hydrau_case"] in {"2.b"}:
            timestep_wish_list = [[hydrau_description["timestep_list"][i]]]
        else:  # {"4.a", "4.b", "3.b", "3.a", "unknown"}:
            timestep_wish_list = hydrau_description["unit_list"]

        # multi_reach from several files
        if len(hydrau_description["reach_list"]) > 1 and len(filename_source) > 1:
            # load first reach
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[i])
            # check error
            if not data_2d_source:
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q and not print_cmd:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return

            data_2d.add_reach(data_2d_source, [0])
        # multi_reach from one files (HEC-RAS 2d, ASCII, .. ?)
        elif len(hydrau_description["reach_list"]) > 1 and len(filename_source) == 1:
            # load data
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[i])
            data_2d.add_reach(data_2d_source, list(range(len(hydrau_description["reach_list"]))))
        # one_reach
        else:
            # load data
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[0])
            # check error
            if not data_2d_source:
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q and not print_cmd:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return
            for reach_number in range(data_2d_source.reach_number):
                # data_2d
                data_2d.add_unit(data_2d_source, reach_number)

    """ get data_2d_whole_profile """
    data_2d_whole_profile = data_2d.get_only_mesh()

    """ set unit_names """
    data_2d.set_unit_list(hydrau_description["unit_list"])

    """ varying mesh """
    hyd_varying_xy_index, hyd_varying_z_index = data_2d_whole_profile.get_hyd_varying_xy_and_z_index()
    for reach_number in range(len(hyd_varying_xy_index)):
        if len(set(hyd_varying_xy_index[reach_number])) == 1:  # one tin for all unit
            hyd_varying_mesh = False
            data_2d_whole_profile.reduce_to_first_unit_by_reach()
        else:
            hyd_varying_mesh = True
        # hyd_unit_z_equal ?
        if len(set(hyd_varying_z_index[reach_number])) == 1:
            hyd_unit_z_equal = True
        else:
            hyd_unit_z_equal = True

        # one file : one reach, varying_mesh==False
        if len(filename_source) == 1:
            hydrau_description["hyd_unit_correspondence"].append(hyd_varying_xy_index[reach_number])
        else:
            hydrau_description["hyd_unit_correspondence"].append(hyd_varying_xy_index[reach_number])

    """ check_validity """
    data_2d.check_validity()

    """ set_min_height_to_0 """
    data_2d.set_min_height_to_0(project_preferences['min_height_hyd'])

    """ remove_dry_mesh """
    data_2d.remove_dry_mesh()
    if data_2d.unit_number == 0:
        print("Error: All selected units or timestep are entirely dry.")
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    """ semi_wetted_mesh_cutting """
    if project_preferences["cut_mesh_partialy_dry"]:
        data_2d.semi_wetted_mesh_cutting(hydrau_description["unit_list"],
                                         progress_value,
                                         delta_file)
    if data_2d.unit_number == 0:
        print("Error: All selected units or timestep are not hydraulically operable.")
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    """ bank hydraulic aberations  """
    # data_2d.fix_aberrations(npasses=1, tolerance=0.01, connectedness_criterion=True, bank_depth=0.05)
    # cProfile.runctx("data_2d.fix_aberrations(npasses=1, tolerance=0.01, connectedness_criterion=False, bank_depth=1)",globals={},locals={"data_2d":data_2d},filename="c:/habby_dev/files/cut6.profile")

    """ re compute area """
    if not data_2d.hvum.area.name in data_2d.hvum.hdf5_and_computable_list.names():
        data_2d.hvum.area.hdf5 = True  # variable
        data_2d.hvum.hdf5_and_computable_list.append(data_2d.hvum.area)
    data_2d.compute_variables([data_2d.hvum.area])

    """ remove null area """
    data_2d.remove_null_area()

    """ get_dimension """
    data_2d.get_dimension()

    # hyd description
    data_2d.filename_source = hydrau_description["filename_source"]
    data_2d.path_filename_source = hydrau_description["path_filename_source"]
    data_2d.hyd_model_type = hydrau_description["model_type"]
    data_2d.hyd_model_dimension = hydrau_description["model_dimension"]
    data_2d.epsg_code = hydrau_description["epsg_code"]
    data_2d.reach_list = hydrau_description["reach_list"]
    data_2d.reach_number = int(hydrau_description["reach_number"])
    data_2d.reach_type = hydrau_description["reach_type"]
    reach_unit_list_str = []
    for reach_number in range(data_2d.reach_number):
        unit_list_str = []
        for unit_name in hydrau_description["unit_list"][reach_number]:
            unit_list_str.append(unit_name.replace(":", "_").replace(" ", "_"))
        reach_unit_list_str.append(unit_list_str)
    data_2d.unit_list = reach_unit_list_str
    data_2d.unit_number = len(hydrau_description["unit_list"][0])
    data_2d.unit_type = hydrau_description["unit_type"]
    data_2d.hyd_varying_mesh = hyd_varying_mesh
    data_2d.hyd_unit_z_equal = hyd_unit_z_equal
    data_2d.hyd_unit_correspondence = hydrau_description["hyd_unit_correspondence"]
    data_2d.hyd_cuted_mesh_partialy_dry = project_preferences["cut_mesh_partialy_dry"]
    data_2d.hyd_hydrau_case = hydrau_description["hydrau_case"]
    if data_2d.hyd_hydrau_case in {"1.b", "2.b"}:
        data_2d.hyd_timestep_source_list = [hydrau_description["timestep_list"]]
    data_2d.hs_calculated = False

    # create hdf5
    path_prj = hydrau_description["path_prj"]
    hdf5_name = hydrau_description["hdf5_name"]
    hdf5 = hdf5_mod.Hdf5Management(path_prj, hdf5_name, new=True)
    # HYD
    if not data_2d.hvum.hdf5_and_computable_list.subs():
        project_preferences_index = 0
        hdf5.create_hdf5_hyd(data_2d,
                             data_2d_whole_profile,
                             project_preferences)
    # HAB
    else:
        project_preferences_index = 1
        data_2d.sub_mapping_method = hsr.sub_mapping_method
        data_2d.sub_classification_code = hsr.sub_classification_code
        data_2d.sub_classification_method = hsr.sub_classification_method
        hdf5.create_hdf5_hab(data_2d,
                             data_2d_whole_profile,
                             project_preferences)

    # create_index_hydrau_text_file
    if not project_preferences["restarted"]:
        create_or_copy_index_hydrau_text_file(hydrau_description)

    # export
    export_dict = dict()
    nb_export = 0
    for key in hdf5.available_export_list:
        if project_preferences[key][project_preferences_index]:
            nb_export += 1
        export_dict[key + "_" + hdf5.extension[1:]] = project_preferences[key][project_preferences_index]

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    progress_value.value = 100.0


def merge_grid_and_save(hdf5_name_hyd, hdf5_name_sub, hdf5_name_hab, path_prj, progress_value, q=[], print_cmd=False,
                        project_preferences={}):
    """
    This function call the merging of the grid between the grid from the hydrological data and the substrate data.
    It then save the merged data and the substrate data in a common hdf5 file. This function is called in a second
    thread to avoid freezin gthe GUI. This is why we have this extra-function just to call save_hdf5() and
    merge_grid_hydro_sub().

    :param hdf5_name_hyd: the name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the name of the hdf5 with the substrate data
    :param hdf5_name_hab: the name of the hdf5 merge output
    :param path_hdf5: the path to the hdf5 data
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: the type of the "model". In this case, it is just 'SUBSTRATE'
    :param q: used to share info with the GUI when this thread have finsihed (print_cmd = False)
    :param print_cmd: If False, print to the GUI (usually False)
    :param path_shp: the path where to save the shp file with hydro and subtrate. If empty, the shp file is not saved.
    :param: erase_id should we erase old shapefile from the same model or not.
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # progress
    progress_value.value = 10

    if not project_preferences:
        project_preferences = load_project_properties(path_prj)

    # get_translator
    qt_tr = get_translator(project_preferences['path_prj'])

    # if exists
    if not os.path.exists(os.path.join(path_prj, "hdf5", hdf5_name_hyd)):
        print('Error: ' + qt_tr.translate("mesh_management_mod",
                                          "The specified file : " + hdf5_name_hyd + " don't exist."))
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    if not os.path.exists(os.path.join(path_prj, "hdf5", hdf5_name_sub)):
        print('Error: ' + qt_tr.translate("mesh_management_mod",
                                          "The specified file : " + hdf5_name_sub + " don't exist."))
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    # load hdf5 hydro
    hdf5_hydro = hdf5_mod.Hdf5Management(path_prj, hdf5_name_hyd, new=False, edit=False)
    hdf5_hydro.load_hdf5(units_index="all", whole_profil=True)

    # load hdf5 sub
    hdf5_sub = hdf5_mod.Hdf5Management(path_prj, hdf5_name_sub, new=False, edit=False)
    hdf5_sub.load_hdf5_sub()

    # CONSTANT CASE
    if hdf5_sub.data_2d.sub_mapping_method == "constant":  # set default value to all mesh
        data_2d_merge = hdf5_hydro.data_2d
        data_2d_whole_merge = hdf5_hydro.data_2d_whole
        data_2d_merge.set_sub_cst_value(hdf5_sub)

    # POLYGON AND POINTS CASES
    elif hdf5_sub.data_2d.sub_mapping_method != "constant":
        # check if EPSG are integer and if TRUE they must be equal
        epsg_hyd = hdf5_hydro.data_2d.epsg_code
        epsg_sub = hdf5_sub.data_2d.epsg_code
        if epsg_hyd.isdigit() and epsg_sub.isdigit():
            if epsg_hyd == epsg_sub:
                hab_epsg_code = epsg_hyd
            if epsg_hyd != epsg_sub:
                print(
                    "Error : Merging failed. EPSG codes are different between hydraulic and substrate data : " + epsg_hyd + ", " + epsg_sub)
                return
        if not epsg_hyd.isdigit() and epsg_sub.isdigit():
            print(
                "Warning: EPSG code of hydraulic data is unknown (" + epsg_hyd + ") "
                                                                                  "and EPSG code of substrate data is known (" + epsg_sub + "). " +
                "The merging data will still be calculated.")
            hab_epsg_code = epsg_sub
        if epsg_hyd.isdigit() and not epsg_sub.isdigit():
            print(
                "Warning: EPSG code of hydraulic data is known (" + epsg_hyd + ") "
                                                                                "and EPSG code of substrate data is unknown (" + epsg_sub + "). " +
                "The merging data will still be calculated.")
            hab_epsg_code = epsg_hyd
        if not epsg_hyd.isdigit() and not epsg_sub.isdigit():
            print(
                "Warning: EPSG codes of hydraulic and substrate data are unknown : " + epsg_hyd + " ; "
                + epsg_sub + ". The merging data will still be calculated.")
            hab_epsg_code = epsg_hyd

        # check if extent match
        extent_hyd = hdf5_hydro.data_2d.data_extent
        extent_sub = hdf5_sub.data_2d.data_extent
        if (extent_hyd[2] < extent_sub[0] or extent_hyd[0] > extent_sub[2] or
                extent_hyd[3] < extent_sub[1] or extent_hyd[1] > extent_sub[3]):
            print("Warning: No intersection found between hydraulic and substrate data (from extent intersection).")
            extent_intersect = False
        else:
            extent_intersect = True

        # check if whole profile is equal for all timestep
        if not hdf5_hydro.data_2d.hyd_varying_mesh:
            # have to check intersection for only one timestep
            pass
        else:
            # TODO : merge for all time step
            pass

        # no intersect
        if not extent_intersect:  # set default value to all mesh
            data_2d_merge = hdf5_hydro.data_2d
            data_2d_whole_merge = hdf5_hydro.data_2d_whole
            data_2d_merge.set_sub_cst_value(hdf5_sub)
        # intersect
        else:
            data_2d_merge = Data2d(reach_number=hdf5_hydro.data_2d.reach_number,
                                   unit_number=hdf5_hydro.data_2d.unit_number)  # new
            # get hyd attr
            data_2d_merge.__dict__ = hdf5_hydro.data_2d.__dict__.copy()
            data_2d_merge.__dict__["hyd_filename_source"] = data_2d_merge.__dict__.pop("filename_source")
            data_2d_merge.__dict__["hyd_path_filename_source"] = data_2d_merge.__dict__.pop("path_filename_source")
            # get sub attr
            for attribute_name in hdf5_sub.data_2d.__dict__.keys():
                attribute_value = getattr(hdf5_sub.data_2d, attribute_name)
                if attribute_name in {"filename_source", "path_filename_source"}:
                    setattr(data_2d_merge, "sub_" + attribute_name, attribute_value)
                if attribute_name[:3] == "sub":
                    setattr(data_2d_merge, attribute_name, attribute_value)
            data_2d_merge.hab_animal_list = ", ".join([])
            data_2d_merge.hab_animal_number = 0
            data_2d_merge.hab_animal_pref_list = ", ".join([])
            data_2d_merge.hab_animal_stage_list = ", ".join([])

            data_2d_whole_merge = hdf5_hydro.data_2d_whole
            data_2d_merge.epsg_code = hab_epsg_code

            data_2d_merge.hvum = hdf5_hydro.data_2d.hvum  # hyd variables
            data_2d_merge.hvum.hdf5_and_computable_list.extend(hdf5_sub.data_2d.hvum.hdf5_and_computable_list)  # sub variables
            hyd_xy_list = []
            hyd_data_node_list = []
            hyd_tin_list = []
            iwholeprofile_list = []
            i_split_list = []
            hyd_data_mesh_list = []
            sub_xy_list = []
            sub_tin_list = []
            sub_data_list = []
            sub_default_list = []
            coeffgrid_list = []
            delta_mesh_list = []
            # progress
            delta_reach = 80 / hdf5_hydro.data_2d.reach_number
            # for each reach
            for reach_number in range(0, hdf5_hydro.data_2d.reach_number):
                # progress
                delta_unit = delta_reach / hdf5_hydro.data_2d.unit_number
                # for each unit
                for unit_number in range(0, hdf5_hydro.data_2d.unit_number):
                    # progress
                    delta_mesh = delta_unit / hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["tin"].shape[0]

                    # conta args to list to Pool
                    hyd_xy_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["node"]["xy"])
                    hyd_data_node_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["node"]["data"].to_numpy())
                    hyd_tin_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["tin"])
                    iwholeprofile_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"])
                    i_split_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["data"]["i_split"])
                    hyd_data_mesh_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["data"].to_numpy())
                    sub_xy_list.append(hdf5_sub.data_2d[0][0]["node"]["xy"])
                    sub_tin_list.append(hdf5_sub.data_2d[0][0]["mesh"]["tin"])
                    sub_data_list.append(hdf5_sub.data_2d[0][0]["mesh"]["data"].to_numpy())
                    sub_default_list.append(np.array(hdf5_sub.data_2d.sub_default_values))
                    coeffgrid_list.append(10)
                    delta_mesh_list.append(delta_mesh)

            # Compute Pool
            input_data = zip(hyd_xy_list,
                             hyd_data_node_list,
                             hyd_tin_list,
                             iwholeprofile_list,
                             i_split_list,
                             hyd_data_mesh_list,
                             sub_xy_list,
                             sub_tin_list,
                             sub_data_list,
                             sub_default_list,
                             coeffgrid_list,
                             delta_mesh_list)

            # start jobs
            lock = Lock()  # to share progress_value
            pool = Pool(processes=2, initializer=setup, initargs=[progress_value, lock])
            results = pool.starmap(merge, input_data)

            # for each reach
            index_loop = -1
            for reach_number in range(0, hdf5_hydro.data_2d.reach_number):
                # for each unit
                for unit_number in range(0, hdf5_hydro.data_2d.unit_number):
                    index_loop = index_loop + 1
                    merge_xy, merge_data_node, merge_tin, merge_i_whole_profile, merge_data_mesh, merge_data_sub = results[index_loop]

                    # get mesh data
                    data_2d_merge[reach_number][unit_number]["mesh"]["tin"] = merge_tin
                    data_2d_merge[reach_number][unit_number]["mesh"]["data"] = DataFrame()
                    for colname_num, colname in enumerate(hdf5_hydro.data_2d[0][0]["mesh"]["data"].columns):
                        if colname == "i_whole_profile":
                            data_2d_merge[reach_number][unit_number]["mesh"]["data"][colname] = merge_i_whole_profile[:, 0]
                        elif colname == "i_split":
                            data_2d_merge[reach_number][unit_number]["mesh"]["data"][colname] = merge_i_whole_profile[:, 1]
                        else:
                            data_2d_merge[reach_number][unit_number]["mesh"]["data"][colname] = merge_data_mesh[:, colname_num]
                    data_2d_merge[reach_number][unit_number]["mesh"]["i_whole_profile"] = merge_i_whole_profile[:, 0]
                    # sub_defaut
                    data_2d_merge[reach_number][unit_number]["mesh"]["data"][data_2d_merge.hvum.i_sub_defaut.name] = merge_i_whole_profile[:, 2]

                    # get mesh sub data
                    for sub_class_num, sub_class_name in enumerate(
                            hdf5_sub.data_2d.hvum.hdf5_and_computable_list.hdf5s().names()):
                        data_2d_merge[reach_number][unit_number]["mesh"]["data"][sub_class_name] = merge_data_sub[:,
                                                                                             sub_class_num]

                    # get node data
                    data_2d_merge[reach_number][unit_number]["node"]["xy"] = merge_xy
                    data_2d_merge[reach_number][unit_number]["node"]["data"] = DataFrame()
                    for colname_num, colname in enumerate(hdf5_hydro.data_2d[0][0]["node"]["data"].columns):
                        data_2d_merge[reach_number][unit_number]["node"]["data"][colname] = merge_data_node[:, colname_num]

                    # post process merge
                    if data_2d_merge[reach_number][unit_number]["node"]["data"][data_2d_merge.hvum.h.name].min() < 0:
                        print("Error: negative water height values detected after merging with substrate.")

                    # # plot_to_check_mesh_merging
                    # plot_to_check_mesh_merging(hyd_xy=hdf5_hydro.data_2d[reach_number][unit_number]["node"]["xy"],
                    #                            hyd_tin=hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["tin"],
                    #
                    #                            sub_xy=hdf5_sub.data_2d[reach_number][unit_number]["node"]["xy"],
                    #                            sub_tin=hdf5_sub.data_2d[reach_number][unit_number]["mesh"]["tin"],
                    #                            sub_data=hdf5_sub.data_2d[reach_number][unit_number]["mesh"]["data"]["sub_coarser"].to_numpy(),
                    #
                    #                            merge_xy=data_2d_merge[reach_number][unit_number]["node"]["xy"],
                    #                            merge_tin=data_2d_merge[reach_number][unit_number]["mesh"]["tin"],
                    #                            merge_data=data_2d_merge[reach_number][unit_number]["mesh"]["data"]["sub_coarser"].to_numpy())

            # new variables
            data_2d_merge.hvum.i_sub_defaut.position = "mesh"
            data_2d_merge.hvum.i_sub_defaut.hdf5 = True
            data_2d_merge.hvum.hdf5_and_computable_list.append(data_2d_merge.hvum.i_sub_defaut)

            # compute area (always after merge)
            data_2d_merge.hvum.area.hdf5 = False
            data_2d_merge.hvum.area.position = "mesh"
            data_2d_merge.hvum.all_final_variable_list.append(data_2d_merge.hvum.area)
            data_2d_merge.compute_variables(data_2d_merge.hvum.all_final_variable_list.to_compute())
            if not data_2d_merge.hvum.area.name in data_2d_merge.hvum.hdf5_and_computable_list.names():
                data_2d_merge.hvum.area.hdf5 = True
                data_2d_merge.hvum.hdf5_and_computable_list.append(data_2d_merge.hvum.area)

            # get_dimension
            data_2d_merge.get_dimension()

    # progress
    progress_value.value = 90

    # create hdf5 hab
    data_2d_merge.filename = hdf5_name_hab
    hdf5 = hdf5_mod.Hdf5Management(path_prj, hdf5_name_hab, new=True)
    hdf5.create_hdf5_hab(data_2d_merge, data_2d_whole_merge, project_preferences)

    # export
    export_dict = dict()
    nb_export = 0
    for key in hdf5.available_export_list:
        if project_preferences[key][1]:
            nb_export += 1
        export_dict[key + "_" + hdf5.extension[1:]] = project_preferences[key][1]

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0


def load_data_and_compute_hs(hydrosignature_description, progress_value, q=[], print_cmd=False, project_preferences={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_properties_dict()

    # progress
    progress_value.value = 10

    path_prj = project_preferences["path_prj"]

    # compute
    if hydrosignature_description["hs_export_mesh"]:
        hdf5 = hdf5_mod.Hdf5Management(path_prj, hydrosignature_description["hdf5_name"], new=False, edit=True)
        hdf5.hydrosignature_new_file(progress_value,
                                     hydrosignature_description["classhv"],
                                     hydrosignature_description["hs_export_txt"])
        # load new hs_data to original hdf5
        hdf5_new = hdf5_mod.Hdf5Management(path_prj, hdf5.filename[:-4] + "_HS" + hdf5.extension, new=False, edit=False)
        hdf5_new.load_hydrosignature()
        hdf5.data_2d = hdf5_new.data_2d
        hdf5.write_hydrosignature()
    else:
        hdf5 = hdf5_mod.Hdf5Management(path_prj, hydrosignature_description["hdf5_name"], new=False, edit=True)
        hdf5.add_hs(progress_value,
                    hydrosignature_description["classhv"],
                    False,
                    hydrosignature_description["hs_export_txt"])
        # check error
        if not hdf5.hs_calculated:
            # warnings
            if not print_cmd:
                sys.stdout = sys.__stdout__
                if q and not print_cmd:
                    q.put(mystdout)
                    sleep(0.1)  # to wait q.put() ..
            return

    # hs input hydraulic class save to input folder
    folder_name = os.path.splitext(hdf5.filename)[0]
    hs_input_class_folder_path_out = os.path.join(project_preferences["path_prj"], "input", folder_name)
    if not os.path.exists(hs_input_class_folder_path_out):
        os.makedirs(hs_input_class_folder_path_out)
    hs_input_class_folder_path_in = os.path.join(hydrosignature_description["classhv_input_class_file_info"]["path"], hydrosignature_description["classhv_input_class_file_info"]["file"])
    sh_copy(hs_input_class_folder_path_in, os.path.join(hs_input_class_folder_path_out, hydrosignature_description["classhv_input_class_file_info"]["file"]))
    if hydrosignature_description["hs_export_mesh"]:
        folder_name_new_hs = os.path.splitext(hdf5_new.filename)[0]
        new_hs_input_class_folder_path_out = os.path.join(project_preferences["path_prj"], "input", folder_name_new_hs)
        if not os.path.exists(new_hs_input_class_folder_path_out):
            os.makedirs(new_hs_input_class_folder_path_out)
        sh_copy(hs_input_class_folder_path_in, os.path.join(new_hs_input_class_folder_path_out, hydrosignature_description["classhv_input_class_file_info"]["file"]))

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0


def load_hs_and_compare(hdf5name_1, reach_index_list_1, unit_index_list_1,
                        hdf5name_2, reach_index_list_2, unit_index_list_2,
                        all_possibilities, out_filename, path_prj):
    # create hdf5 class
    hdf5_1 = hdf5_mod.Hdf5Management(path_prj, hdf5name_1, new=False, edit=False)
    hdf5_1.load_hydrosignature()
    hdf5_2 = hdf5_mod.Hdf5Management(path_prj, hdf5name_2, new=False, edit=False)
    hdf5_2.load_hydrosignature()

    name_list_1 = [""]
    name_list_2 = [""]
    table_list_1 = []
    table_list_2 = []
    reach_name_1_list = []
    unit_name_1_list = []
    for reach_num_1 in reach_index_list_1:
        for unit_num_1 in unit_index_list_1:
            reach_name_1 = hdf5_1.data_2d[reach_num_1][unit_num_1].reach_name
            unit_name_1 = hdf5_1.data_2d[reach_num_1][unit_num_1].unit_name
            col_name = hdf5name_1 + "_" + reach_name_1 + "_" + unit_name_1
            name_list_1.append(col_name)
            table_list_1.append((hdf5_1, reach_num_1, unit_num_1))
            # templist
            reach_name_1_list.append(reach_name_1)
            unit_name_1_list.append(unit_name_1)
    for reach_num_2 in reach_index_list_2:
        for unit_num_2 in unit_index_list_2:
            reach_name_2 = hdf5_2.data_2d[reach_num_2][unit_num_2].reach_name
            unit_name_2 = hdf5_2.data_2d[reach_num_2][unit_num_2].unit_name
            col_name = hdf5name_2 + "_" + reach_name_2 + "_" + unit_name_2
            # all same
            if not all_possibilities:
                if reach_name_2 in reach_name_1_list and unit_name_2 in unit_name_1_list:
                    name_list_2.append(col_name)
                    table_list_2.append((hdf5_2, reach_num_2, unit_num_2))
            else:
                name_list_2.append(col_name)
                table_list_2.append((hdf5_2, reach_num_2, unit_num_2))

    # compute combination
    combination_list = []
    for i in table_list_1:
        for j in table_list_2:
            combination_list.append((i, j))

    # compute hscomparison area
    data_list = []
    for comb in combination_list:
        # first
        first_comp = comb[0]
        classhv1 = first_comp[0].hs_input_class
        hs1 = first_comp[0].data_2d[first_comp[1]][first_comp[2]].hydrosignature["hsarea"]
        # second
        second_comp = comb[1]
        classhv2 = second_comp[0].hs_input_class
        hs2 = second_comp[0].data_2d[second_comp[1]][second_comp[2]].hydrosignature["hsarea"]
        # comp
        done_tf, hs_comp_value = hscomparison(classhv1=classhv1,
                                              hs1=hs1,
                                              classhv2=classhv2,
                                              hs2=hs2)
        # append
        data_list.append(str(hs_comp_value))

    row_area_list = []
    for ind, x in enumerate(range(0, len(data_list), len(name_list_2) - 1)):
        row_list = [name_list_1[ind + 1]] + data_list[x:x + len(name_list_2) - 1]
        row_area_list.append(row_list)
    row_area_list.insert(0, name_list_2)

    # compute hscomparison volume
    data_list = []
    for comb in combination_list:
        # first
        first_comp = comb[0]
        classhv1 = first_comp[0].hs_input_class
        hs1 = first_comp[0].data_2d[first_comp[1]][first_comp[2]].hydrosignature["hsvolume"]
        # second
        second_comp = comb[1]
        classhv2 = second_comp[0].hs_input_class
        hs2 = second_comp[0].data_2d[second_comp[1]][second_comp[2]].hydrosignature["hsvolume"]
        # comp
        done_tf, hs_comp_value = hscomparison(classhv1=classhv1,
                                              hs1=hs1,
                                              classhv2=classhv2,
                                              hs2=hs2)
        # append
        data_list.append(str(hs_comp_value))

    row_volume_list = []
    for ind, x in enumerate(range(0, len(data_list), len(name_list_2) - 1)):
        row_list = [name_list_1[ind + 1]] + data_list[x:x + len(name_list_2) - 1]
        row_volume_list.append(row_list)
    row_volume_list.insert(0, name_list_2)

    # write file
    f = open(os.path.join(path_prj, "output", "text", out_filename), 'w')
    f.write("area" + '\n')
    for row in row_area_list:
        f.write("\t".join(row) + '\n')
    f.write('\n' + "volume" + '\n')
    for row in row_volume_list:
        f.write("\t".join(row) + '\n')
    f.close()


