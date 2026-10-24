# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all


streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")
datas = streamlit_datas + [
    ("Icono.jpeg", "."),
    ("Icono.ico", "."),
    ("ui/assets", "ui/assets"),
    ("reporting/streamlit_reports.py", "reporting"),
    ("reporting/pdf_export.py", "reporting"),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=streamlit_binaries,
    datas=datas,
    hiddenimports=streamlit_hiddenimports + [
        "streamlit.web.cli",
        "reporting.streamlit_reports",
        "reporting.pdf_export",
        "mysql.connector",
    ],
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
    name="SNIG",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["Icono.ico"],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SNIG",
)
