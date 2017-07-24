# -*- mode: python -*-
a = Analysis(['CoregulationDataHarvester.py'],
             pathex=['c:\\Python27'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)


pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Win-x64-CoregulationDataHarvester.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
