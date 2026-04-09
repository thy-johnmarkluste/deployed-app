# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules


block_cipher = None

datas = [
    ('assets', 'assets'),
]

if os.path.exists('.env'):
    datas.append(('.env', '.'))

hiddenimports = (
    collect_submodules('controllers')
    + collect_submodules('models')
    + collect_submodules('views')
)


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ThyWeb',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ThyWeb',
)

app = BUNDLE(
    coll,
    name='ThyWeb.app',
    icon=None,
    bundle_identifier='com.thyweb.desktop',
    info_plist={
        'CFBundleName': 'ThyWeb',
        'CFBundleDisplayName': 'ThyWeb',
        'CFBundleShortVersionString': '1.0.1',
        'CFBundleVersion': '1.0.1',
        'NSHighResolutionCapable': True,
    },
)
