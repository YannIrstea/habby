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
import time
import os
from copy import deepcopy
from multiprocessing import Value, Queue, Process
import psutil
import numpy as np
from PyQt5.QtCore import QThread, QObject
from time import sleep

from src import plot_mod
from src.calcul_hab_mod import calc_hab_and_output
from src.hdf5_mod import Hdf5Management
from src.hydraulic_process_mod import load_hydraulic_cut_to_hdf5, merge_grid_and_save, load_data_and_compute_hs
from src.substrate_mod import load_sub
from src.bio_info_mod import read_pref, get_hydrosignature
from src.project_properties_mod import available_export_list
from src.tools_mod import compute_interpolation, export_text_interpolatevalues
from src.plot_mod import create_map_plot_string_dict
from src.hrr import hrr
from src.mesh_manager_mod import mesh_manager


class MyProcessManager(QThread):
    """
    """
    def __init__(self, type):
        QThread.__init__(self)
        self.plot_production_stopped = False
        self.thread_started = False
        self.all_process_runned = False
        self.nb_finished = 0
        self.export_finished = False
        self.nb_hs_total = 0
        self.process_type = type  # hs or plot or export
        if self.process_type == "hyd":
            self.process_type_gui = self.tr("Hydraulic")
        elif self.process_type == "sub":
            self.process_type_gui = self.tr("Substrate")
        elif self.process_type == "merge":
            self.process_type_gui = self.tr("Merge")
        elif self.process_type == "hab":
            self.process_type_gui = self.tr("Habitat")
        elif self.process_type == "hs":
            self.process_type_gui = self.tr("Hydrosignature")
        elif self.process_type == "export":
            self.process_type_gui = self.tr("Export")
        elif self.process_type == "plot":
            self.process_type_gui = self.tr("Figure")
        elif self.process_type == "hs_plot":
            self.process_type_gui = self.tr("Hydrosignature figure")
        else:
            self.process_type_gui = self.process_type.capitalize()
        self.process_list = MyProcessList()
        self.save_process = []
        self.interp_attr = lambda: None
        self.interp_attr.mode = None
        self.export_hdf5_mode = False
        self.progress_value = 0.0

    # hyd
    def set_hyd_mode(self, path_prj, hydrau_description_multiple, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("hyd")
        else:
            self.add_plots(1)
        self.path_prj = path_prj
        self.hydrau_description_multiple = hydrau_description_multiple
        self.names_hdf5 = [hydrau_description["hdf5_name"] for hydrau_description in self.hydrau_description_multiple]
        self.project_properties = project_properties

    def hyd_process(self):
        # for each .hyd (or .hab) to create
        for hdf5_file_index in range(0, len(self.hydrau_description_multiple)):
            # class MyProcess
            progress_value = Value("d", 0.0)
            q = Queue()
            my_process = MyProcess(p=Process(target=load_hydraulic_cut_to_hdf5,
                                             args=(self.hydrau_description_multiple[hdf5_file_index],
                                               progress_value,
                                               q,
                                               False,
                                               self.project_properties),
                                             name=self.hydrau_description_multiple[hdf5_file_index]["hdf5_name"] + self.tr(" creation")),
                               progress_value=progress_value,
                               q=q)
            self.process_list.append(my_process)

    # sub
    def set_sub_mode(self, path_prj, sub_description, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("sub")
        else:
            self.add_plots(1)
        self.path_prj = path_prj
        self.sub_description = sub_description
        self.project_properties = project_properties

    def sub_process(self):
        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()
        my_process = MyProcess(p=Process(target=load_sub,
                                         args=(self.sub_description,
                                           progress_value,
                                           q,
                                           False,
                                           self.project_properties),
                                         name=self.sub_description["name_hdf5"] + self.tr(" creation")),
                           progress_value=progress_value,
                           q=q)
        self.process_list.append(my_process)

    # merge
    def set_merge_mode(self, path_prj, hdf5_name_hyd, hdf5_name_sub, name_hdf5, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("merge")
        else:
            self.add_plots(1)
        self.path_prj = path_prj
        self.hdf5_name_hyd = hdf5_name_hyd
        self.hdf5_name_sub = hdf5_name_sub
        self.name_hdf5 = name_hdf5
        self.project_properties = project_properties

    def merge_process(self):
        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()
        my_process = MyProcess(p=Process(target=merge_grid_and_save,
                                         args=(self.hdf5_name_hyd,
                                               self.hdf5_name_sub,
                                               self.name_hdf5,
                                               self.path_prj,
                                               progress_value,
                                               q,
                                               False,
                                               self.project_properties),
                                         name=self.name_hdf5 + self.tr(" creation")),
                               progress_value=progress_value,
                               q=q)
        self.process_list.append(my_process)

    # hab
    def set_hab_mode(self, path_prj, user_target_list, name_hdf5, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("hab")
        else:
            self.add_plots(1)
        self.path_prj = path_prj
        self.user_target_list = user_target_list
        self.name_hdf5 = name_hdf5
        self.project_properties = project_properties

    def hab_process(self):
        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()
        my_process = MyProcess(p=Process(target=calc_hab_and_output,
                                         args=(self.name_hdf5,
                                               self.user_target_list,
                                               progress_value,
                                               q,
                                               False,
                                               self.project_properties),
                                         name=self.name_hdf5 + self.tr(" habitat calculation")),
                               progress_value=progress_value,
                               q=q)
        self.process_list.append(my_process)

    # plot
    def set_plot_hdf5_mode(self, path_prj, names_hdf5, plot_attr, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__(self.process_type)
        else:
            self.add_plots(plot_attr.nb_plot)
        self.path_prj = path_prj
        self.names_hdf5 = names_hdf5
        self.plot_attr = plot_attr
        self.project_properties = project_properties

    def load_data_and_append_plot_process(self):
        for name_hdf5 in self.names_hdf5:
            self.hdf5 = Hdf5Management(self.path_prj, name_hdf5, new=False, edit=False)
            self.hvum = self.plot_attr.hvum
            reach = self.plot_attr.reach
            plot_type = self.plot_attr.plot_type
            units_index = self.plot_attr.units_index
            units = self.plot_attr.units

            # load data
            if self.hdf5.hdf5_type in ("hydraulic", "habitat"):
                self.hdf5.load_hdf5(units_index=units_index,
                                    user_target_list=self.hvum.user_target_list,
                                    whole_profil=True)

            # load substrate data
            elif self.hdf5.hdf5_type == "substrate":
                self.hdf5.load_hdf5_sub(user_target_list=self.hvum.user_target_list)

            habitat_variable_list = self.hdf5.data_2d.hvum.all_final_variable_list.habs()
            light_data_2d = self.hdf5.data_2d.get_light_data_2d()

            # all cases
            unit_type = light_data_2d.unit_type[light_data_2d.unit_type.find('[') + len('['):light_data_2d.unit_type.find(
                            ']')]

            # for each reach
            for reach_name in reach:
                reach_number = light_data_2d.reach_list.index(reach_name)

                # hab data (OSI and WUA) not maps
                if habitat_variable_list and plot_type != ["map"] and not self.plot_production_stopped:
                    # class MyProcess
                    progress_value = Value("d", 0.0)
                    q = Queue()
                    my_process = MyProcess(p=Process(target=plot_mod.plot_fish_osi_wua,
                                                     args=(progress_value,
                                                             self.hdf5.data_2d,
                                                             reach_number,
                                                             habitat_variable_list,
                                                             self.project_properties),
                                                     name="plot_fish_osi_wua"),
                                           progress_value=progress_value,
                                           q=q)
                    self.process_list.append(my_process)

                # for each desired units ==> maps
                if plot_type != ["result"]:
                    for unit_index, unit_number in enumerate(units_index[reach_number]):
                        # string_tr
                        string_tr = [self.tr("reach"), self.tr("unit")]
                        """ MAP """
                        if self.plot_attr.plot_map_QCheckBoxisChecked:
                            # plot
                            for variable in self.hvum.user_target_list.no_habs():
                                if not self.plot_production_stopped:
                                    plot_string_dict = create_map_plot_string_dict(light_data_2d.filename,
                                                                                   reach_name,
                                                                                   units[reach_number][unit_index],
                                                                                   unit_type,
                                                                                   variable,
                                                                                   string_tr)
                                    # class MyProcess
                                    progress_value = Value("d", 0.0)
                                    q = Queue()
                                    if variable.name in (self.hvum.sub_coarser.name, self.hvum.sub_dom.name):
                                        my_process = MyProcess(p=Process(target=getattr(plot_mod, "plot_map_substrate"),
                                                                   args=(
                                                                       progress_value,
                                                                       self.hdf5.data_2d[reach_number][unit_number]["node"]["xy"],
                                                                       self.hdf5.data_2d[reach_number][unit_number]["mesh"]["tin"],
                                                                       self.hdf5.data_2d[reach_number][unit_number][variable.position]["data"][variable.name].to_numpy(),
                                                                       plot_string_dict,
                                                                       light_data_2d,
                                                                       self.project_properties
                                                                   ),
                                                                   name=plot_string_dict["title"]),
                                                               progress_value=progress_value,
                                                               q=q)
                                    else:
                                        my_process = MyProcess(p=Process(target=getattr(plot_mod, "plot_map_" + variable.position),
                                                                   args=(
                                                                       progress_value,
                                                                       self.hdf5.data_2d[reach_number][unit_number]["node"]["xy"],
                                                                       self.hdf5.data_2d[reach_number][unit_number]["mesh"]["tin"],
                                                                       self.hdf5.data_2d[reach_number][unit_number][variable.position]["data"][variable.name].to_numpy(),
                                                                       plot_string_dict,
                                                                       light_data_2d,
                                                                       self.project_properties
                                                                   ),
                                                                   name=plot_string_dict["title"]),
                                                               progress_value=progress_value,
                                                               q=q)
                                    self.process_list.append(my_process)

                            # plot animal map
                            for animal in habitat_variable_list:
                                if not self.plot_production_stopped:
                                    plot_string_dict = create_map_plot_string_dict(light_data_2d.filename,
                                                                                   reach_name,
                                                                                   units[reach_number][unit_index],
                                                                                   unit_type,
                                                                                   animal,
                                                                                   string_tr,
                                                                                   'OSI = {0:3.2f}'.format(animal.osi[reach_number][unit_number]) +
                                                                                   " / WUA = " + '{0:3.2f}'.format(
                                                                                       animal.wua[reach_number][unit_number]) + " m²" +
                                                                                   " / UA = " + '{0:3.2f}'.format(animal.percent_area_unknown[reach_number][unit_number]) + " %")

                                    # class MyProcess
                                    progress_value = Value("d", 0.0)
                                    q = Queue()
                                    my_process = MyProcess(p=Process(target=plot_mod.plot_map_fish_habitat,
                                                                  args=(
                                                                      progress_value,
                                                                      self.hdf5.data_2d[reach_number][unit_number]["node"]["xy"],
                                                                      self.hdf5.data_2d[reach_number][unit_number]["mesh"]["tin"],
                                                                      self.hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name],
                                                                      plot_string_dict,
                                                                      light_data_2d,
                                                                      self.project_properties
                                                                  ),
                                                                  name=plot_string_dict["title"]),
                                                           progress_value=progress_value,
                                                           q=q)
                                    self.process_list.append(my_process)

                # # class MyProcess
                # progress_value = Value("d", 0.0)
                # q = Queue()
                # my_process = MyProcess(p=Process(target=plot_mod.create_gif_from_files,
                #                                  args=(progress_value,
                #                                animal.name,
                #                                reach_name,
                #                                units,
                #                                light_data_2d.filename,
                #                                self.project_properties),
                #                                  name=animal.name),
                #                        progress_value=progress_value,
                #                        q=q)
                # self.process_list.append(my_process)

    # export
    def set_export_hdf5_mode(self, path_prj, names_hdf5, project_properties):
        self.export_available = [""]
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("export")
        else:
            self.__init__("export")
        self.path_prj = path_prj
        self.names_hdf5 = names_hdf5
        self.project_properties = project_properties
        self.export_hdf5_mode = True

    def check_if_one_default_export_is_enabled(self):
        if self.process_type == "hyd":
            index_export = 0
        elif self.process_type in ("merge", "hab"):
            index_export = 1

        one_default_export_is_enabled = False
        for key in available_export_list:
            if self.project_properties[key][index_export]:
                one_default_export_is_enabled = True
                break

        return one_default_export_is_enabled

    def load_data_and_append_export_process(self):
        for name_hdf5 in self.names_hdf5:
            hdf5 = Hdf5Management(self.path_prj, name_hdf5, new=False, edit=False)
            hdf5.close_file()
            """ LOADING """
            # hydraulic
            if hdf5.hdf5_type == "hydraulic":  # load hydraulic data
                index_export = 0

            # habitat
            elif hdf5.hdf5_type == "habitat":  # load habitat data
                index_export = 1

            """ APPEND PROCESS """
            if self.project_properties["mesh_whole_profile"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_gpkg_mesh_whole_profile,
                                                 args=(progress_value,),
                                                 name="gpkg_mesh_whole_profile"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)
            if self.project_properties["point_whole_profile"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_gpkg_point_whole_profile,
                                                 args=(progress_value,),
                                                 name="gpkg_point_whole_profile"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)
            if self.project_properties["mesh_units"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_gpkg_mesh_units,
                                                 args=(progress_value,),
                                                 name="gpkg_mesh_units"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)
            if self.project_properties["point_units"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_gpkg_point_units,
                                                 args=(progress_value,),
                                                 name="gpkg_point_units"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)

            # export_stl
            if self.project_properties["elevation_whole_profile"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_stl,
                                             args=(progress_value,),
                                             name="stl_whole_profile"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)

            # export_paraview
            if self.project_properties["variables_units"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_paraview,
                                                 args=(progress_value,),
                                                 name="paraview_mesh_units"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)

            # mesh_detailled_text
            if self.project_properties["mesh_detailled_text"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_detailled_mesh_txt,
                                                 args=(progress_value,),
                                                 name="txt_mesh_units"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)

            # point_detailled_text
            if self.project_properties["point_detailled_text"][index_export]:
                # class MyProcess
                progress_value = Value("d", 0.0)
                q = Queue()
                my_process = MyProcess(p=Process(target=hdf5.export_detailled_point_txt,
                                                 args=(progress_value,),
                                                 name="txt_point_units"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)

            # habitat
            if hdf5.hdf5_type == "habitat":  # load habitat data
                # fish_information_hab
                if self.project_properties["fish_information"][index_export]:
                    # class MyProcess
                    progress_value = Value("d", 0.0)
                    q = Queue()
                    my_process = MyProcess(p=Process(target=hdf5.export_report,
                                                     args=(progress_value,),
                                                     name="report_suitability_curve"),
                                           progress_value=progress_value,
                                           q=q)
                    self.process_list.append(my_process)

    # hs
    def set_hs_hdf5_mode(self, path_prj, hs_description_dict, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("hs")
        else:
            self.add_plots(1)

        self.path_prj = path_prj
        self.hs_description_dict = hs_description_dict
        self.project_properties = project_properties

    def load_data_and_append_hs_process(self):
        self.process_list = MyProcessList()
        for hdf5_name in self.hs_description_dict["hdf5_name_list"]:
            hs_description_dict = deepcopy(self.hs_description_dict)
            hs_description_dict["hdf5_name"] = hdf5_name
            # class MyProcess
            progress_value = Value("d", 0.0)
            q = Queue()
            my_process = MyProcess(p=Process(target=load_data_and_compute_hs,
                                             args=(hs_description_dict,
                                                   progress_value,
                                                   q,
                                                   False,
                                                   self.project_properties),
                                             name=hdf5_name),
                                   progress_value=progress_value,
                                   q=q)
            self.process_list.append(my_process)

    def set_mesh_manager(self, path_prj, mesh_manager_dict, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("mesh_manager")
        else:
            self.add_plots(1)

        self.path_prj = path_prj
        self.mesh_manager_description_dict = mesh_manager_dict
        self.project_properties = project_properties

    def load_data_and_append_mesh_manager_process(self):
        self.process_list = MyProcessList()
        for hdf5_name in self.mesh_manager_description_dict["hdf5_name_list"]:
            mesh_manager_description_dict = deepcopy(self.mesh_manager_description_dict)
            mesh_manager_description_dict["hdf5_name"] = hdf5_name
            # class MyProcess
            progress_value = Value("d", 0.0)
            q = Queue()
            my_process = MyProcess(p=Process(target=mesh_manager,
                                             args=(mesh_manager_description_dict,
                                                   progress_value,
                                                   q,
                                                   False,
                                                   self.project_properties),
                                             name=hdf5_name),
                                   progress_value=progress_value,
                                   q=q)
            self.process_list.append(my_process)

    # hrr
    def set_hrr_hdf5_mode(self, path_prj, hrr_description_dict, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("hrr")
        else:
            self.add_plots(1)

        self.path_prj = path_prj
        self.hrr_description_dict = hrr_description_dict
        self.project_properties = project_properties

    def load_data_and_append_hrr_process(self):
        self.process_list = MyProcessList()
        for hdf5_name in self.hrr_description_dict["hdf5_name_list"]:
            hrr_description_dict = deepcopy(self.hrr_description_dict)
            hrr_description_dict["hdf5_name"] = hdf5_name
            # class MyProcess
            progress_value = Value("d", 0.0)
            q = Queue()
            my_process = MyProcess(p=Process(target=hrr,
                                             args=(hrr_description_dict,
                                                   progress_value,
                                                   q,
                                                   False,
                                                   self.project_properties),
                                             name=hdf5_name),
                                   progress_value=progress_value,
                                   q=q)
            self.process_list.append(my_process)


    # hs plot
    def load_data_and_append_hs_plot_process(self):
        for name_hdf5 in self.names_hdf5:
            hdf5 = Hdf5Management(self.path_prj, name_hdf5, new=False, edit=False)

            # create hdf5 class
            hdf5.load_hydrosignature()
            hdf5.close_file()

            # class MyProcess
            progress_value = Value("d", 0.0)
            q = Queue()

            if self.plot_attr.hs_plot_type in ("area", "volume"):
                # loop
                for reach_number in self.plot_attr.reach:
                    for unit_number in self.plot_attr.units:
                        my_process = MyProcess(p=Process(target=plot_mod.plot_hydrosignature,
                                                         args=(progress_value,
                                                               hdf5.data_2d[reach_number][unit_number].hydrosignature["hs" + self.plot_attr.hs_plot_type],
                                                               hdf5.hs_input_class[1],
                                                               hdf5.hs_input_class[0],
                                                               self.plot_attr.hs_plot_type + " hydrosignature : " + hdf5.data_2d[reach_number][unit_number].reach_name + " at " + \
                                    hdf5.data_2d[reach_number][unit_number].unit_name + " " + hdf5.data_2d.unit_type[
                                                                                              hdf5.data_2d.unit_type.find(
                                                                                                  '[') + len(
                                                                                                  '['):hdf5.data_2d.unit_type.find(
                                                                                                  ']')],
                                                               self.tr(self.plot_attr.hs_plot_type),
                                                               self.project_properties,
                                                               self.plot_attr.axe_mod_choosen),
                                                         name=self.plot_attr.hs_plot_type + " hydrosignature " + name_hdf5),
                                               progress_value=progress_value,
                                               q=q)
                        self.process_list.append(my_process)
            else:
                my_process = MyProcess(p=Process(target=plot_mod.plot_hydrosignature,
                                       args=(progress_value,
                                             None,
                                             hdf5.hs_input_class[1],
                                             hdf5.hs_input_class[0],
                                             "input classes of " + name_hdf5,
                                             None,
                                             self.project_properties,
                                             self.plot_attr.axe_mod_choosen),
                                                 name="input class"),
                                       progress_value=progress_value,
                                       q=q)
                self.process_list.append(my_process)

    # sc_plot
    def set_sc_plot_mode(self, path_prj, plot_attr, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__(self.process_type)
        else:
            self.add_plots(plot_attr.nb_plot)
        self.path_prj = path_prj
        self.plot_attr = plot_attr
        self.project_properties = project_properties

    def load_data_and_append_sc_plot_process(self):
        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()

        # read_pref
        information_model_dict = read_pref(self.plot_attr.xmlfile)

        # univariate
        if self.plot_attr.information_model_dict["model_type"] == "univariate suitability index curves":
            # specific stage of the same xml pref curve
            if self.plot_attr.selected_fish_stage:
                hydraulic_type_list = self.plot_attr.information_model_dict["hydraulic_type_available"][information_model_dict["stage_and_size"].index(self.plot_attr.selected_fish_stage)]
            # all stage of the same xml pref curve (get first because homogeneous model)
            else:
                hydraulic_type_list = self.plot_attr.information_model_dict["hydraulic_type_available"][0]
            if "HEM" in hydraulic_type_list:
                # HEM
                my_process = MyProcess(p=Process(target=plot_mod.plot_suitability_curve_hem,
                                                 args=(progress_value,
                                              information_model_dict,
                                              self.plot_attr.selected_fish_stage,
                                              self.project_properties,
                                              False),
                                                 name="plot_suitability_curve_invertebrate"),
                                       progress_value=progress_value,
                                       q=q)
            else:
                # classic univariate suitability_curve
                my_process = MyProcess(p=Process(target=plot_mod.plot_suitability_curve,
                                                 args=(progress_value,
                                              information_model_dict,
                                            self.plot_attr.selected_fish_stage,
                                              self.project_properties,
                                              False),
                                                 name="plot_suitability_curve"),
                                       progress_value=progress_value,
                                       q=q)

        else:
            # bivariate suitability_curve
            my_process = MyProcess(p=Process(target=plot_mod.plot_suitability_curve_bivariate,
                                    args=(progress_value,
                                          information_model_dict,
                                          None,
                                          self.project_properties,
                                          False),
                                    name="plot_suitability_curve_bivariate"),
                                       progress_value=progress_value,
                                       q=q)
        self.process_list.append(my_process)

    # sc_hs_plot
    def set_sc_hs_plot_mode(self, path_prj, plot_attr, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__(self.process_type)
        else:
            self.add_plots(plot_attr.nb_plot)
        self.path_prj = path_prj
        self.plot_attr = plot_attr
        self.project_properties = project_properties

    def load_data_and_append_sc_hs_plot_process(self):
        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()

        # get data
        data, vclass, hclass = get_hydrosignature(self.plot_attr.xmlfile)
        if isinstance(data, np.ndarray):
            my_process = MyProcess(Process(target=plot_mod.plot_hydrosignature,
                                           args=(progress_value,
                                                   data,
                                                   vclass,
                                                   hclass,
                                                   self.plot_attr.fishname,
                                                   "from suitability curve",
                                                   self.project_properties,
                                                   self.project_properties["hs_axe_mod"]),
                                           name="plot_suitability_curve"),
                               progress_value=progress_value,
                               q=q)

            self.process_list.append(my_process)

    # estimhab_plot
    def set_estimhab_plot_mode(self, path_prj, plot_attr, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__(self.process_type)
        else:
            self.add_plots(plot_attr.nb_plot)
        self.path_prj = path_prj
        self.plot_attr = plot_attr
        self.project_properties = project_properties

    def load_data_and_append_estimhab_plot_process(self):
        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()

        # load
        hdf5 = Hdf5Management(self.path_prj, self.plot_attr.name_hdf5, new=False)
        hdf5.load_hdf5_estimhab()

        # plot
        my_process = MyProcess(Process(target=plot_mod.plot_stat_data,
                                       args=(progress_value,
                                               hdf5.estimhab_dict,
                                             "Estimhab",
                                               self.project_properties),
                                       name="plot_suitability_curve"),
                           progress_value=progress_value,
                           q=q)

        self.process_list.append(my_process)

    # interpolation
    def set_interpolation_hdf5_mode(self, path_prj, names_hdf5, interp_attr, project_properties):
        # check_all_process_closed
        if self.check_all_process_closed():
            self.__init__("interpolation")
        else:
            self.add_plots(1)
        self.path_prj = path_prj
        self.name_hdf5 = names_hdf5
        self.interp_attr = interp_attr
        self.project_properties = project_properties

    def load_data_and_append_interpolation_plot_process(self):
        self.hdf5 = Hdf5Management(self.path_prj, self.name_hdf5, new=False, edit=False)

        # get hdf5 inforamtions
        self.hdf5.get_hdf5_attributes(close_file=True)

        # recompute
        data_to_table, horiz_headers, vertical_headers = compute_interpolation(self.hdf5.data_2d,
                                                                                     self.interp_attr.hvum.user_target_list,
                                                                                     self.hdf5.data_2d.reach_list.index(self.interp_attr.reach),
                                                                                     self.interp_attr.units,
                                                                                     self.interp_attr.unit_type,
                                                                                     rounddata=False)

        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()
        my_process = MyProcess(p=Process(target=plot_mod.plot_interpolate_chronicle,
                                         args=(progress_value,
                                                           data_to_table,
                                                           horiz_headers,
                                                           vertical_headers,
                                                           self.hdf5.data_2d,
                                                           self.interp_attr.hvum.user_target_list,
                                                           self.hdf5.data_2d.reach_list.index(self.interp_attr.reach),
                                                           self.interp_attr.unit_type,
                                                           self.project_properties),
                                         name=self.tr("interpolated figure")),
                               progress_value=progress_value,
                               q=q)

        # append to list
        self.process_list.append(my_process)

    def load_data_and_append_interpolation_export_process(self):
        self.hdf5 = Hdf5Management(self.path_prj, self.name_hdf5, new=False, edit=False)

        # get hdf5 inforamtions
        self.hdf5.get_hdf5_attributes(close_file=True)

        # recompute
        data_to_table, horiz_headers, vertical_headers = compute_interpolation(self.hdf5.data_2d,
                                                                                     self.interp_attr.hvum.user_target_list,
                                                                                     self.hdf5.data_2d.reach_list.index(self.interp_attr.reach),
                                                                                     self.interp_attr.units,
                                                                                     self.interp_attr.unit_type,
                                                                                     rounddata=False)

        # class MyProcess
        progress_value = Value("d", 0.0)
        q = Queue()
        my_process = MyProcess(p=Process(target=export_text_interpolatevalues,
                                         args=(progress_value,
                                               data_to_table,
                                               horiz_headers,
                                               vertical_headers,
                                               self.hdf5.data_2d,
                                               self.interp_attr.unit_type,
                                               self.project_properties),
                                         name=self.tr("interpolated export")),
                               progress_value=progress_value,
                               q=q)

        # append to list
        self.process_list.append(my_process)

    def add_plots(self, plus):
        self.plot_production_stopped = False
        # remove plots not started
        self.remove_process_not_started()

    def append(self, process):
        self.process_list.append(process)

    def run(self):  # start : enable debugger and disable progress_bar, run : disable debugger and enable progress_bar
        self.thread_started = True
        self.plot_production_stopped = False
        if self.process_type == "hyd":
            self.hyd_process()
        elif self.process_type == "sub":
            self.sub_process()
        elif self.process_type == "merge":
            self.merge_process()
        elif self.process_type == "hab":
            self.hab_process()
        elif self.process_type == "plot":
            self.load_data_and_append_plot_process()
        elif self.process_type == "sc_plot":
            self.load_data_and_append_sc_plot_process()
        elif self.process_type == "sc_hs_plot":
            self.load_data_and_append_sc_hs_plot_process()
        elif self.process_type == "estimhab_plot":
            self.load_data_and_append_estimhab_plot_process()
        elif self.process_type == "export":
            self.load_data_and_append_export_process()
        elif self.process_type == "hs":
            self.load_data_and_append_hs_process()
        elif self.process_type == "hrr":
            self.load_data_and_append_hrr_process()
        elif self.process_type == "mesh_manager":
            self.load_data_and_append_mesh_manager_process()
        elif self.process_type == "hs_plot":
            self.load_data_and_append_hs_plot_process()
        elif self.process_type == "interpolation":
            if self.interp_attr.mode == "plot":
                self.load_data_and_append_interpolation_plot_process()
            elif self.interp_attr.mode == "export":
                self.load_data_and_append_interpolation_export_process()

        self.add_send_log_to_each_process()

        # start
        if self.process_type in {"plot", "hs_plot"} or self.interp_attr.mode == "plot":
            self.process_list.start_all_process(parallel=True)
        else:
            self.process_list.start_all_process(parallel=False)  # risk of crash if all exports are enabled
        self.all_process_runned = True

    def add_send_log_to_each_process(self):
        if hasattr(self, "send_log"):
            for process in self.process_list:
                process.send_log = self.send_log

    def close_all_plot(self):
        # remove plots not started
        self.remove_process_not_started()
        for i in range(len(self.process_list)):
            self.process_list[i][0].terminate()
        self.process_list = MyProcessList()

    def close_all_export(self):
        """
        Close all plot process. usefull for button close all figure and for closeevent of Main_windows_1.
        """
        if self.thread_started:
            while not self.all_process_runned:
                #print("waiting", self.all_process_runned)
                pass

            for i in range(len(self.process_list)):
                if self.process_list[i][0].is_alive() or self.process_list[i][1].value == 1:
                    self.process_list[i][0].terminate()
            self.thread_started = False
            self.export_finished = True
            self.process_list = MyProcessList()

    def close_all_hs(self):
        """
        Close all plot process. usefull for button close all figure and for closeevent of Main_windows_1.
        """
        if self.thread_started:
            while not self.all_process_runned:
                pass

            for i in range(len(self.process_list)):
                if self.process_list[i].p.is_alive():
                    self.process_list[i].p.terminate()
            self.thread_started = False
            self.terminate()

    def check_all_process_closed(self):
        """
        Check if a process is alive (plot window open)
        """
        #print("check_all_process_closed")
        if any([self.process_list[i].p.is_alive() for i in range(len(self.process_list))]):  # plot window open or plot not finished
            return False
        else:
            return True

    def remove_process_not_started(self):
        #print("remove_process_not_started")
        for i in reversed(range(len(self.process_list))):
            if not self.process_list[i].p.is_alive():
                self.process_list.pop(i)

    def stop_by_user(self):
        self.process_list.stop_by_user = True
        if self.thread_started:
            # terminate
            for process in self.process_list:
                if process.p.is_alive():
                    # not started
                    if process.progress_value.value == 0.0:
                        process.state = self.tr("not started")
                        if self.process_type in {"plot", "hs_plot"}:
                            pass
                        else:
                            process.get_total_time()
                    # started ==> terminate
                    elif process.progress_value.value != 0.0:
                        process.p.terminate()
                        process.state = self.tr("stopped")
                        if self.process_type in {"plot", "hs_plot"}:
                            pass
                        else:
                            process.get_total_time()
                else:
                    # not started
                    if process.progress_value.value == 0.0:
                        process.state = self.tr("not started")
                        if self.process_type in {"plot", "hs_plot"}:
                            process.get_total_time()
                        else:
                            process.get_total_time()

            # get_total_time
            self.process_list.get_total_time()

            # child process
            kill_proc_tree(os.getpid())

            self.terminate()


class MyProcessList(list):
    """
    Represent list of process
    """
    def __init__(self):
        super().__init__()
        self.nb_total = len(self)
        self.nb_finished = 0
        self.stop_by_user = False
        self.progress_value = 0.0
        self.start_time = time.time()
        self.total_time = 0
        self.parallel = False

    def start_all_process(self, parallel):
        # init
        self.nb_total = len(self)
        self.nb_finished = 0
        self.stop_by_user = False
        self.progress_value = 0.0
        self.start_time = time.time()
        self.total_time = 0
        self.parallel = parallel

        # start
        for process in self:
            if not self.stop_by_user:
                if process.progress_value.value == 0.0:
                    process.start_process()
                    self.get_progress_value()
                    # to wait end of each process (block multiprocessing)
                    if not self.parallel:
                        # one by one
                        while process.p.is_alive():
                            # print("wait1")
                            if self.stop_by_user:
                                break
                            self.get_progress_value()
                        if process.progress_value.value != 100 and not self.stop_by_user:  # not finish but not alive with error or not
                            process.get_total_time()

        sleep(0.1)  # wait the last send_lod.emit because it's unorganized

        if self.parallel:
            while self.nb_finished != self.nb_total:
                # print("wait2")
                if self.stop_by_user:
                    break
                self.get_progress_value()

        # get_total_time
        self.get_total_time()

    def get_progress_value(self):
        progress_value_list = []
        for process in self:
            process_value = process.progress_value.value
            progress_value_list.append(process_value)

            # finish
            if process_value == 100.0 and not process.total_time_computed:
                process.state = "done"
                # total_time
                process.get_total_time()

        actual_nb_finished = progress_value_list.count(100.0)
        if actual_nb_finished > self.nb_finished:
            pass
        # save to attr
        self.nb_finished = actual_nb_finished
        self.progress_value = sum(progress_value_list) / len(self)  # 100 %

    def get_total_time(self):
        # thread
        self.total_time = time.time() - self.start_time


class MyProcess(QObject):
    """
    Represent one process
    """

    def __init__(self, p=Process(name="- None"), progress_value=Value("d", 0.0), q=Queue()):
        super().__init__()
        self.state = self.tr("started")
        self.p = p  # process
        self.progress_value = progress_value  # progress value in float (Value class)
        self.q = q  # string to get if warning or error
        self.init_start_time = time.time()  # start time in
        self.start_time = None
        self.total_time = 0  # total time in s
        self.total_time_computed = False
        self.send_log = None

    def start_process(self):
        self.start_time = time.time()  # start time in s
        try:
            try:
                self.p.start()
            except BrokenPipeError:
                print("BrokenPipeError", self.p.name)
        except MemoryError:
            print("MemoryError", self.p.name)
        # if self.send_log is not None:
        #     process_info = "- " + self.tr(self.p.name.replace("_", " ") + " started with " + str(psutil.Process(self.p.pid).memory_info()[0] / 1000000) + " Mo.")
        #     self.send_log.emit(process_info)

    def get_total_time(self):
        if self.start_time:
            self.total_time = time.time() - self.start_time  # total time in s
        else:
            # not started
            self.total_time = 0
        self.total_time_computed = True
        self.mystdout = None
        if self.send_log is not None:
            error = False
            if not self.q.empty():
                self.mystdout = self.q.get()
                error = self.send_err_log(True)
            if self.state == self.tr("stopped"):
                if not error:
                    if self.progress_value.value == 100:
                        # print("- " + self.p.name.replace("_", " ") + self.tr(" closed by user after ") + str(
                        #     round(self.total_time)) + " s")
                        pass
                    else:
                        self.send_log.emit("- " + self.p.name.replace("_", " ") + self.tr(" stopped (process time = ") + str(
                            round(self.total_time)) + " s).")
            elif self.state == self.tr("not started"):
                self.send_log.emit("- " + self.tr(self.p.name.replace("_", " ") + " " + self.tr("not started.")))
            else:
                if not error:
                    if self.progress_value.value == 100:
                        self.send_log.emit("- " + self.p.name.replace("_", " ") + self.tr(" done (process time = ") + str(
                            round(self.total_time)) + " s).")
                    else:
                        self.send_log.emit("- " + self.p.name.replace("_", " ") + self.tr(" crashed (process time = ") + str(
                            round(self.total_time)) + " s).")
                else:
                    self.send_log.emit(
                        "- " + self.p.name.replace("_", " ") + self.tr(" crashed (process time = ") + str(
                            round(self.total_time)) + " s).")
        else:
            # print("- " + self.p.name.replace("_", " ") + " " + self.state + self.tr(" (process time = ") + str(
            #                 round(self.total_time)) + " s).")
            pass

    def send_err_log(self, check_ok=False):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout before calling this function. It only sends the hundred first errors
        to avoid freezing the GUI. A similar function exists in estimhab_GUI.py. Correct both if necessary.

        :param check_ok: This is an optional paramter. If True, it checks if the function returns any error
        """
        error = False

        max_send = 400
        if self.mystdout is not None:
            str_found = self.mystdout.getvalue()
        else:
            return
        str_found = str_found.split('\n')
        for i in range(0, min(len(str_found), max_send)):
            # print(i, str_found[i])
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
            if i == max_send - 1:
                self.send_log.emit(self.tr('Warning: too many information for the GUI'))
            if 'Error' in str_found[i] and check_ok:
                error = True
        if check_ok:
            return error


def kill_proc_tree(pid, including_parent=False):
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):
        try:
            if "python" in child.name():
                child.kill()
        except psutil.NoSuchProcess:
            pass
    if including_parent:
        parent.kill()


def limit_cpu():
    "is called at every process start"
    p = psutil.Process(os.getpid())
    # set to lowest priority, this is windows only, on Unix use ps.nice(19)
    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)