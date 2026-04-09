# -*- mode: python ; coding: utf-8 -*-

import os


def _local_modules(package_dir):
    modules = []
    if not os.path.isdir(package_dir):
        return modules
    for root, _, files in os.walk(package_dir):
        for filename in files:
            if not filename.endswith('.py') or filename == '__init__.py':
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, '.')
            module_name = rel_path[:-3].replace('\\', '.').replace('/', '.')
            modules.append(module_name)
    return modules


block_cipher = None

datas = [
    ('assets', 'assets'),
]

if os.path.exists('.env'):
    datas.append(('.env', '.'))

hiddenimports = _local_modules('controllers') + _local_modules('models') + _local_modules('views')


a = Analysis(
    ['app.py'],
    pathex=[os.path.abspath('.')],
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
