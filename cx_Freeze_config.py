#!/usr/bin/python
# -*- coding: utf-8 -*-
# Python 3



import sys
import os
import os.path
from cx_Freeze import setup, Executable

PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

#
# Options
#
path = sys.path

# python modules if cx_freeze does not find them
includes = ['numpy.core._methods', 'numpy.lib.format', 'matplotlib.backends.backend_qt5agg', 'matplotlib.backends.backend_pdf', 'scipy.sparse.csgraph._validation']
# exclusion
excludes = ['scipy.spatial.cKDTree'] # 
# package
packages = []
# include files
includefiles = []


if sys.platform == "win32":
    pass
    # includefiles += [...]
elif sys.platform == "linux2":
    pass
    # includefiles += [...]
else:
    pass
    # includefiles += [...]

	
# Linux libraries
binpathincludes = []
if sys.platform == "linux2":
    binpathincludes += ["/usr/lib"]

# optimization level (bytecode)
optimize = 0

# verbose mode
silent = False

# dictionary of the options
options = {"path": path,
           "includes": includes,
           "excludes": excludes,
           "packages": packages,
           "include_files": includefiles,
           "bin_path_includes": binpathincludes,
           "optimize": optimize,
           "silent": silent
           }

		   # Windows dll
if sys.platform == "win32":
    options["include_msvcr"] = True

#
# Targets
#

base = None
#************************* to see error in windows console set this two lines in comment : ***********************#
#if sys.platform == "win32":
#    base = "Win32GUI"  # graphical app
#****************************************************************************************************************#
    # base = "Console"  # text app

# icon
ico = None
if sys.platform == "win32":
    ico = "translation/habby_icon.ico"
target = Executable(
    script="habby.py",
    base=base,
    icon=ico
    )
#
# Setup
#
setup(
    name="Habby",
    version="0.24",
    description="HABitat suitaBilitY",
    author="Fabrice Zaoui",
    options={"build_exe": options},
    executables=[target]
    )
