"""Educational personal-media fetcher with a portable terminal UI.

The module intentionally keeps the runtime dependency surface small: Python and
yt-dlp are sufficient.  FFmpeg is used automatically when it is available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import yt_dlp
except ImportError as exc:  # Friendly message also works in a frozen executable.
    raise SystemExit("yt-dlp が見つかりません。'python -m pip install yt-dlp' を実行してください。") from exc


APP_NAME = "RAVENFETCH"
APP_VERSION = "0.1.1"
GITHUB_REPOSITORY = "softbloomxo/RavenFetch"
UPDATE_ASSET_NAME = "RavenFetch-Windows-x64.zip"
UPDATE_CHECK_INTERVAL = 24 * 60 * 60
SUPPORTED_HOSTS = {
    "tver.jp": "TVer",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
}


class UI:
    """Small dependency-free, Blackbird-inspired terminal renderer."""

    def __init__(self, color: bool = True) -> None:
        self.color = color and sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def _paint(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def banner(self) -> None:
        cyan = lambda value: self._paint("96", value)
        print(cyan(r"""
    ____  ___ _    _______   __
   / __ \/   | |  / /  _/ | / /
  / /_/ / /| | | / // //  |/ /
 / _, _/ ___ | |/ // // /|  /
/_/ |_/_/  |_|___/___/_/ |_/
"""))
        print(f"  {self._paint('1;97', APP_NAME)} {APP_VERSION}  {self._paint('90', 'personal media fetcher')}\n")

    def line(self, marker: str, message: str, color: str = "96") -> None:
        print(f" {self._paint(color, '[' + marker + ']')} {message}")

    def info(self, message: str) -> None:
        self.line("*", message)

    def ok(self, message: str) -> None:
        self.line("+", message, "92")

    def warn(self, message: str) -> None:
        self.line("!", message, "93")

    def error(self, message: str) -> None:
        self.line("x", message, "91")


def configure_console() -> None:
    """Avoid mojibake on Windows while remaining harmless on other platforms."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def app_directory() -> Path:
    """Return the directory containing the portable application."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def update_cache_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "RavenFetch"
    return base / "update-check.json"


def version_key(version: str) -> tuple[int, ...]:
    """Convert a conventional v1.2.3 tag into a comparable tuple."""
    numbers: list[int] = []
    for part in version.lstrip("vV").split("."):
        digits = "".join(character for character in part if character.isdigit())
        numbers.append(int(digits or 0))
    return tuple(numbers)


def fetch_latest_release() -> dict:
    request = Request(
        f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"RavenFetch/{APP_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=8) as response:
        return json.load(response)


def find_update_asset(release: dict) -> dict | None:
    return next(
        (asset for asset in release.get("assets", []) if asset.get("name") == UPDATE_ASSET_NAME),
        None,
    )


def should_check_for_update(force: bool = False) -> bool:
    if force:
        return True
    try:
        cache = json.loads(update_cache_path().read_text(encoding="utf-8"))
        return time.time() - float(cache.get("checked_at", 0)) >= UPDATE_CHECK_INTERVAL
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return True


def record_update_check() -> None:
    try:
        path = update_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"checked_at": time.time()}), encoding="utf-8")
    except OSError:
        pass


def download_update(asset: dict, ui: UI) -> Path:
    destination = Path(tempfile.gettempdir()) / UPDATE_ASSET_NAME
    request = Request(
        asset["browser_download_url"],
        headers={"User-Agent": f"RavenFetch/{APP_VERSION}"},
    )
    digest = hashlib.sha256()
    with urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)

    expected_digest = str(asset.get("digest") or "")
    if expected_digest.startswith("sha256:") and digest.hexdigest() != expected_digest.removeprefix("sha256:"):
        destination.unlink(missing_ok=True)
        raise ValueError("SHA-256 検証に失敗しました。")
    ui.ok("更新ファイルの取得と検証が完了しました。")
    return destination


def launch_update_installer(archive: Path) -> None:
    """Launch a temporary PowerShell helper that can replace the running EXE."""
    helper = Path(tempfile.gettempdir()) / "RavenFetch-update.ps1"
    helper.write_text(
        "param([int]$RavenPid,[string]$Archive,[string]$Target,[string]$Executable)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "Wait-Process -Id $RavenPid -ErrorAction SilentlyContinue\n"
        "$stage = Join-Path $env:TEMP ('RavenFetch-' + [guid]::NewGuid().ToString('N'))\n"
        "New-Item -ItemType Directory -Path $stage | Out-Null\n"
        "Expand-Archive -LiteralPath $Archive -DestinationPath $stage -Force\n"
        "Copy-Item -Path (Join-Path $stage '*') -Destination $Target -Recurse -Force\n"
        "Remove-Item -LiteralPath $stage -Recurse -Force\n"
        "Remove-Item -LiteralPath $Archive -Force\n"
        "Start-Process -FilePath (Join-Path $Target $Executable)\n"
        "Remove-Item -LiteralPath $PSCommandPath -Force\n",
        encoding="utf-8-sig",
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper),
            "-RavenPid",
            str(os.getpid()),
            "-Archive",
            str(archive),
            "-Target",
            str(app_directory()),
            "-Executable",
            Path(sys.executable).name,
        ],
        creationflags=creation_flags,
        close_fds=True,
    )


def check_for_update(ui: UI, force: bool = False) -> bool:
    """Check GitHub Releases and optionally stage a verified portable update."""
    if not should_check_for_update(force):
        return False
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        if force:
            ui.warn("自動更新はWindows版実行ファイルで利用できます。")
        return False

    try:
        release = fetch_latest_release()
        record_update_check()
        latest = str(release.get("tag_name", "")).lstrip("vV")
        if not latest or version_key(latest) <= version_key(APP_VERSION):
            if force:
                ui.ok(f"最新版です (v{APP_VERSION})。")
            return False
        asset = find_update_asset(release)
        if not asset:
            raise ValueError(f"Releaseに {UPDATE_ASSET_NAME} がありません。")
        ui.info(f"新しいバージョン v{latest} を利用できます。")
        answer = input(" 更新して再起動しますか? [Y/n] ").strip().lower()
        if answer not in {"", "y", "yes"}:
            return False
        archive = download_update(asset, ui)
        launch_update_installer(archive)
        ui.info("更新を開始しました。RavenFetchを終了します。")
        return True
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if force:
            ui.warn(f"更新を確認できません: {exc}")
        return False


def detect_service(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    for domain, service in SUPPORTED_HOSTS.items():
        if host == domain or host.endswith("." + domain):
            return service
    return "Other"


def is_web_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def find_ffmpeg() -> str | None:
    """Find system FFmpeg or a copy bundled beside a future executable."""
    candidates = [shutil.which("ffmpeg")]
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidates.extend(str(app_dir / name) for name in ("ffmpeg.exe", "ffmpeg"))
    return next((item for item in candidates if item and Path(item).is_file()), None)


def find_deno() -> str | None:
    """Find the JavaScript runtime recommended for full YouTube extraction."""
    candidates = [shutil.which("deno")]
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidates.extend(str(app_dir / name) for name in ("deno.exe", "deno"))
    return next((item for item in candidates if item and Path(item).is_file()), None)


def output_template(output_dir: Path, service: str) -> str:
    destination = output_dir.expanduser().resolve() / service.lower()
    destination.mkdir(parents=True, exist_ok=True)
    return str(destination / "%(title).180B [%(id)s].%(ext)s")


def progress_hook(ui: UI):
    last_percent = {"value": ""}

    def hook(status: dict) -> None:
        if status.get("status") == "downloading":
            percent = str(status.get("_percent_str", "")).strip()
            if percent and percent != last_percent["value"]:
                speed = str(status.get("_speed_str", "?B/s")).strip()
                eta = str(status.get("_eta_str", "?" )).strip()
                print(f"\r [>] {percent:>7}  {speed:>12}  ETA {eta:<8}", end="", flush=True)
                last_percent["value"] = percent
        elif status.get("status") == "finished":
            print("\r", end="")
            ui.ok("転送完了。後処理を実行しています。")

    return hook


def ydl_options(url: str, output_dir: Path, ui: UI, quiet: bool = False) -> dict:
    service = detect_service(url)
    ffmpeg = find_ffmpeg()
    # Without FFmpeg choose the best already-combined stream. This keeps the app
    # functional on clean Windows/macOS/Linux machines instead of failing at merge.
    video_format = "bestvideo*+bestaudio/best" if ffmpeg else "best[ext=mp4]/best"
    options = {
        "format": video_format,
        "outtmpl": output_template(output_dir, service),
        "windowsfilenames": sys.platform == "win32",
        "noplaylist": True,
        "progress_hooks": [] if quiet else [progress_hook(ui)],
        "quiet": quiet,
        "no_warnings": quiet,
    }
    deno = find_deno()
    if service == "YouTube" and deno:
        options["js_runtimes"] = {"deno": {"path": deno}}
    if ffmpeg:
        options.update({"ffmpeg_location": ffmpeg, "merge_output_format": "mp4"})
    return options


def list_formats(url: str, ui: UI | None = None) -> bool:
    ui = ui or UI()
    if not is_web_url(url):
        ui.error("有効な http(s) URL を指定してください。")
        return False
    ui.info(f"利用可能な形式を照会: {detect_service(url)}")
    try:
        with yt_dlp.YoutubeDL({"listformats": True}) as ydl:
            ydl.download([url])
        return True
    except yt_dlp.utils.DownloadError as exc:
        ui.error(f"形式を取得できません: {exc}")
        return False


def download_video(url: str, output_dir: Path | str = Path("downloads"), ui: UI | None = None) -> bool:
    ui = ui or UI()
    if not is_web_url(url):
        ui.error("有効な http(s) URL を指定してください。")
        return False

    service = detect_service(url)
    ffmpeg = find_ffmpeg()
    ui.info(f"TARGET   {service}  {url}")
    ui.info(f"OUTPUT   {(Path(output_dir).expanduser().resolve() / service.lower())}")
    if not ffmpeg:
        ui.warn("FFmpeg未検出: 結合不要な最高品質を選択します。")
    if service == "YouTube" and not find_deno():
        ui.warn("Deno未検出: 通常は続行できますが、一部動画では形式が制限されます。")

    try:
        with yt_dlp.YoutubeDL(ydl_options(url, Path(output_dir), ui)) as ydl:
            error_code = ydl.download([url])
        if error_code:
            ui.error(f"ダウンロードに失敗しました (code: {error_code})")
            return False
        ui.ok("保存が完了しました。")
        return True
    except yt_dlp.utils.DownloadError as exc:
        ui.error(f"ダウンロードエラー: {exc}")
        return False
    except (OSError, ValueError) as exc:
        ui.error(f"ファイル操作エラー: {exc}")
        return False


def interactive(ui: UI, output_dir: Path) -> int:
    ui.banner()
    ui.warn("自分が権利を保有するか、保存の許諾を得たメディアにのみ使用してください。")
    ui.info("URLを貼り付けてください。空欄で終了します。")
    while True:
        try:
            url = input("\n raven > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not url:
            ui.info("セッションを終了します。")
            return 0
        download_video(url, output_dir, ui)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RavenFetch - 権利を保有するメディアの個人用取得ツール")
    parser.add_argument("target", nargs="?", help="動画ページのURL")
    parser.add_argument("--url", dest="legacy_url", help=argparse.SUPPRESS)
    parser.add_argument("-o", "--output", type=Path, default=Path("downloads"), help="保存先 (既定: ./downloads)")
    parser.add_argument("-F", "--list-formats", action="store_true", help="利用可能な形式を一覧表示")
    parser.add_argument("--no-color", action="store_true", help="ANSIカラーを無効化")
    parser.add_argument("--check-update", action="store_true", help="GitHub Releasesの更新を今すぐ確認")
    parser.add_argument("--no-update-check", action="store_true", help="起動時の更新確認を省略")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    ui = UI(color=not args.no_color)
    if args.check_update:
        check_for_update(ui, force=True)
        return 0
    if not args.no_update_check and not (args.target or args.legacy_url):
        if check_for_update(ui):
            return 0
    url = args.target or args.legacy_url
    if not url:
        return interactive(ui, args.output)
    ui.banner()
    success = list_formats(url, ui) if args.list_formats else download_video(url, args.output, ui)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
