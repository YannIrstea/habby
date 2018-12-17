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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout,  QLineEdit, \
    QComboBox, QListWidget, QSpacerItem, QFileDialog, QFrame
import numpy as np
from src import hydraulic_chronic
from src import load_hdf5
from src_GUI import estimhab_GUI
from src_GUI import output_fig_GUI
import os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from io import StringIO


class ChroniqueGui(estimhab_GUI.StatModUseful):
    """
    This class contains the tab with the hydrological chronique.
    It takes a list of merge files as input and
    the user gives the output discharge. With these data,
    it create height and velcoity for the outpus dicharge
    based on interpoliation.

    It inherites from StatModUseful. StatModuseful is a QWidget,
    with some practical signal (send_log and show_fig)
    and some functions to find path_im and path_bio
    (the path wher to save image) and to manage lists.
    """

    drop_merge = pyqtSignal()
    """
    PyQtsignal to update the merge file in the Habitat Calc Tab
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.init_iu()

    def init_iu(self):

        # merge file
        l0 = QLabel(self.tr('<b> Substrate and hydraulic data </b>'))
        self.merge_all = QComboBox()  # fill in Main_Windows_1.py
        self.add_merge = QPushButton(self.tr("Select file"))
        self.add_merge.clicked.connect(self.add_file)
        self.add_allmerge = QPushButton(self.tr("Select all file"))
        self.add_allmerge.clicked.connect(self.add_all_file)

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # selected merge file
        l1 = QLabel(self.tr("<b> Chosen data </b>"))
        self.chosen_all = QListWidget()
        # to debug if you want to sort filename with mouse interactions
        # self.chosen_all.setDragDropMode(QAbstractItemView.InternalMove)
        self.show_file_selected()
        self.remove_all = QPushButton(self.tr("Remove all file"))
        self.remove_all.clicked.connect(self.remove_all_file)
        self.remove_one = QPushButton(self.tr("Remove one file"))
        self.remove_one.clicked.connect(self.remove_one_file)
        self.export_name = QPushButton(self.tr('Export file names'))
        self.export_name.clicked.connect(self.export_all_name)

        # discharge input
        l2 = QLabel(self.tr("<b> Discharge input </b>[m3/sec]"))
        self.input = QLineEdit("q1,q2,...")
        self.filein = QPushButton(self.tr("From file (.txt)"))
        self.filein.clicked.connect(lambda: self.load_file(self.input))
        self.mergein = QPushButton(self.tr("From chosen data"))
        self.mergein.clicked.connect(self.discharge_from_chosen_data)
        # discharge output
        l3 = QLabel(self.tr("<b> Discharge output </b>[m3/sec]"))
        self.output = QLineEdit("q1,q2,...")
        self.fileout = QPushButton(self.tr("From file (.txt)"))
        self.fileout.clicked.connect(lambda: self.load_file_output_discharge(self.output))
        # update Qlabel for discharge
        root, docxml, xmlfile = self.open_xml()
        if isinstance(root, int):  # no project found
            disin = None
            disout = None
        else:
            disin = root.find('.//Chronicle/DischargeInput')
            disout = root.find('.//Chronicle/DischargeOutput')
        if disin is not None:
            if disin.text is not None:
                self.input.setText(disin.text)
        if disout is not None:
            if disout.text is not None:
                self.output.setText(disout.text)

        # run
        self.run_chronicle = QPushButton(self.tr("Run Chronicles"))
        self.run_chronicle.setStyleSheet(
            "background-color: #47B5E6; color: black")
        self.run_chronicle.clicked.connect(self.run_chronicle_func)
        spacer = QSpacerItem(1, 100)

        # empty frame scrolable
        content_widget = QFrame()

        # layout
        self.layout4 = QGridLayout(content_widget)
        self.layout4.addWidget(l0, 0, 0)
        self.layout4.addWidget(self.merge_all, 0, 1)
        self.layout4.addWidget(self.add_merge, 0, 2)
        self.layout4.addWidget(self.add_allmerge, 0, 3)
        self.layout4.addWidget(l1, 1, 0)
        self.layout4.addWidget(self.chosen_all, 1, 1, 2, 1)
        self.layout4.addWidget(self.remove_all, 1, 2)
        self.layout4.addWidget(self.remove_one, 2, 2)
        self.layout4.addWidget(self.export_name, 2, 3)

        self.layout4.addWidget(l2, 3, 0)
        self.layout4.addWidget(self.input, 3, 1)
        self.layout4.addWidget(self.filein, 3, 2)
        self.layout4.addWidget(self.mergein, 3, 3)

        self.layout4.addWidget(l3, 5, 0)
        self.layout4.addWidget(self.output, 5, 1)
        self.layout4.addWidget(self.fileout, 5, 2)

        self.layout4.addWidget(self.run_chronicle, 7, 1)
        self.layout4.addItem(spacer, 8, 1)

        #self.setLayout(self.layout4)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content_widget)

    def open_xml(self):
        """
        This function open the xml project file, hwich is useful for
         the function below
        """
        xmlfile = os.path.join(self.path_prj, self.name_prj + '.xml')
        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                self.send_log.emit(
                   "Warning: the xml project file does not exist \n")
                return -99, -99, -99
        except ET.ParseError:
            self.send_log.emit(
                   "Warning: the xml project file is not well-formed.\n")
            return -99, -99, -99

        return root, docxml, xmlfile

    def show_file_selected(self):
        """
        This function open the xml project files and see
        if there were some selected merge file before. If yes,
        it update the QLabel on chosen data.
        """
        self.chosen_all.clear()

        # get data
        root, docxml, xmlfile = self.open_xml()
        if isinstance(root, int):
            return
        files = root.find('.//Chronicle/SelectedMerge')

        # add data to QListWidget
        if files is not None:
            if files.text is not None:
                files = files.text.split(',')
                for f in files:
                    self.chosen_all.addItem(f)
            else:
                self.chosen_all.addItem(self.tr("No file chosen"))
        else:
            self.chosen_all.addItem(self.tr("No file chosen"))

    def add_file(self):
        """
        This function adds one file to the selected merge file
        """

        root, docxml, xmlfile = self.open_xml()
        if isinstance(root, int):
            return

        mergeatt = root.find('.//Chronicle/SelectedMerge')
        if mergeatt is None:
            chronicleatt = root.find('.//Chronicle')
            if chronicleatt is None:
                chronicleatt = ET.SubElement(root, "Chronicle")
            mergeatt = ET.SubElement(chronicleatt, "SelectedMerge")
            mergeatt.text = self.merge_all.currentText()
        elif mergeatt.text is None:
            mergeatt.text = self.merge_all.currentText()
        else:
            mergeatt.text += ',' + self.merge_all.currentText()
        docxml.write(xmlfile)

        self.show_file_selected()

    def add_all_file(self):
        """
        This function is used to all all available merge hdf5 file
         to the chosen file
        """

        root, docxml, xmlfile = self.open_xml()
        if isinstance(root, int):
            return

        mergeatt = root.find('.//Chronicle/SelectedMerge')
        if mergeatt is None:
            chronicleatt = root.find('.//Chronicle')
            if chronicleatt is None:
                chronicleatt = ET.SubElement(root, "Chronicle")
            mergeatt = ET.SubElement(chronicleatt, "SelectedMerge")
        mergeatt.text = ''
        for i in range(0, self.merge_all.count()):
            self.merge_all.setCurrentIndex(i)
            mergeatt.text += self.merge_all.currentText() + ','
        mergeatt.text = mergeatt.text[:-1]
        docxml.write(xmlfile)

        self.show_file_selected()

    def remove_all_file(self):
        """
        This function remove all selected merge file
        """
        self.chosen_all.clear()
        self.chosen_all.addItem(self.tr("No file chosen"))

        root, docxml, xmlfile = self.open_xml()
        if isinstance(root, int):
            return
        files = root.find('.//Chronicle/SelectedMerge')
        if files is not None:
            files.text = ''
            docxml.write(xmlfile)

    def remove_one_file(self):
        """
        This function remove one selected merge file
        """
        if self.chosen_all.count() > 0 and \
           self.chosen_all.currentItem() is not None:
            ind = self.chosen_all.currentRow()
            self.chosen_all.takeItem(ind)

            root, docxml, xmlfile = self.open_xml()
            if isinstance(root, int):
                return
            files = root.find('.//Chronicle/SelectedMerge')
            if files is not None:
                if files.text is not None:
                    filetext = files.text.split(',')
                    new_text = ''
                    for idx, f in enumerate(filetext):
                        if idx != ind:
                            new_text += "," + f
                    new_text = new_text[1:]  # get rid of the first comma
                    files.text = new_text
                    docxml.write(xmlfile)

    def export_all_name(self):
        """
        This function creates a text file with the chosen hdf5 filename.
        This is useful to create a file to read the
        discharge. If there is more than one discharger/time step in the hdf5,
        the filename is repeated as many times as
        the number of discharge. Thie text file is written in text output
        """

        # get all file name for from file
        namefile = []
        for x in range(self.chosen_all.count()):
            # this is bad coding ;-) correct this!
            if x == 0 and \
               (self.chosen_all.item(x).text() == 'No file chosen'
                or self.chosen_all.item(x).text()
                    == 'Pas de fichier choisi'):
                self.send_log.emit('Warning: No file chosen.')
                return
            else:
                namefile.append(self.chosen_all.item(x).text())

        # get the number of time step
        path_hdf5 = self.find_path_hdf5_est()
        nb_t_all = []
        for n in namefile:
            nb_t = load_hdf5.get_unit_number(n, path_hdf5)
            if nb_t != -99:
                nb_t_all.append(nb_t)
            else:
                nb_t_all.append(0)

        # create the string which will be written to the file
        text = '# Filename\tQ[m3/s]\n'
        for id, n in enumerate(namefile):
            for t in range(0, nb_t_all[id]):
                text += n + '\t\n'

        # save the file
        path_txt = self.find_path_text_est()
        filename_txt = os.path.join(path_txt, 'filenames_chronicle.txt')
        if os.path.isfile(filename_txt):
            os.remove(filename_txt)
        with open(filename_txt, 'wt') as f:
            f.write(text)

        self.send_log.emit('A text file with the filenames was created.\
         It is saved in the text_output folder. \n')

    def load_file(self, linetext):
        """
        This functions lets the user choose a text file and use
         it to get the discharge intput.
        The format of the text file is one discharge value by line.
         Each line is in the format "hdf5 file name" and
        discharge value. It is possible to add an header by starting
         the line with the sign #. The discharges given
        are in m3/sec.

        It is important that the order of the discharge are the name than
         in the file. We check that here. It
        cannot be checked afterwards as the number in
         the QLineEdit might change before execution.

        :param linetext: This is the QLineEdit where the discharge
        have to be shown.
        """

        filename_path = QFileDialog.getOpenFileName(
            self, 'QFileDialog.getOpenFileName()', self.path_prj)[0]

        try:
            with open(filename_path, 'rt') as f:
                data_dis = f.read()
        except IOError or UnicodeDecodeError:
            self.send_log.emit(
             "Error: the discharge file could not be loaded.\n")
            return
        data_dis = data_dis.strip()

        # ignore header
        data_dis = data_dis.split('\n')
        if len(data_dis) == 0:
            self.send_log.emit('Warning: No data found in file')
            return

        # get dicharge data in string
        dis_all = ''  # string for the xml file
        name_all = []
        for d in data_dis:
            if not d[0] == '#':  # ignore header
                d2 = d.split()
                if len(d2) > 1:
                    # check for float
                    try:
                        float(d2[1])
                    except:
                        self.end_log.emit('Could not read discharge\
                         from file as it should be a float')
                        return
                    # get discharge and name
                    dis_all += d2[1] + ','
                    name_all.append(d2[0])
        dis_all = dis_all[:-1]  # one comma too much

        # Check order of file. Send warning if not ok
        nameqlist = []
        for x in range(self.chosen_all.count()):
            if x == 0 and self.chosen_all.item(x).text() == 'No file chosen':
                pass
            else:
                nameqlist.append(self.chosen_all.item(x).text())
        for idx, n in enumerate(nameqlist):
            if n != name_all[idx]:
                self.send_log.emit('Warning: The order of the file on the GUI\
                 is not coherent with the names '
                                   'contained in the loaded files. Order\
                                    is important here.')

        # save into the xml project file
        self.save_discharge()
        # add text to QLineEdit
        linetext.setText(dis_all)

    def load_file_output_discharge(self, linetext):
        """
        This functions lets the user choose a text file and use
         it to get the discharge output.
        The format of the text file is :
            first line start with '#' == headers
            no white space in individual headers
            all other lines with '#' are ignored
            headers without space ' '
            discharge column define with 'Q[' and ']'
            if date : date column define with "date" upper or lower case
            column separator : '\t' or '   ' or '  ' or ' '
            row separator : '\n'
            decimal separator : '.' or ','
        :param linetext: This is the QLineEdit where the discharge
        have to be shown.
        """

        filename_path = QFileDialog.getOpenFileName(
            self, 'QFileDialog.getOpenFileName()', self.path_prj)[0]

        try:
            with open(filename_path, 'rt') as f:
                data_dis = f.read()
        except IOError or UnicodeDecodeError:
            self.send_log.emit(
             "Error: the discharge file could not be loaded.\n")
            return
        if len(data_dis) == 0:
            self.send_log.emit('Error: No data found in file')
            return

        # clean
        data_dis = data_dis.strip()  # remove the last "\n"
        data_dis = data_dis.split('\n')  # row sep by \n to list
        data_dis[0] = data_dis[0].strip("#")
        data_dis[0] = data_dis[0].strip(" ")

        # remove comment lines (row start with #)
        comment_lines = []
        for i in range(1, len(data_dis)):
            if data_dis[i][0] == '#':
                comment_lines.append(i)
        data_dis = [j for i, j in enumerate(data_dis) if i not in comment_lines]

        # check column separator
        c_separator = None
        if all([';' in i for i in data_dis]): # check if ';' is in all element
            c_separator = ';'

        # headers index
        date_index = None
        q_index = None
        headers = data_dis[0].upper().split(c_separator)  # split take tabulation or 1, 2 or 3 white spaces or mixing
        for i in range(len(headers)):
            if 'DATE' in headers[i]:  # Date
                date_index = i
            if 'Q[' in headers[i] and ']' in headers[i]:  # Q
                q_index = i
        if q_index is None:
            self.send_log.emit('Error: No discharge header (Q[...]) found in file')
            return

        # get data
        date = []
        q_output = []
        for i in range(1, len(data_dis)):
            if date_index is not None and len(data_dis[i].split(c_separator)) == 1:
                self.send_log.emit('Error: Column separators are not homogeneous for all lines\
                                    (different at line ' + str(i + 1) + ')')
                return
            if date_index is not None:
                date.append(data_dis[i].split(c_separator)[date_index])
            if q_index is not None:
                q_output.append(data_dis[i].split(c_separator)[q_index])

        # convert decimal separator , by .
        for i in range(len(q_output)):
            if ',' in q_output[i]:
                q_output[i] = q_output[i].replace(',', '.')
            try:
                float(q_output[i])
            except ValueError or TypeError:
                self.send_log.emit('Error: Could not read discharge\
                 from file as it should be a float')
                return

        # get discharge data in string
        dis_all = ''  # string for the xml file
        date_all = ''
        for i in range(len(q_output)):
            # get discharge and name
            dis_all += q_output[i] + ','
            if date_index is not None:
                date_all += date[i] + ','
        dis_all = dis_all[:-1]  # one comma too much
        date_all = date_all[:-1]  # one comma too much

        # save
        linetext.setText(dis_all)  # add text to QLineEdit
        self.save_discharge()  # save into the xml project file
        self.send_log.emit('The discharge output file has been correctly read')  # log valid file

    def discharge_from_chosen_data(self):
        """
        This function open the chosen merge files and find
         the simulation name. It assume that the
        name of the simulation are the discharge data (simulation name
         can be time step or discharge). It then
        add these discharge to the QLineEdit so the user can check it.
        """

        path_hdf5 = self.find_path_hdf5_est()

        discharge = ''
        for i in range(0, self.chosen_all.count()):
            self.chosen_all.setCurrentRow(i)
            namefile = self.chosen_all.currentItem().text()
            pathnamefile = os.path.join(path_hdf5, namefile)
            if not os.path.isfile(pathnamefile):
                self.send_log.emit('Warning: A merge file was not found in\
                the hdf5 folder. \n')
            else:
                timestep = load_hdf5.load_unit_name(namefile, path_hdf5)
                for t in timestep:
                    discharge += t + ','
        discharge = discharge[:-1]
        self.save_discharge()
        self.input.setText(discharge)

    def get_discharge(self, linetext):
        """
        This function takes the data in the QlineEdit and transform it to
         a list of float. There are three possibilities:
        a) The discharge are given one by one separated by a comma
        b) We give the start, end and steps of discharge
        separated by a colon and habby create a list of discharge.
         1:5:1 -> 1,2,3,4 c) We give the start, end and number
        of points and habby creates a list of value spaced evenly on
         a LOGARTHMIC scale. LOG 1:5:10 ->
        Careful, the last number is here the  number of point created,
         not the step as the steps increases
        because of the logarythmic scale.
        """
        dstr0 = linetext.text()
        dstr = dstr0.split(',')
        discharge = []
        if len(dstr) < 2:  # we do not find many comma

            # logarthmic format
            if dstr0[:3].lower() == 'log':
                dstr0 = dstr0[3:]
                if ':' in dstr0:
                    dstr = dstr0.split(':')
                    if len(dstr) == 2:  # start:end
                        try:
                            startd = int(dstr[0])
                            endd = int(dstr[1])
                        except ValueError:
                            self.send_log.emit(
                                'Error: Discharge format was not understood.\
                                 Discharges should be separated '
                                'by a comma or in the format start:end:step\
                                 or LOG start:end:number points '
                                '(1). \n')
                            return [-99]
                        discharge = np.logspace(np.log10(startd),
                                                np.log10(endd))
                        #  50 points by default
                    elif len(dstr) == 3:  # start:end:step
                        try:
                            startd = int(dstr[0])
                            endd = int(dstr[1])
                            nbpoint = int(dstr[2])
                        except ValueError:
                            self.send_log.emit(
                                'Error: Discharge format was not understood.\
                                 Discharges should be separated '
                                'by a comma or in the format start:end:step\
                                 or LOG start:end:number points (5). \n')
                            return [-99]
                        discharge = np.logspace(np.log10(startd),
                                                np.log10(endd), num=nbpoint)

                else:
                    self.send_log.emit('Error: Discharge format was not\
                     understood. Discharges should be separated '
                                       'by a comma or in the format\
                                        start:end:step or '
                                       'LOG start:end:number points (4). \n')
                    return

            # start:end: step format
            elif ':' in dstr0:  # range of discharge
                dstr = dstr0.split(':')
                if len(dstr) == 2:  # start:end
                    try:
                        startd = int(dstr[0])
                        endd = int(dstr[1])
                    except ValueError:
                        self.send_log.emit('Error: Discharge format was not\
                         understood. Discharges should be separated '
                                           'by a comma or in the format\
                                            start:end:step or\
                                             LOG start:end:number points '
                                           '(1). \n')
                        return [-99]
                    discharge = range(startd, endd)
                elif len(dstr) == 3:  # start:end:step
                    try:
                        startd = int(dstr[0])
                        endd = int(dstr[1])
                        step = int(dstr[2])
                    except ValueError:
                        self.send_log.emit(
                            'Error: Discharge format was not understood.\
                             Discharges should be separated '
                            'by a comma or in the format start:end:step or\
                             LOG start:end:number points (5). \n')
                        return [-99]
                    discharge = range(startd, endd + step, step)
                else:
                    self.send_log.emit(
                        'Error: Discharge format was not understood.\
                         Discharges should be separated '
                        'by a comma or in the format start:end:step or\
                         LOG start:end:number points (2). \n')
                    return [-99]

            # just one discharge ? Or an error
            else:
                try:
                    discharge = [float(dstr[0])]
                except ValueError:
                    self.send_log.emit(
                        'Error: Discharge format was not understood.\
                     Discharges should be separated '
                        'by a comma or in the format\
                    start:end:step or LOG start:end:number points '
                        ' (3). \n')
                    return [-99]

        # list of discharge format
        else:
            try:
                discharge = list(map(float, dstr))
            except ValueError:
                self.send_log.emit('Error: \
                Discharge format was not understood.\
                 Discharges should be separated '
                                   'by a comma or in the format start:end:step\
                                    or LOG start:end:number points (4). \n')
                return [-99]

        return discharge

    def save_discharge(self):
        """
        This functions save the discharge data into the xml project file.\
         It saves the input and output discharge.
        """
        root, docxml, xmlfile = self.open_xml()
        if isinstance(root, int):
            return
        chro = root.find('.//Chronicle')
        if chro is None:
            self.send_log('Error: Could not saved the discharge data\
             into the xml project file. '
                          'Are merge files selected? \n')
            return
        disin = root.find('.//Chronicle/DischargeInput')
        disout = root.find('.//Chronicle/DischargeOutput')
        if disin is None:
            disin = ET.SubElement(chro, "DischargeInput")
        if disout is None:
            disout = ET.SubElement(chro, "DischargeOutput")
        if self.input.text() != "q1,q2,...":
            disin.text = self.input.text()
        if self.output.text() != "q1,q2,...":
            disout.text = self.output.text()
        docxml.write(xmlfile)

    def run_chronicle_func(self):
        """
        This function make the link between the GUI and the functions
        in hydraulic_chronic.py. It calls the chronic_hydro functions.
        """

        self.send_log.emit("Calculating hydrological chronicle....")

        # add discharge input to a list
        discharge_input = self.get_discharge(self.input)
        if len(discharge_input) < 2:
            self.send_log.emit('Error: Need at least two discharge input\
                                separated by a comma\n')
            return
        # add discharge output to a list
        discharge_output = self.get_discharge(self.output)
        # check discharge
        if len(discharge_input) == 0 or len(discharge_output) == 0:
            self.send_log.emit('Error: No discharge found')
            return
        if discharge_input[0] == -99 or discharge_output[0] == -99:
            return

        # get the merges file
        merge_files = []
        for i in range(0, self.chosen_all.count()):
            self.chosen_all.setCurrentRow(i)
            namefile = self.chosen_all.currentItem().text()
            merge_files.append(namefile)

        # get the path to the merge file (in the hdf5 file)
        path_hdf5 = self.find_path_hdf5_est()
        path_merges = []
        for m in merge_files:
            path_merges.append(path_hdf5)

        # save the discharges in the xml project file
        self.save_discharge()

        # send simulation
        figopt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        minh = figopt['min_height_hyd']
        sys.stdout = self.mystdout = StringIO()
        hydraulic_chronic.chronic_hydro(merge_files, path_merges,
                                        discharge_input, discharge_output,
                                        self.name_prj, self.path_prj,
                                        model_type='chronic_hydro',
                                        min_height=minh)
        sys.stdout = sys.__stdout__
        self.send_err_log()

        # add to the merge files in habitat calc
        self.drop_merge.emit()
        self.send_log.emit(self.tr("The created file is ready for habitat\
         calculation and has been added to the 'Habitat Calc.' tab. (Chronic_") + merge_files[0] + ")\n")

        # send log (with message on getting the data in habitat calc)
        self.send_log.emit(
            "py    merge_files= ['" + "', '".join(merge_files) + "']")
        self.send_log.emit(
            "py    path_merges= [r'" + "', r'".join(path_merges) + "']")
        self.send_log.emit(
            "py    discharge_input= [" + self.input.text() + ']')
        self.send_log.emit(
            "py    discharge_output= [" + self.output.text() + ']')
        self.send_log.emit("py    minh =" + str(minh))
        self.send_log.emit(
            "py    hydraulic_chronic.chronic_hydro(\
                    merge_files, path_merges, discharge_input, "
            "discharge_output, name_prj, path_prj, minh)")

        self.send_log.emit("restart HYDRO_CHRONIC")
        self.send_log.emit(
            "restart    list of merge file: " + ",".join(merge_files))
        self.send_log.emit("restart    discharge_input: " + self.input.text())
        self.send_log.emit(
            "restart    discharge_output: " + self.output.text())
        self.send_log.emit("restart    minimum_height: " + str(minh))
