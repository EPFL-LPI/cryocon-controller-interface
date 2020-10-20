# -*- mode: python -*-

block_cipher = None


a = Analysis(['C:\\Users\\carls\\Documents\\Python Scripts\\cryocon-controller\\app\\src\\main\\python\\main.py'],
             pathex=['C:\\Users\\carls\\Documents\\Python Scripts\\cryocon-controller\\app\\target\\PyInstaller'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=['C:\\Users\\carls\\AppData\\Local\\Temp\\tmph69mn8h2\\fbs_pyinstaller_hook.py'],
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
          name='power-supply',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False , icon='C:\\Users\\carls\\Documents\\Python Scripts\\cryocon-controller\\app\\src\\main\\icons\\Icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='power-supply')
