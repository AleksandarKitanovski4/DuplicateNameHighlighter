# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = collect_submodules('core') + collect_submodules('gui') + collect_submodules('utils')

a = Analysis([
    'main.py',
    'core/scroll_tracker.py',
],
    pathex=['.'],
    binaries=[],
    datas=[
        ('core/*.py', 'core'),
        ('gui/*.py', 'gui'),
        ('utils/*.py', 'utils'),
        ('*.db', '.'),
        ('*.json', '.'),
        ('attached_assets/*', 'attached_assets'),
        ('gui/settings_dialog.py', 'gui'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DuplicateNameHighlighter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DuplicateNameHighlighter'
) 