#-------------------------------------------------------------------------------
# Name:        module1
# Purpose: Let"s try to make a .exe. file
#
# Author:      Diane.Von-Gunten
#
# Created:     12/02/2016
# Copyright:   (c) Diane.Von-Gunten 2016
# Licence:     <your licence>

#-------------------------------------------------------------------------------

from distutils.core import setup
import py2exe
import matplotlib

setup(console=['habby.py'], #  windows=['Hec_ras01.py']
      data_files=matplotlib.get_py2exe_datafiles(),
      options={
                "py2exe":{
                        "includes": ["PyQt5.QtCore", "PyQt5.QtGui", "sip",  "matplotlib.backends.backend_tkagg", \
                                     "tkinter.filedialog", "h5py","h5py.defs", "h5py.utils", "h5py.h5ac", 'h5py._proxy' \
                                     ,'scipy.linalg.cython_blas', 'scipy.linalg.cython_lapack', \
                                     'scipy.special._ufuncs_cxx', 'scipy.sparse.csgraph._validation']
                }
        })

#, "h5py","h5py.defs", "h5py.utils", "h5py.h5ac"