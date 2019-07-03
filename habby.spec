# -*- mode: python -*-

#from PyInstaller.utils.hooks import collect_data_files # this is very helpful
#_osgeo_pyds = collect_data_files('osgeo', include_py_files=True)
#osgeo_pyds = []
#for p, lib in _osgeo_pyds:
#    if '.pyd' in p:
#        osgeo_pyds.append((p, ''))

		
block_cipher = None


a = Analysis(['habby.py'],
             pathex=['C:\\habby'],
             binaries=[],  # osgeo_pyds
             datas=[],
             hiddenimports=[],
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
          console=False , icon='translation\\habby_icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='habby')
