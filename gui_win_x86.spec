# -*- mode: python -*-

block_cipher = None
from os.path import expanduser
os.path.expanduser
a = Analysis(['circleguard/gui.pyw'],
             pathex=['.', 'C:/Program Files (x86)/Windows Kits/10/Redist/ucrt/DLLs/x86', expanduser('~/AppData/Local/Programs/Python/Python37-32/')],
             binaries=[(expanduser('~/AppData/Local/Programs/Python/Python37-32/Lib/tkinter'), 'tk'), (expanduser('~/AppData/Local/Programs/Python/Python37-32/tcl'), 'tcl')],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Circleguard_x86',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='./circleguard/resources/logo.ico')
