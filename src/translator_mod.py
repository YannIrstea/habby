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
import sys
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import QApplication

from src.project_properties_mod import load_project_properties


def get_translator(path_prj):
    """
    :param path_prj: path_prj
    :return: application with translate method.
    """
    # get language from project_preferences['language']
    project_preferences = load_project_properties(path_prj)
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


def main():
    pass


if __name__ == '__main__':
    main()