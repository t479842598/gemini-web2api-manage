# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the manage edition binary.

Build on the target platform. PyInstaller does not cross-compile native
bootloaders, so Linux artifacts must be built on Linux (or a Linux CI runner).
"""
from pathlib import Path
import sys

ROOT = Path(SPECPATH).resolve().parent
UPSTREAM = ROOT / "_upstream"
if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))

from PyInstaller.utils.hooks import collect_submodules
ADMIN_STATIC = ROOT / "gemini_web2api_manage" / "admin_static"

hiddenimports = (
    collect_submodules("gemini_web2api")
    + collect_submodules("gemini_web2api_manage")
)

a = Analysis(
    [str(ROOT / "gemini_web2api_manage" / "__main__.py")],
    pathex=[str(ROOT), str(UPSTREAM)],
    binaries=[],
    datas=[(str(ADMIN_STATIC), "gemini_web2api_manage/admin_static")],
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
    a.binaries,
    a.datas,
    [],
    name="gemini-web2api-manage",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
