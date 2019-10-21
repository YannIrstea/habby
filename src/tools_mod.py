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
import numpy as np
import urllib
from copy import deepcopy
import sys
from PyQt5.QtWidgets import QApplication, QGroupBox, QProgressBar, QLabel, QFrame
from PyQt5.QtCore import QTranslator, QCoreApplication, QObject, pyqtSignal, QEvent

from src.project_manag_mod import load_project_preferences


# INTERPOLATION TOOLS
def export_empty_text_from_hdf5(unit_type, unit_min, unit_max, filename, path_prj):
    # get unit type
    start = unit_type.find('[')
    end = unit_type.find(']')
    unit_type = unit_type[start + 1:end]

    # headers
    headers = "unit[" + unit_type + "]"

    # lines
    linetext1 = str(unit_min)
    linetext2 = str(unit_max)

    text = headers + "\n" + linetext1 + "\n" + linetext2

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_empty_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            f.write(text)
        return True
    except:
        return False


def read_chronicle_from_text_file(chronicle_filepath):
    # read discharge chronicle
    with open(chronicle_filepath, 'rt') as f:
        dataraw = f.read()
    # headers
    headers = dataraw.split("\n")[0].split("\t")
    date_index = None
    units_index = None
    for i in range(len(headers)):
        if 'DATE' in headers[i].upper():  # Date
            date_index = i
            date_type = headers[date_index][headers[date_index].find('[') + 1:headers[date_index].find(']')]
        if 'UNIT[' in headers[i].upper() and ']' in headers[i]:  # Q
            units_index = i
            unit_type = headers[units_index][headers[units_index].find('[') + 1:headers[units_index].find(']')]

    if units_index is None:
        return False, "Error : Interpolation not done. 'unit[' header not found in " + chronicle_filepath + "."

    # create dict
    if type(date_index) == int and type(units_index) == int:
        chronicle_from_file = dict(date=[], units=[])
        types_from_file = dict(date=date_type, units=unit_type)
    if type(date_index) == int and type(units_index) != int:
        chronicle_from_file = dict(date=[])
        types_from_file = dict(date=date_type)
    if type(date_index) != int and type(units_index) == int:
        chronicle_from_file = dict(units=[])
        types_from_file = dict(units=unit_type)

    data_row_list = dataraw.split("\n")[1:]
    for line in data_row_list:
        if line == "":
            #print("empty line")
            pass
        else:
            for index in range(2):
                # units presence (time or discharge)
                if index == units_index:
                    data = line.split("\t")[index]
                    if not data:
                        chronicle_from_file["units"].append(None)
                    if data:
                        chronicle_from_file["units"].append(float(data))
                # date presence
                if index == date_index:
                    chronicle_from_file["date"].append(line.split("\t")[index])
    chronicle_from_file["units"] = np.array(chronicle_from_file["units"])
    if type(date_index) == int:
        #chronicle_from_file["date"] = np.array([dt.strptime(date, date_type).date() for date in chronicle_from_file["date"]], dtype='datetime64')
        chronicle_from_file["date"] = np.array(chronicle_from_file["date"])
    return chronicle_from_file, types_from_file


def check_matching_units(data_description, types):
    # get units types
    unit_hdf5_type = data_description["hyd_unit_type"][
                     data_description["hyd_unit_type"].find('[') + 1:data_description["hyd_unit_type"].find(']')]
    for key in types.keys():
        if "units" in key:
            unit_chronicle_type = types[key]

    # check matching units type ok
    if unit_hdf5_type == unit_chronicle_type:
        #print("units type match")
        return True, ""
    if unit_hdf5_type != unit_chronicle_type:
        #print("units type doesn't match")
        return False, " Desired units type is different from available units type : " + unit_chronicle_type + " != " + unit_hdf5_type


def compute_interpolation(data_description, fish_names, reach_num, chronicle, types, rounddata=True):
    # check if date
    if "date" in types.keys():
        date_presence = True
    else:
        date_presence = False

    # get hdf5 model
    inter_data_model = dict()
    inter_data_model["unit"] = data_description["hyd_unit_list"][reach_num]
    wet_area = np.array(list(map(float, data_description["total_wet_area"][reach_num])))
    # map by fish
    for fish_index, fish_name in enumerate(fish_names):
        spu = np.array(list(map(float, data_description["total_WUA_area"][fish_name][reach_num])))
        inter_data_model["hv_" + fish_name] = spu / wet_area
        inter_data_model["spu_" + fish_name] = spu

    # copy chonicle to interpolated
    chronicle_interpolated = deepcopy(chronicle)
    # Add new column to chronicle_interpolated
    for fish_name in fish_names:
        chronicle_interpolated["hv_" + fish_name] = []
    for fish_name in fish_names:
        chronicle_interpolated["spu_" + fish_name] = []
    # copy for round for table gui
    chronicle_gui = deepcopy(chronicle_interpolated)
    # get min max
    q_min = min(inter_data_model["unit"])
    q_max = max(inter_data_model["unit"])

    # interpolation
    for fish_name in fish_names:
        for index_to_est, q_value_to_est in enumerate(chronicle_interpolated["units"]):
            if q_value_to_est != None:
                if q_value_to_est < q_min or q_value_to_est > q_max:
                    chronicle_interpolated["hv_" + fish_name].append(None)
                    chronicle_gui["hv_" + fish_name].append("")
                    chronicle_interpolated["spu_" + fish_name].append(None)
                    chronicle_gui["spu_" + fish_name].append("")
                else:
                    data_interp_hv = np.interp(q_value_to_est,
                                               inter_data_model["unit"],
                                               inter_data_model["hv_" + fish_name])
                    chronicle_interpolated["hv_" + fish_name].append(data_interp_hv)
                    chronicle_gui["hv_" + fish_name].append("{0:.2f}".format(data_interp_hv))
                    data_interp_spu = np.interp(q_value_to_est,
                                                inter_data_model["unit"],
                                                inter_data_model["spu_" + fish_name])
                    chronicle_interpolated["spu_" + fish_name].append(data_interp_spu)
                    chronicle_gui["spu_" + fish_name].append("{0:.0f}".format(data_interp_spu))
            if q_value_to_est == None:
                chronicle_interpolated["hv_" + fish_name].append(None)
                chronicle_gui["hv_" + fish_name].append("")
                chronicle_interpolated["spu_" + fish_name].append(None)
                chronicle_gui["spu_" + fish_name].append("")

    # round for GUI
    if rounddata:
        if not date_presence:
            horiz_headers = list(chronicle_gui.keys())[1:]
            vertical_headers = list(map(str, chronicle_gui["units"]))
            del chronicle_gui["units"]
            data_to_table = list(zip(*chronicle_gui.values()))
        if date_presence:
            horiz_headers = list(chronicle_gui.keys())[1:]
            vertical_headers = list(map(str, chronicle_gui["date"]))
            del chronicle_gui["date"]
            chronicle_gui["units"] = list(map(str, chronicle_gui["units"]))
            data_to_table = list(zip(*chronicle_gui.values()))
    # not round to export text and plot
    if not rounddata:
        if not date_presence:
            horiz_headers = list(chronicle_interpolated.keys())[1:]
            vertical_headers = list(map(str, chronicle_interpolated["units"]))
            data_to_table = chronicle_interpolated
        if date_presence:
            horiz_headers = list(chronicle_interpolated.keys())[1:]
            vertical_headers = list(map(str, chronicle_interpolated["date"]))
            del chronicle_interpolated["date"]
            chronicle_interpolated["units"] = list(map(str, chronicle_interpolated["units"]))
            data_to_table = chronicle_interpolated
    return data_to_table, horiz_headers, vertical_headers


def export_text_interpolatevalues(data_to_table, horiz_headers, vertical_headers, data_description, types, project_preferences):
    filename = data_description["hab_filename"]
    path_prj = data_description["path_project"]
    unit_type = types["units"]

    fish_names = list(horiz_headers)

    # prep data
    for fish_num, fish_name in enumerate(fish_names):
        if "hv_" in fish_name:
            fish_names[fish_num] = fish_name.replace("hv_", "")
        if "spu_" in fish_name:
            fish_names[fish_num] = fish_name.replace("spu_", "")

    # header 1
    if project_preferences['language'] == 0:
        if len(types.keys()) > 1:  # date
            date_type = types["date"]
            header = 'reach\tdate\tunit'
        else:
            header = 'reach\tunit'
    else:
        if len(types.keys()) > 1:  # date
            date_type = types["date"]
            header = 'troncon\tdate\tunit'
        else:
            header = 'troncon\tunit'
    if project_preferences['language'] == 0:
        header += "".join(['\tHV' + str(i) for i in range(int(len(fish_names) / 2))])
        header += "".join(['\tWUA' + str(i) for i in range(int(len(fish_names) / 2))])
    else:
        header += "".join(['\tVH' + str(i) for i in range(int(len(fish_names) / 2))])
        header += "".join(['\tSPU' + str(i) for i in range(int(len(fish_names) / 2))])
    header += '\n'
    # header 2
    if len(types.keys()) > 1:  # date
        header += '[]\t[' + date_type + ']\t[' + unit_type + ']'
    else:
        header += '[]\t[' + unit_type + ']'
    header += "".join(['\t[]' for _ in range(int(len(fish_names) / 2))])
    header += "".join(['\t[m2]' for _ in range(int(len(fish_names) / 2))])
    header += '\n'
    # header 3
    if len(types.keys()) > 1:  # date
        header += 'all\tall\tall'
    else:
        header += 'all\tall'
    for fish_name in fish_names:
        if "units" in fish_name:
            pass
        else:
            header += '\t' + fish_name.replace(' ', '_')
    # lines
    linetext = ""
    # for each line
    for row_index in range(len(vertical_headers)):
        # print("line", line)
        if len(types.keys()) > 1:  # date
            linetext += "0" + "\t" + str(vertical_headers[row_index]) + "\t"
        else:
            linetext += "0" + "\t" + str(vertical_headers[row_index]) + "\t"
        # for each column
        for column_name in horiz_headers:
            data_hv = data_to_table[column_name][row_index]
            if not data_hv:
                linetext += "None" + "\t"
            if data_hv:
                linetext += str(data_hv) + "\t"
        # new line
        linetext += "\n"
    text = header + "\n" + linetext

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_interpolate_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            f.write(text)
            return True
    except:
        return False


# OTHERS TOOLS
def get_prj_from_epsg_web(epsg_code):
    wkt = urllib.request.urlopen("http://spatialreference.org/ref/epsg/{0}/prettywkt/".format(epsg_code))
    data_byte = wkt.read()
    data_str = data_byte.decode("utf-8")
    remove_spaces = data_str.replace(" ", "")
    output = remove_spaces.replace("\n", "")
    return output


def remove_image(name, path, format1):
    """
    This is a small function used to erase images if erase_id is True. We have a function because different format
    czan be used and because it is done often in the functions above.

    :param name: the name of the file t be erase (without the extension)
    :param path: the path to the file
    :param format1: the type of format
    :return:
    """
    if format1 == 0:
        ext = ['.png', '.pdf']
    elif format1 == 1:
        ext = ['.png']
    elif format1 == 2:
        ext = ['jpg']
    elif format1 == 3:
        ext = ['.pdf']
    else:
        return True
    for e in ext:
        if os.path.isfile(os.path.join(path, name + e)):
            try:
                os.remove(os.path.join(path, name + e))
            except PermissionError:
                print('Warning: Figures used by an other program. could not be erased \n')
                return False
    return True


def isstranumber(a):
    try:
        float(a)
        bool_a = True
    except:
        bool_a = False
    return bool_a


def sort_homogoeneous_dict_list_by_on_key(dict_to_sort, key):
    indice_sorted = [dict_to_sort[key].index(x) for x in sorted(dict_to_sort[key])]
    if list(set(indice_sorted)) == [0]:
        indice_sorted = list(range(len(indice_sorted)))

    for key in dict_to_sort.keys():
        key_list = []
        for ind_num, ind_ind in enumerate(indice_sorted):
            key_list.append(dict_to_sort[key][ind_ind])
        dict_to_sort[key] = key_list
    return dict_to_sort


def get_translator(path_prj, name_prj):
    """
    :param language: 0:EN, 1:FR, 2:ES
    :return: application with translate method.
    """
    # get language from project_preferences['language']
    project_preferences = load_project_preferences(path_prj, name_prj)
    language = project_preferences['language']

    # translator
    app = QApplication(sys.argv)
    languageTranslator = QTranslator(app)
    if language == 0:
        input_file_translation = 'Zen_EN'
        languageTranslator.load(input_file_translation, os.path.join(os.getcwd(), 'translation'))
    if language == 1:
        input_file_translation = 'Zen_FR'
        languageTranslator.load(input_file_translation, os.path.join(os.getcwd(), 'translation'))
    elif language == 2:
        input_file_translation = 'Zen_ES'
        languageTranslator.load(input_file_translation, os.path.join(os.getcwd(), 'translation'))
    app.installTranslator(languageTranslator)
    return app


def txt_file_convert_dot_to_comma(filename_full_path):
    # read and convert
    with open(filename_full_path, 'r') as file:
        text_data_with_comma = file.read().replace('.', ',')
    # write converted
    with open(filename_full_path, 'w') as file:
        file.write(text_data_with_comma)


# GUI
class QGroupBoxCollapsible(QGroupBox):
    def __init__(self):
        super().__init__()
        # group title
        self.setCheckable(True)
        self.setStyleSheet('QGroupBox::indicator {width: 20px; height: 20px;}'
            'QGroupBox::indicator:unchecked {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:hover {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:pressed {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:checked {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:checked:hover {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:checked:pressed {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:indeterminate:hover {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:indeterminate:pressed {image: url(translation//icon//triangle_black_open_50_50.png);}'
        )
        #'QGroupBox::indicator:checked:hover {image: url(translation//triangle_black_closed.png);}'
        self.toggled.connect(self.toggle_group)
        self.setChecked(True)

    def toggle_group(self, checked):
        if checked:
            self.setFixedHeight(self.sizeHint().height())
        else:
            self.setFixedHeight(30)


class MyProcessList(list):
    """
    This class is a subclass of class list created in order to analyze the status of the processes and the refresh of the progress bar in real time.

    :param nb_plot_total: integer value representing the total number of graphs to be produced.
    :param progress_bar: Qprogressbar of DataExplorerFrame to be refreshed
    """

    def __init__(self, type):
        super().__init__()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_label = QLabel()
        self.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))
        self.nb_plot_total = 0
        self.export_production_stoped = False
        self.process_type = type  # cal or plot or export

    def new_plots(self, nb_plot_total):
        self.add_plots_state = False
        self.nb_plot_total = nb_plot_total
        self.save_process = []
        self[:] = []

    def add_plots(self, nb_plot_total):
        self.add_plots_state = True
        self.nb_plot_total = nb_plot_total
        self.save_process = self[:]
        self[:] = []

    def append(self, *args):
        """
        Overriding of append method in order to analyse state of plot processes and refresh progress bar.
        Each time the list is appended, state is analysed and progress bar refreshed.

        :param args: tuple(process, state of process)
        """
        args[0][0].start()
        self.extend(args)

        self.check_all_process_produced()

    def check_all_process_produced(self):
        """
        State is analysed and progress bar refreshed.
        """
        nb_finished = 0
        state_list = []
        for i in range(len(self)):
            state = self[i][1].value
            state_list.append(state)
            if state == 1:
                nb_finished = nb_finished + 1
            if state == 0:
                if i == self.nb_plot_total - 1:  # last of all plot
                    while 0 in state_list:
                        if self.export_production_stoped:
                            break
                        for j in [k for k, l in enumerate(state_list) if l == 0]:
                            state = self[j][1].value
                            state_list[j] = state
                            if state == 1:
                                nb_finished = nb_finished + 1
                                self.progress_bar.setValue(nb_finished)
                                self.progress_label.setText("{0:.0f}/{1:.0f}".format(nb_finished, self.nb_plot_total))
                                QCoreApplication.processEvents()

        self.progress_bar.setValue(nb_finished)
        self.progress_label.setText("{0:.0f}/{1:.0f}".format(nb_finished, self.nb_plot_total))
        QCoreApplication.processEvents()

    def check_all_process_closed(self):
        """
        Check if a process is alive (plot window open)
        """
        if any([self[i][0].is_alive() for i in range(len(self))]):  # plot window open or plot not finished
            return False
        else:
            return True

    def kill_all_process(self):
        """
        Close all plot process. usefull for button close all figure and for closeevent of Main_windows_1.
        """
        for i in range(len(self)):
            self[i][0].terminate()
            #print(self[i][0].name, "terminate(), state : ", self[i][1].value)


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class DoubleClicOutputGroup(QObject):
    double_clic_signal = pyqtSignal()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick:
            self.double_clic_signal.emit()
            return True  # eat double click
        else:
            # standard event processing
            return QObject.eventFilter(self, obj, event)
