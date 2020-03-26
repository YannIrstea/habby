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

HSSI = dict(name_models_list=['', 'LAMMI', 'RubarBE 1D', 'Mascaret 1D', 'HEC-RAS 1D',
                         'Rubar20 2D', 'TELEMAC 2D', 'HEC-RAS 2D', 'Iber 2D', 'River 2D', 'SW2D', 'BASEMENT 2D',
                         'TXT 1D-2D'],
            attribute_models_list=['free', 'lammi', 'rubar1d', 'mascaret', 'hecras1d',
                                   'rubar2d', 'telemac', 'hecras2d', 'iber2d', 'river2d', 'sw2d', 'basement2d', 'ascii'],
            class_models_list=["QWidget", "LAMMI", "Rubar1D", "Mascaret", "HEC_RAS1D",
                                 "Rubar2D", "TELEMAC", "HEC_RAS2D", "IBER2D", "River2D", "SW2D", "Basement2D", "ASCII"],
            website_models_list=["",
                                 "<a href=\"https://www.edf.fr/en/the-edf-group/world-s-largest-power-company/activities/research-and-development/scientific-communities/simulation-softwares?logiciel=10847\">LAMMI</a>",
                                 "<a href=\"https://riverhydraulics.inrae.fr/outils/modelisation-numerique/modelisation-1d-avec-evolution-des-fonds-rubarbe/\">RubarBE 1D</a>",
                                 "<a href=\"http://www.openmascaret.org/\">Mascaret 1D</a>",
                                 "<a href=\"https://www.hec.usace.army.mil/software/hec-ras/\">HEC-RAS 1D</a>",
                                 "<a href=\"http://www.captiven.fr/article/logiciel-rubar-20\">Rubar20 2D</a>",
                                 "<a href=\"http://www.opentelemac.org/index.php/presentation?id=17\">TELEMAC 2D</a>",
                                 "<a href=\"https://www.hec.usace.army.mil/software/hec-ras/\">HEC-RAS 2D</a>",
                                 "<a href=\"http://www.iberaula.es/\">Iber 2D</a>",
                                 "<a href=\"http://www.river2d.ualberta.ca/\">River 2D</a>",
                                 "<a href=\"https://sw2d.wordpress.com\">SW2D</a>",
                                 "<a href=\"https://basement.ethz.ch/\">BASEMENT</a>",
                                 "<a href=\"https://github.com/YannIrstea/habby\">TXT 1D-2D</a>"])


class HydraulicSimulationResults:
    def __init__(self, filename, folder_path, model_type, path_prj):
        """
        :param filename_path_list: list of absolute path file, type: list of str
        :param path_prj: absolute path to project, type: str
        :param model_type: type of hydraulic model, type: str
        :param nb_dim: dimension number (1D/1.5D/2D), type: int
        :return: hydrau_description_list, type: dict
        :return: warnings list, type: list of str
        """

        # init
        self.valid_file = True
        self.warning_list = []  # text warning output
        self.name_prj = os.path.splitext(os.path.basename(path_prj))[0]
        self.path_prj = path_prj
        self.hydrau_case = "unknown"
        self.filename = filename
        self.folder_path = folder_path
        self.filename_path = os.path.join(self.folder_path, self.filename)
        self.blob, self.ext = os.path.splitext(self.filename)

        # index_hydrau
        self.index_hydrau_file_exist = False
        if os.path.isfile(self.filename_path):
            self.index_hydrau_file_exist = True
        self.index_hydrau_file = "indexHYDRAU.txt"
        self.index_hydrau_file_path = os.path.join(self.folder_path, self.index_hydrau_file)
        # hydraulic attributes
        self.model_type = model_type
        # exist ?
        if not os.path.isfile(self.filename_path):
            self.warning_list.append("Error: The file does not exist.")
            self.valid_file = False

        # init
        self.timestep_name_list = None
        self.timestep_nb = None
        self.timestep_unit = None
        self.unit_z_equal = True
