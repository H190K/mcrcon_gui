"""Build the desktop app with PyInstaller, then package it.

    python tools/build.py              # app folder + portable zip (+ installer if Inno Setup is available)

Outputs in dist/:
    MCRCON GUI/                               the app (folder build: starts fast, nothing to unpack)
    MCRCON-GUI-<ver>-<os>-<arch>-portable.zip that folder, zipped
    MCRCON-GUI-<ver>-windows-x64-setup.exe    Windows installer (needs Inno Setup 6 + packaging/installer.iss)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcrcon_gui import __version__  # noqa: E402

APP_NAME = "MCRCON GUI"
DIST = ROOT / "dist"

# Qt modules the app never touches; leaving them out keeps the bundle small.
EXCLUDES = [
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtPdf",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia", "PySide6.Qt3DCore",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtOpenGL", "PySide6.QtSql",
    "PySide6.QtXml", "PySide6.QtBluetooth", "PySide6.QtPositioning", "tkinter", "unittest",
    "pydoc", "PIL", "ssl", "_ssl", "hashlib", "_hashlib",
]
# Imported at runtime by PySide's shibokensupport, invisible to PyInstaller's analysis.
HIDDEN_IMPORTS = ["logging", "argparse", "inspect", "textwrap", "typing", "contextlib", "tokenize"]
# Files PyInstaller's Qt hook copies that a widgets-only app does not need.
PRUNE = [
    "opengl32sw.dll", "Qt6Pdf.dll", "Qt6Network.dll", "Qt6Qml*.dll", "Qt6Quick*.dll", "Qt6VirtualKeyboard.dll",
    "qdirect2d.dll", "qjpeg.dll", "qwebp.dll", "qtiff.dll", "qgif.dll", "qsvg*.dll", "qicns.dll",
    "qtga.dll", "qwbmp.dll", "qpdf.dll", "translations", "libcrypto-*.dll", "libssl-*.dll",
]


def platform_tag() -> str:
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine)
    return f"{system}-{arch}"


def build_app() -> Path:
    assets = ROOT / "src" / "mcrcon_gui" / "assets"
    sep = ";" if sys.platform == "win32" else ":"
    args = [
        str(ROOT / "tools" / "launcher.py"),
        "--name", APP_NAME,
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(ROOT / "src"),
        "--add-data", f"{assets}{sep}mcrcon_gui/assets",
        "--icon", str(assets / "icon.ico"),
        "--distpath", str(DIST),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]
    if sys.platform == "win32":
        args += ["--version-file", str(_write_version_file())]
    for module in EXCLUDES:
        args += ["--exclude-module", module]
    for module in HIDDEN_IMPORTS:
        args += ["--hidden-import", module]
    PyInstaller.__main__.run(args)

    app_dir = DIST / APP_NAME
    for pattern in PRUNE:
        for path in app_dir.rglob(pattern):
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    for license_file in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy(ROOT / license_file, app_dir / license_file)
    return app_dir


def build_zip(app_dir: Path) -> Path:
    base = DIST / f"MCRCON-GUI-{__version__}-{platform_tag()}-portable"
    return Path(shutil.make_archive(str(base), "zip", root_dir=DIST, base_dir=app_dir.name))


def build_installer(app_dir: Path) -> Path | None:
    script = ROOT / "packaging" / "installer.iss"
    iscc = shutil.which("ISCC") or next(
        (p for p in (Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
                     Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
                     Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe") if p.exists()),
        None,
    )
    if sys.platform != "win32" or not script.exists() or not iscc:
        print("Skipping installer (needs Windows, Inno Setup 6 and packaging/installer.iss).")
        return None
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_art.py")], check=True)
    output = f"MCRCON-GUI-{__version__}-{platform_tag()}-setup"
    # Compile into a temp folder: antivirus folder protection (e.g. Defender on Desktop/Documents)
    # can lock the setup exe while Inno Setup is still writing its resources.
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [str(iscc), "/Q", f"/O{tmp}", f"/DAppVersion={__version__}", f"/DSourceDir={app_dir}", f"/DOutputBase={output}", str(script)],
            check=True,
        )
        target = DIST / f"{output}.exe"
        shutil.move(str(Path(tmp) / f"{output}.exe"), target)
    return target


def _write_version_file() -> Path:
    major, minor, patch = (int(x) for x in __version__.split("."))
    path = ROOT / "build" / "version_info.txt"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({major}, {minor}, {patch}, 0), prodvers=({major}, {minor}, {patch}, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Hasan Albehadili (H190K)'),
      StringStruct('FileDescription', 'MCRCON GUI'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('ProductName', 'MCRCON GUI'),
      StringStruct('ProductVersion', '{__version__}'),
      StringStruct('LegalCopyright', 'Copyright (c) 2025-2026 Hasan Albehadili. MIT License.'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return path


def main() -> None:
    app_dir = build_app()
    outputs = [build_zip(app_dir), build_installer(app_dir)]
    print("\nBuilt:")
    for out in [app_dir, *outputs]:
        if out:
            print(f"  {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
