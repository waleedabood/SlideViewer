# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect PyQt6 WebEngine data files
datas = [
    ('slide_viewer/SLIDE_FORMAT_GUIDE.md', 'slide_viewer'),
    ('slide_viewer/test.md', 'slide_viewer'),
]

# Collect all submodules
hiddenimports = collect_submodules('markdown') + [
    'pygments.formatters.html',
    'pygments.styles.monokai',
    'pygments.lexers',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'tkinter', '_tkinter',
        'pygame', 'boto3', 'botocore', 'sounddevice', '_sounddevice_data',
        'numpy', 'pandas', 'scipy', 'matplotlib', 'PIL.ImageQt',
        'IPython', 'jupyter', 'notebook', 'zmq', 'tornado',
        'cv2', 'sklearn', 'tensorflow', 'torch',
        'sqlalchemy', 'flask', 'django', 'fastapi', 'uvicorn', 'uvloop',
        'black', 'mypy', 'pytest', 'setuptools', 'pip',
        'bcrypt', 'paramiko', 'cryptography',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SlideViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SlideViewer',
)

app = BUNDLE(
    coll,
    name='SlideViewer.app',
    icon=None,
    bundle_identifier='com.waleedabood.slideviewer',
    info_plist={
        'CFBundleName': 'Slide Viewer',
        'CFBundleDisplayName': 'Slide Viewer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)
