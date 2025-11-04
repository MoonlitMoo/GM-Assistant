from __future__ import annotations
import sys
import shutil
import subprocess
from pathlib import Path
from importlib import resources as _res

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from dmt.core.config import APP


def set_app_identity(app_id: str, desktop_file: str) -> None:
    """
    Set a unique application identity across platforms.

    On Windows:
        - Sets the AppUserModelID (for taskbar grouping and icon identity).
    On Linux:
        - Sets the desktop file name (for DE integration and icon lookup).
    """
    if sys.platform == "win32":
        # Set the window icon
        if "player" in desktop_file:
            QApplication.setWindowIcon(QIcon("dmt/assets/icons/gm-assistant-player.ico"))
        else:
            QApplication.setWindowIcon(QIcon("dmt/assets/icons/gm-assistant.ico"))
        # Set application name
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        # Set the desktop file
        if desktop_file:
            QApplication.setDesktopFileName(desktop_file)


def ensure_linux_desktop_entries() -> dict:
    """
    Ensure user-local .desktop files and icons exist; if missing, copy from package data.
    """
    result = {"installed": [], "skipped": [], "errors": []}

    if not sys.platform.startswith("linux"):
        return result  # no-op elsewhere

    package = "dmt.assets"
    apps_dir = Path.home() / ".local/share/applications"
    hicolor_dir = Path.home() / ".local/share/icons/hicolor"

    items = [APP, f"{APP}-player"]
    icon_sizes = (32, 48, 64, 128, 256, 512)
    apps_dir.mkdir(parents=True, exist_ok=True)
    hicolor_dir.mkdir(parents=True, exist_ok=True)

    def _copy_if_missing(src: Path, dst: Path):
        if dst.exists():
            result["skipped"].append(str(dst))
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        result["installed"].append(str(dst))
        return True

    # Resolve package base path (works for zipped packages too)
    for item in items:
        # Source files inside the package
        try:
            with _res.as_file((_res.files(package) / "desktop" / f"{item}.desktop")) as src_desktop:
                dst_desktop = apps_dir / f"{item}.desktop"
                _copy_if_missing(src_desktop, dst_desktop)
        except Exception as e:
            result["errors"].append((f"{package}:desktop/{item}.desktop", str(e)))

        try:
            with _res.as_file((_res.files(package) / "icons" / f"{item}.png")) as src_icon:
                # Copy the same icon into several hicolor sizes (ok even if source is 256)
                for sz in icon_sizes:
                    dst_icon = hicolor_dir / f"{sz}x{sz}" / "apps" / f"{item}.png"
                    try:
                        _copy_if_missing(src_icon, dst_icon)
                    except Exception as e:
                        result["errors"].append((str(dst_icon), str(e)))
        except Exception as e:
            result["errors"].append((f"{package}:icons/{item}.png", str(e)))

    # If we installed anything, try to refresh caches
    if result["installed"]:
        _best_effort_refresh_caches(apps_dir, hicolor_dir)
    return result


def _best_effort_refresh_caches(apps_dir: Path, hicolor_dir: Path) -> None:
    def _run_if_available(cmd: list[str]) -> None:
        exe = shutil.which(cmd[0])
        if not exe:
            return
        try:
            subprocess.run([exe, *cmd[1:]], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # Update desktop database (some DEs read this)
    _run_if_available(["update-desktop-database", str(apps_dir)])

    # Refresh GTK icon cache for hicolor theme
    # (Some systems use gtk4's icon cache tool name; most still have this one.)
    cache_root = hicolor_dir  # the tool expects the theme dir itself
    _run_if_available(["gtk-update-icon-cache", "-f", "-t", str(cache_root)])

    # Refresh KDE service cache (whichever exists)
    _run_if_available(["kbuildsycoca6"])
    _run_if_available(["kbuildsycoca5"])
