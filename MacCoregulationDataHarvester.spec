# -*- mode: python -*-

a = Analysis(['CoregulationDataHarvester.py'],
             pathex=['/Users/levtsypin/Desktop/TranscriptomicsProject'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='MacOS-10.6-CoregulationDataHarvester',
          debug=False,
          strip=None,
          upx=True,
          console=True )
