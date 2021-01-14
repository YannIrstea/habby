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
from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtWidgets import QHBoxLayout, QComboBox, QProgressBar, QLabel, QPushButton

from src.process_manager_mod import MyProcessManager
from src_GUI.dev_tools_GUI import change_button_color


class ProcessProgLayout(QHBoxLayout):
    def __init__(self, run_function, send_log, process_type, send_refresh_filenames=None):
        super().__init__()
        widget_height = QComboBox().minimumSizeHint().height()
        # send_log
        self.send_log = send_log
        # progressbar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(widget_height)
        self.progress_bar.setValue(0.0)
        self.progress_bar.setRange(0.0, 100.0)
        self.progress_bar.setTextVisible(False)

        # progress_label
        self.progress_label = QLabel()
        self.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

        # run_stop_button
        self.run_stop_button = QPushButton(self.tr("run"))
        self.run_stop_button.setMaximumHeight(widget_height)
        change_button_color(self.run_stop_button, "#47B5E6")
        self.run_stop_button.clicked.connect(run_function)  # self.collect_data_from_gui_and_plot
        self.run_stop_button.setEnabled(False)

        # layout
        self.addWidget(self.progress_bar)
        self.addWidget(self.progress_label)
        self.addWidget(self.run_stop_button)

        # process_manager
        self.process_manager = MyProcessManager(process_type)

        # process_prog_show
        self.process_prog_show = ProcessProgShow(send_log=self.send_log,
                                                 send_refresh_filenames=send_refresh_filenames,
                                                 progressbar=self.progress_bar,
                                                 progress_label=self.progress_label,
                                                 computation_pushbutton=self.run_stop_button,
                                                 run_function=run_function)

    def start(self):
        self.process_prog_show.start_show_prog(self.process_manager)

    def stop_by_user(self):
        self.process_prog_show.stop_by_user()


class ProcessProgShow(QObject):
    """
    show progress (progress bar, text, number of process)
    """
    def __init__(self, send_log=None, send_refresh_filenames=None, progressbar=None, progress_label=None,
                 computation_pushbutton=None, run_function=None):
        super().__init__()
        self.send_log = send_log
        self.send_refresh_filenames = send_refresh_filenames
        if type(progressbar) == QProgressBar:
            self.progressbar = progressbar
        else:
            self.progressbar = QProgressBar()
        if type(progress_label) == QLabel:
            self.progress_label = progress_label
        else:
            self.progress_label = QLabel()
        self.computation_pushbutton = computation_pushbutton
        self.original_pushbutton_text = self.tr("run")
        self.run_function = run_function
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_prog)
        self.process_manager = None
        self.current_finished = 0

    def send_err_log(self, check_ok=False):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout before calling this function. It only sends the hundred first errors
        to avoid freezing the GUI. A similar function exists in estimhab_GUI.py. Correct both if necessary.

        :param check_ok: This is an optional paramter. If True, it checks if the function returns any error
        """
        error = False

        max_send = 100
        if self.mystdout is not None:
            str_found = self.mystdout.getvalue()
        else:
            return
        str_found = str_found.split('\n')
        for i in range(0, min(len(str_found), max_send)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
            if i == max_send - 1:
                self.send_log.emit(self.tr('Warning: too many information for the GUI'))
            if 'Error' in str_found[i] and check_ok:
                error = True
        if check_ok:
            return error

    def start_show_prog(self, process_manager):
        self.original_pushbutton_text = self.computation_pushbutton.text()

        self.process_manager = process_manager
        self.process_manager.send_log = self.send_log

        self.process_manager.start()

        self.computation_pushbutton.setText(self.tr("stop"))
        self.computation_pushbutton.disconnect()
        self.computation_pushbutton.clicked.connect(self.stop_by_user)

        # log
        self.send_log.emit(self.process_manager.process_type_gui + self.tr(" computing ") + "...")
        self.timer.start(100)

    def show_prog(self):
        # RUNNING
        if self.process_manager.isRunning():
            self.show_running_prog()
        # NOT RUNNING (stop_by_user, error, known error, done)
        else:
            self.show_not_running_prog()

    def show_running_prog(self):
        # progressbar
        self.progressbar.setValue(int(self.process_manager.process_list.progress_value))
        if self.current_finished != self.process_manager.process_list.nb_finished:
            # new
            self.progress_label.setText("{0:.0f}/{1:.0f}".format(self.process_manager.process_list.nb_finished,
                                                                 self.process_manager.process_list.nb_total))
            self.current_finished = self.process_manager.process_list.nb_finished

    def show_not_running_prog(self):
        error = False
        # stop show_prog
        self.timer.stop()

        self.progressbar.setValue(int(self.process_manager.process_list.progress_value))
        self.progress_label.setText("{0:.0f}/{1:.0f}".format(self.process_manager.process_list.nb_finished,
                                                             self.process_manager.process_list.nb_total))
        self.computation_pushbutton.setText(self.tr("run"))
        self.computation_pushbutton.setChecked(True)
        self.computation_pushbutton.disconnect()
        self.computation_pushbutton.clicked.connect(self.run_function)

        if self.process_manager.process_list.stop_by_user:
            # log
            self.send_log.emit(self.process_manager.process_type_gui + self.tr(" computation(s) stopped by user."))
        else:
            if error:
                # log
                self.send_log.emit(self.process_manager.process_type_gui + self.tr(" computation(s) finished with error(s)."))
            else:
                self.send_log.emit(self.process_manager.process_type_gui + self.tr(" computing finished."))

        if self.send_refresh_filenames is not None:
            # update_gui
            self.send_refresh_filenames.emit()

        self.computation_pushbutton.setText(self.original_pushbutton_text)

    def stop_by_user(self):
        self.process_manager.stop_by_user()
        self.computation_pushbutton.setText("run")
        self.computation_pushbutton.disconnect()
        self.computation_pushbutton.clicked.connect(self.run_function)