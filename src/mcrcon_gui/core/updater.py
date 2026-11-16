"""Update check, download and install (stdlib only, no Qt).

* The manifest lives at ``https://mcrcon.app/update/latest.json`` (see the mcrcon-website repo)
  and points at the versioned installer attached to a GitHub release.
* All network traffic goes through the ``curl.exe`` that ships with Windows 10+, falling back
  to PowerShell. That uses the OS's TLS stack and proxy settings, so the app doesn't need to
  bundle OpenSSL, and no console window ever appears (``CREATE_NO_WINDOW``).
* The installer's size and SHA-256 are always checked against the manifest before it runs.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .. import APP_NAME, UPDATE_MANIFEST_URLS, __version__

USER_AGENT = f"MCRCON-GUI/{__version__}"
ProgressCallback = Callable[[int, int], None]

# Process-creation flags are Windows-only; POSIX Python rejects any non-zero value.
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
_DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
_CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
_ERROR_ELEVATION_REQUIRED = 740
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_POLL_INTERVAL = 0.15
_MAX_MANIFEST_BYTES = 256 * 1024


class UpdateError(Exception):
    """Network, parse, download or verification failure."""


class UpdateCancelled(UpdateError):
    """The download was cancelled."""


@dataclass
class UpdateInfo:
    version: str
    url: str
    sha256: str
    size: int
    published: str = ""
    notes: list[str] = field(default_factory=list)


# -- versions --------------------------------------------------------------------------


def version_key(version: str) -> tuple[int, ...]:
    """``"v1.10.2-beta"`` -> ``(1, 10, 2)``; trailing zeros are dropped so 1.0 == 1.0.0."""
    core = version.strip().lstrip("vV").split("+", 1)[0].split("-", 1)[0]
    parts: list[int] = []
    for piece in core.split("."):
        match = re.match(r"\d+", piece)
        if not match:
            break
        parts.append(int(match.group()))
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    return version_key(remote) > version_key(local)


# -- install type ------------------------------------------------------------------------


def can_self_install() -> bool:
    """True for the Windows build installed by the setup program (it has an uninstaller next to it)."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    return any(Path(sys.executable).parent.glob("unins*.exe"))


# -- manifest --------------------------------------------------------------------------


def _check_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in _LOOPBACK_HOSTS):
        return url
    raise UpdateError(f"Refusing insecure update URL: {url}")


def parse_manifest(data: bytes | str | dict, base_url: str) -> UpdateInfo:
    """Validate a manifest and resolve a relative installer ``url`` against *base_url*."""
    try:
        obj = json.loads(data) if isinstance(data, (bytes, str)) else data
        if not isinstance(obj, dict):
            raise TypeError("manifest is not an object")
        version = str(obj["version"]).strip()
        url = urllib.parse.urljoin(base_url, str(obj["url"]).strip())
        sha256 = str(obj["sha256"]).strip().lower()
        size = int(obj.get("size", 0) or 0)
        published = str(obj.get("published", "") or "")
        notes_raw = obj.get("notes", []) or []
        notes = [str(n) for n in notes_raw] if isinstance(notes_raw, list) else [str(notes_raw)]
    except (ValueError, KeyError, TypeError) as exc:
        raise UpdateError(f"Invalid update manifest: {exc}") from exc
    if not version_key(version):
        raise UpdateError(f"Invalid version in manifest: {version!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise UpdateError("Invalid sha256 in manifest")
    if size < 0:
        raise UpdateError("Invalid size in manifest")
    return UpdateInfo(version, _check_url(url), sha256, size, published, notes)


def _find_curl() -> str | None:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    builtin = Path(system_root) / "System32" / "curl.exe"
    if builtin.is_file():
        return str(builtin)
    return shutil.which("curl.exe") or shutil.which("curl")


def _find_powershell() -> str | None:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    builtin = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if builtin.is_file():
        return str(builtin)
    return shutil.which("powershell.exe") or shutil.which("pwsh")


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _downloaders(url: str, out: Path, *, timeout: float | None = None, small: bool = False) -> list[tuple[list[str], bool]]:
    """Command lines to try in order; the flag says whether stdout reports the final URL."""
    attempts: list[tuple[list[str], bool]] = []
    if curl := _find_curl():
        cmd = [curl, "-L", "--fail", "--silent", "--show-error", "-A", USER_AGENT]
        if timeout:
            cmd += ["--max-time", str(max(1, int(timeout)))]
        if small:
            cmd += ["-H", "Cache-Control: no-cache", "-H", "Accept: application/json", "-w", "%{url_effective}"]
        else:
            cmd += ["--retry", "2", "--connect-timeout", "20"]
        attempts.append((cmd + ["-o", str(out), url], small))
    if sys.platform == "win32" and (ps := _find_powershell()):
        limit = f" -TimeoutSec {max(1, int(timeout))}" if timeout else ""
        script = (
            "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; "
            "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
            f"Invoke-WebRequest -UseBasicParsing -Uri {_ps_quote(url)} -OutFile {_ps_quote(str(out))} "
            f"-UserAgent {_ps_quote(USER_AGENT)}{limit}"
        )
        attempts.append(([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script], False))
    return attempts


def _fetch_small(url: str, timeout: float) -> tuple[bytes, str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mcrcon-") as tmp:
        out = Path(tmp) / "manifest.json"
        attempts = _downloaders(url, out, timeout=timeout, small=True)
        if not attempts:
            raise UpdateError("No downloader available (curl / PowerShell)")
        for cmd, reports_url in attempts:
            out.unlink(missing_ok=True)
            try:
                proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                    cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout + 15, creationflags=_CREATE_NO_WINDOW
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                errors.append(str(exc))
                continue
            if proc.returncode == 0 and out.is_file():
                final = proc.stdout.decode("utf-8", "replace").strip() if reports_url else ""
                return out.read_bytes()[:_MAX_MANIFEST_BYTES], final or url
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            errors.append(stderr.splitlines()[-1] if stderr else f"exit code {proc.returncode}")
    raise UpdateError("Couldn't reach the update server (" + "; ".join(errors) + ")")


def update_sources() -> tuple[str, ...]:
    """The update sources. ``MCRCON_GUI_UPDATE_MANIFEST`` overrides them (staging and release testing)."""
    override = os.environ.get("MCRCON_GUI_UPDATE_MANIFEST")
    return (override,) if override else UPDATE_MANIFEST_URLS


def check_for_update(
    current: str = __version__, timeout: float = 8, manifest_urls: Sequence[str] | None = None
) -> UpdateInfo | None:
    """The newer release, ``None`` when up to date. Raises ``UpdateError`` if every source fails."""
    errors: list[str] = []
    for url in manifest_urls if manifest_urls is not None else update_sources():
        try:
            body, final_url = _fetch_small(_check_url(url), timeout)
            info = parse_manifest(body, final_url)
        except UpdateError as exc:
            errors.append(str(exc))
            continue
        return info if is_newer(info.version, current) else None
    raise UpdateError("; ".join(errors) if errors else "No update sources configured")


# -- download --------------------------------------------------------------------------


def default_download_dir() -> Path:
    return Path(tempfile.gettempdir()) / "mcrcon-gui" / "updates"


def sha256_file(path: Path) -> str:
    # hashlib is excluded from the frozen build (it drags in OpenSSL); _sha2 is built in.
    try:
        from _sha2 import sha256  # type: ignore[import-not-found]
    except ImportError:  # Python < 3.12
        from hashlib import sha256
    digest = sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_download(cmd: list[str], out: Path, total: int, on_progress: ProgressCallback | None, cancel: threading.Event | None) -> None:
    try:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=_CREATE_NO_WINDOW
        )
    except OSError as exc:
        raise UpdateError(f"Couldn't start downloader: {exc}") from exc
    last = -1
    while True:
        try:
            proc.wait(timeout=_POLL_INTERVAL)
            done = True
        except subprocess.TimeoutExpired:
            done = False
        if cancel is not None and cancel.is_set():
            proc.kill()
            proc.wait()
            raise UpdateCancelled("Download cancelled")
        if on_progress is not None:
            try:
                current = out.stat().st_size
            except OSError:
                current = 0
            if current != last:
                last = current
                on_progress(current, total)
        if done:
            break
    stderr = proc.stderr.read().decode("utf-8", "replace").strip() if proc.stderr else ""
    if proc.returncode != 0:
        raise UpdateError(stderr.splitlines()[-1] if stderr else f"Downloader exited with {proc.returncode}")


def download_installer(
    info: UpdateInfo, dest_dir: Path | None = None, on_progress: ProgressCallback | None = None, cancel: threading.Event | None = None
) -> Path:
    """Download and verify the installer; returns its path."""
    dest_dir = Path(dest_dir) if dest_dir is not None else default_download_dir()
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UpdateError(f"Can't create download folder: {exc}") from exc
    safe_version = re.sub(r"[^0-9A-Za-z.]+", "_", info.version)
    final = dest_dir / f"MCRCON-GUI-Setup-{safe_version}.exe"
    _check_url(info.url)

    if final.is_file() and sha256_file(final) == info.sha256:  # already downloaded earlier
        if on_progress is not None:
            on_progress(final.stat().st_size, info.size or final.stat().st_size)
        return final

    part = final.with_name(final.name + ".part")
    errors: list[str] = []
    for cmd, _ in _downloaders(info.url, part):
        part.unlink(missing_ok=True)
        try:
            _run_download(cmd, part, info.size, on_progress, cancel)
            if part.is_file():
                break
            errors.append("no file was written")
        except UpdateCancelled:
            part.unlink(missing_ok=True)
            raise
        except UpdateError as exc:
            errors.append(str(exc))
    else:
        part.unlink(missing_ok=True)
        raise UpdateError("Download failed: " + ("; ".join(errors) or "no downloader available"))

    try:
        size = part.stat().st_size
        if info.size and size != info.size:
            raise UpdateError(f"Downloaded size {size} doesn't match the expected {info.size}")
        if sha256_file(part) != info.sha256:
            raise UpdateError("The downloaded installer failed verification (SHA-256 mismatch)")
        os.replace(part, final)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return final


def launch_installer(path: Path, *, silent: bool = True, relaunch: bool = True) -> None:
    """Start the installer detached from this process; the caller should quit right after.

    Silent mode shows only a small progress window, closes the running app, and (unless
    ``relaunch`` is False) starts the new version when it is done.
    """
    path = Path(path)
    if not path.is_file():
        raise UpdateError(f"Installer not found: {path}")
    args = [str(path)]
    if silent:
        args += ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"]
        if relaunch:
            args.append("/RELAUNCH")  # handled by the [Run]/[Code] section of the installer script
    try:
        subprocess.Popen(  # noqa: S603 - verified local installer, no shell
            args, cwd=str(path.parent), close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP,
        )
    except OSError as exc:
        if getattr(exc, "winerror", None) == _ERROR_ELEVATION_REQUIRED and hasattr(os, "startfile"):
            os.startfile(str(path), arguments=" ".join(args[1:]))  # noqa: S606 - shows the UAC prompt
            return
        raise UpdateError(f"Couldn't start the installer: {exc}") from exc
