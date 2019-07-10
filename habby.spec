# -*- mode: python -*-
		
block_cipher = None

import os
from PyInstaller.utils.hooks import collect_data_files # this is very helpful
from osgeo import gdal, ogr, osr
from fiona.ogrext import Iterator, ItemsIterator, KeysIterator

paths = [
	'C:\\habby',
    'C:\\Users\\quentin.royer\\AppData\\Local\\Programs\\Python\\Python36\\DLLs',
    'C:\\Users\\quentin.royer\\Documents\\TAF\\ENVIRONNEMENTS_VIRTUELS\\env_habby_dev\\Lib\\site-packages\\osgeo'
]

_osgeo_pyds = collect_data_files('osgeo', include_py_files=True)
_osgeo_pyds  = _osgeo_pyds  + collect_data_files('fiona', include_py_files=True)
osgeo_pyds = []
for p, lib in _osgeo_pyds:
    if '.pyd' in p or '.pyx' in p or '.pyc' in p:
        osgeo_pyds.append((p, '.'))
print(osgeo_pyds)

hidden_imports = [
    'fiona',
	'fiona._shim',
	'fiona.schema',
    'gdal',
    'shapely',
    'shapely.geometry'
]

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
