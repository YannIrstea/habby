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
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
import sys
import time

from src.variable_unit_mod import HydraulicVariableUnitManagement, HydraulicVariableUnitList, SuitabilityIndexVariable


class HabEquationManager:
    def __init__(self):
        self.equation_dict = dict()


class EquationA:
    def __init__(self, hydraulic_variable_unit_list, unit_dict):
        self.hsi = np.multiply(hydraulic_variable_unit_list)





if __name__ == '__main__':
    hvum = HydraulicVariableUnitManagement()


    equ_a = EquationA([hvum.h, hvum.v, hvum.sub])

