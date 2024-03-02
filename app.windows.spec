# -*- mode: python ; coding: utf-8 -*-


import os, platform, shutil
# from pathlib import Path
# import PyInstaller.config
# PyInstaller.config.CONF["distpath"] = os.path.join(os.getcwd(), "dist")


def build_app():
    # home = str(Path.home())

    a = Analysis(
        [os.path.join(".", "app.py")],
        pathex=[],
        binaries=[],
        datas=[
            (
                os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "unidic_lite", "dicdir"),
                os.path.join(".", "unidic_lite", "dicdir"),
            ),
            (
                os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "manga_ocr"),
                os.path.join(".", "manga_ocr"),
            ),
        ],
        hiddenimports=[],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        module_collection_mode={
            "onnxscript": "pyz+py",
        },
    )
    pyz = PYZ(a.pure)

    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="app",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="eyeofbabel",
    )


build_app()

shutil.copytree(
    os.path.join(os.getcwd(), "assets"),
    os.path.join(os.getcwd(), "dist", "eyeofbabel", "assets"),
)
