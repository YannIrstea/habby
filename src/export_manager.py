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
from PyQt5.QtCore import QLocale


def export_point_txt(args):
    name, hvum, unit_data = args
    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:
        # header 1
        text_to_write_str = "x\ty\t"
        text_to_write_str += "\t".join(hvum.all_final_variable_list.nodes().names())
        text_to_write_str += '\n'
        f.write(text_to_write_str)

        # header 2 2
        text_to_write_str = '[m]\t[m]\t['
        text_to_write_str += "]\t[".join(hvum.all_final_variable_list.nodes().units())
        text_to_write_str += "]"
        f.write(text_to_write_str)

        # data
        text_to_write_str = ""
        # for each point
        for point_num in range(0, len(unit_data["node"][hvum.xy.name])):
            text_to_write_str += '\n'
            # data geom (get the triangle coordinates)
            x = str(unit_data["node"][hvum.xy.name][point_num][0])
            y = str(unit_data["node"][hvum.xy.name][point_num][1])
            text_to_write_str += f"{x}\t{y}"
            for node_variable_name in hvum.all_final_variable_list.nodes().names():
                text_to_write_str += "\t" + str(
                    unit_data["node"]["data"][node_variable_name][point_num])

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            text_to_write_str = text_to_write_str.replace('.', ',')

        # write file
        f.write(text_to_write_str)


def export_mesh_txt(args):
    name, hvum, unit_data = args
    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:
        # header 1
        text_to_write_str_list = ["node1", "node2", "node3"]
        text_to_write_str_list.extend(hvum.all_final_variable_list.meshs().names())
        text_to_write_str = "\t".join(text_to_write_str_list)
        text_to_write_str += '\n'
        f.write(text_to_write_str)

        # header 2
        text_to_write_str = "[]\t[]\t[]\t["
        text_to_write_str += ']\t['.join(hvum.all_final_variable_list.meshs().units())
        f.write(text_to_write_str)

        # data
        text_to_write_str = ""
        # for each mesh
        for mesh_num in range(0, len(unit_data["mesh"][hvum.tin.name])):
            node1 = unit_data["mesh"][hvum.tin.name][mesh_num][
                0]  # node num
            node2 = unit_data["mesh"][hvum.tin.name][mesh_num][1]
            node3 = unit_data["mesh"][hvum.tin.name][mesh_num][2]
            text_to_write_str += '\n'
            text_to_write_str += f"{str(node1)}\t{str(node2)}\t{str(node3)}\t"
            data_list = []
            for mesh_variable_name in hvum.all_final_variable_list.meshs().names():
                data_list.append(str(
                    unit_data["mesh"]["data"][mesh_variable_name][mesh_num]))
            text_to_write_str += "\t".join(data_list)

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            text_to_write_str = text_to_write_str.replace('.', ',')

        # write file
        f.write(text_to_write_str)