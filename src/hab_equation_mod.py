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


class HabEquationManager:
    def __init__(self):
        self.eq_a = EquationA()
        self.eq_b = EquationB()
        self.eq_c = EquationC()
        self.list = [self.eq_a, self.eq_b, self.eq_c]
        self.names = [self.eq_a.name, self.eq_b.name, self.eq_c.name]


class EquationA:
    def __init__(self):
        self.name = "a"
        self.img_path = os.path.join(os.getcwd(), 'file_dep', "equation_" + self.name + ".png")

    def compute(self, variable_list):
        # empty hsi array
        hsi = np.array([1.0] * len(variable_list[0]))

        # compute
        for var in variable_list:
            hsi *= var

        return hsi


class EquationB:
    def __init__(self):
        self.name = "b"
        self.img_path = os.path.join(os.getcwd(), 'file_dep', "equation_" + self.name + ".png")

    def compute(self, variable_list):
        # empty hsi array
        hsi = np.array([1.0] * len(variable_list[0]))

        # compute
        for var in variable_list:
            hsi *= var
        hsi = np.power(hsi, 1 / len(variable_list))

        return hsi


class EquationC:
    def __init__(self):
        self.name = "c"
        self.img_path = os.path.join(os.getcwd(), 'file_dep', "equation_" + self.name + ".png")

    def compute(self, variable_list):
        # empty hsi array
        hsi = np.array([0.0] * len(variable_list[0]))

        # compute
        for var in variable_list:
            hsi += var
        hsi = hsi / len(variable_list)

        return hsi


hab_equation_manager = HabEquationManager()
