# -*- mode: python -*-

block_cipher = None

import os
from PyInstaller.utils.hooks import collect_data_files  # this is very helpful
from osgeo import gdal, ogr, osr
from platform import system as operatingsystem

if operatingsystem() == 'Windows':
    habby_dev_path = 'C:\\habby_dev'
elif operatingsystem() == 'Linux':
    habby_dev_path = '\\local\\AIX\\quentin.royer\\Documents\\habby_dev'
elif operatingsystem() == 'Darwin':
    habby_dev_path = '\\local\\AIX\\quentin.royer\\Documents\\habby_dev'

paths = [
    os.path.join(habby_dev_path, 'habby'),
    os.path.join(habby_dev_path, 'env_virtuels\\env_habby_dev\\Lib\\site-packages\\osgeo'),
    os.path.join(habby_dev_path, 'env_virtuels\\env_habby_dev\\Lib\\site-packages\\triangle')
]

_osgeo_pyds = collect_data_files('osgeo', include_py_files=True)
osgeo_pyds = []
for p, lib in _osgeo_pyds:
    if '.pyd' in p or '.pyx' in p or '.pyc' in p:
        osgeo_pyds.append((p, '.'))
_triangle_pyds = collect_data_files('triangle', include_py_files=True)
triangle_pyds = []
for p, lib in _osgeo_pyds:
    if '.pyd' in p or '.pyx' in p or '.pyc' in p:
        triangle_pyds.append((p, '.'))
binaries = osgeo_pyds + triangle_pyds


hidden_imports = [
    'gdal',
    'pkg_resources.py2_warn']
# pkg_resources.py2_warn : if not set, .exe crash (Failed to execute script pyi_rth_pkgres)

a = Analysis(['habby.py'],
             pathex=[],
             binaries=osgeo_pyds,
             datas=[],
             hiddenimports=hidden_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='habby',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='translation\\habby_icon.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='habby')
