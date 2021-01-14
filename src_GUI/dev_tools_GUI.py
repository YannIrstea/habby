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
from PyQt5.QtCore import QAbstractTableModel, QRect, QPoint, QObject, pyqtSignal, QEvent, QVariant, Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QKeySequence
from PyQt5.QtWidgets import QTabBar, QStylePainter, QStyleOptionTab, QStyle, QListWidget, QApplication, QPushButton, QGroupBox, QFrame


def change_button_color(button, color):
    """change_button_color

        Change a button's color
    :param button: target button
    :type button: QPushButton
    :param color: new color (any format)
    :type color: str
    :return: None
    """
    style_sheet = button.styleSheet()
    pairs = [pair.replace(' ', '') for pair in style_sheet.split(';') if pair]

    style_dict = {}
    for pair in pairs:
        key, value = pair.split(':')
        style_dict[key] = value

    style_dict['background-color'] = color
    style_sheet = '{}'.format(style_dict)

    chars_to_remove = ('{', '}', '\'')
    for char in chars_to_remove:
        style_sheet = style_sheet.replace(char, '')
    style_sheet = style_sheet.replace(',', ';')

    button.setStyleSheet(style_sheet)


class LeftHorizontalTabBar(QTabBar):
    def tabSizeHint(self, index):
        s = QTabBar.tabSizeHint(self, index)
        s.transpose()
        return s

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionTab()

        for i in range(self.count()):
            self.initStyleOption(opt, i)
            painter.drawControl(QStyle.CE_TabBarTabShape, opt)
            painter.save()

            s = opt.rect.size()
            s.transpose()
            r = QRect(QPoint(), s)
            r.moveCenter(opt.rect.center())
            opt.rect = r

            c = self.tabRect(i).center()
            painter.translate(c)
            painter.rotate(90)
            painter.translate(-c)
            painter.drawControl(QStyle.CE_TabBarTabLabel, opt)
            painter.restore()


class QListWidgetClipboard(QListWidget):
    def __init__(self):
        super().__init__()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            clipboard = QApplication.clipboard()
            string_to_clipboard = ""
            for item in self.selectedItems():
                string_to_clipboard = string_to_clipboard + item.text() + "\n"
            clipboard.setText(string_to_clipboard)
        else:
            QListWidget.keyPressEvent(self, event)


class EnterPressEvent(QObject):
    enter_signal = pyqtSignal()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == 16777220:
            self.enter_signal.emit()
            return True  # ENTER
        else:
            # standard event processing
            return QObject.eventFilter(self, obj, event)


class MyTableModel(QAbstractTableModel):
    def __init__(self, datain, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = datain

    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        return len(self.arraydata[0])

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(self.arraydata[index.row()][index.column()])


class MyTableModelHab(QStandardItemModel):
    def __init__(self, data_to_table, horiz_headers, vertical_headers, source, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        # save source
        self.source = source
        # model data for table view
        if data_to_table and horiz_headers and vertical_headers:
            for row_index in range(len(vertical_headers)):
                line_string_list = []
                for column_index in range(len(horiz_headers)):
                    line_string_list.append(QStandardItem(data_to_table[row_index][column_index]))
                self.appendRow(line_string_list)
            # save data to export and plot
            self.rownames = vertical_headers
            self.colnames = horiz_headers
            # headers
            horiz_headers = [head.replace("_", "\n") for head in horiz_headers]
            for head_index, head in enumerate(horiz_headers):
                if "all\nstages" in head:
                    horiz_headers[head_index] = head.replace("all\nstages", "all_stages")
            self.setHorizontalHeaderLabels(horiz_headers)
            self.setVerticalHeaderLabels(vertical_headers)

    def get_data_from_column(self, column):
        col_index = self.colnames.index(column)
        data_to_get = []
        for row_nb in range(len(self.rownames)):
            data_to_get.append(self.item(row_nb, col_index).text())
        return data_to_get


class QGroupBoxCollapsible(QGroupBox):
    def __init__(self, title=""):
        super().__init__()
        self.setTitle(title)
        # group title
        self.setCheckable(True)
        self.setStyleSheet('QGroupBox::indicator {width: 20px; height: 20px;}'
                           
            'QGroupBox::indicator:unchecked {image: url(translation//icon//triangle_black_closed_50_50.png);}'  # close
            'QGroupBox::indicator:unchecked:hover {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:pressed {image: url(translation//icon//triangle_black_closed_50_50.png);}'
                           
            'QGroupBox::indicator:checked {image: url(translation//icon//triangle_black_open_50_50.png);}'  # open
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
            self.setFlat(False)
            self.setFixedHeight(self.sizeHint().height())
        else:
            self.setFlat(True)
            self.setFixedHeight(23)


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