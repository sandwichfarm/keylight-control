# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Key Light Controller

a = Analysis(
    ['src/keylight_controller.py'],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Third-party
        'qasync',
        'aiohttp',
        'zeroconf',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # Project modules (ensure inclusion)
        'core.models',
        'core.discovery',
        'core.service',
        'ui.main_window',
        'ui.widgets.jump_slider',
        'ui.widgets.rename_dialog',
        'ui.widgets.master_widget',
        'ui.widgets.keylight_widget',
        'ui.styles.dark_theme',
        'utils.single_instance',
        'utils.color_utils',
        'utils.system_tray',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='keylight-controller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
