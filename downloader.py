"""RavenFetch: a single-file personal media fetcher for Windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import yt_dlp
except ImportError as exc:
    raise SystemExit("yt-dlp が見つかりません。'python -m pip install yt-dlp' を実行してください。") from exc


APP_NAME = "RavenFetch"
APP_VERSION = "0.2.2"
GITHUB_REPOSITORY = "softbloomxo/RavenFetch"
UPDATE_ASSET_NAME = "RavenFetch.exe"
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"

RUNTIME_RELEASES = {
    "ffmpeg": {
        "repository": "yt-dlp/FFmpeg-Builds",
        "asset": "ffmpeg-master-latest-win64-gpl.zip",
        "executables": ("ffmpeg.exe", "ffprobe.exe"),
    },
    "deno": {
        "repository": "denoland/deno",
        "asset": "deno-x86_64-pc-windows-msvc.zip",
        "executables": ("deno.exe",),
    },
}

SUPPORTED_HOSTS = {
    "tver.jp": "TVer",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
}

LEGAL_NOTICE = """RavenFetch is distributed under the MIT License.
Copyright (c) 2026 softbloomxo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Third-party projects:
- yt-dlp: https://github.com/yt-dlp/yt-dlp (The Unlicense and bundled licenses)
- Deno: https://github.com/denoland/deno (MIT License)
- FFmpeg build: https://github.com/yt-dlp/FFmpeg-Builds (GPLv3 build)
- FFmpeg upstream: https://ffmpeg.org/

RavenFetch is not affiliated with or endorsed by these projects or by any
media service. Each component remains subject to its own license.
"""


class Palette:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


class UI:
    """Dependency-free terminal interface designed for modern Windows."""

    def __init__(self, color: bool = True) -> None:
        self.color = color and sys.stdout.isatty() and "NO_COLOR" not in os.environ
        self._progress_visible = False

    def paint(self, color: str, text: str) -> str:
        return f"{color}{text}{Palette.RESET}" if self.color else text

    def clear_progress(self) -> None:
        if self._progress_visible:
            print("\r\033[2K", end="", flush=True)
            self._progress_visible = False

    def box_row(self, content: str, width: int) -> None:
        visible = re.sub(r"\x1b\[[0-9;]*m", "", content)
        padding = " " * max(0, width - len(visible))
        print(self.paint(Palette.CYAN, "│") + content + padding + self.paint(Palette.CYAN, "│"))

    def banner(self, output_dir: Path | None = None) -> None:
        logo = self.paint(Palette.CYAN + Palette.BOLD, "RAVEN") + self.paint(Palette.WHITE + Palette.BOLD, "FETCH")
        version = self.paint(Palette.GRAY, f"v{APP_VERSION}")
        width = 58
        print()
        print(self.paint(Palette.CYAN, "╭" + "─" * width + "╮"))
        self.box_row(f"  {logo}  {version}", width)
        self.box_row(self.paint(Palette.GRAY, "  PERSONAL MEDIA FETCHER"), width)
        print(self.paint(Palette.CYAN, "╰" + "─" * width + "╯"))
        if output_dir is not None:
            self.key_value("保存先", str(output_dir.expanduser().resolve()))

    def key_value(self, key: str, value: str) -> None:
        print(f"  {self.paint(Palette.GRAY, key.ljust(8))} {self.paint(Palette.WHITE, value)}")

    def message(self, icon: str, message: str, color: str) -> None:
        self.clear_progress()
        print(f"  {self.paint(color + Palette.BOLD, icon)}  {message}")

    def info(self, message: str) -> None:
        self.message("●", message, Palette.CYAN)

    def ok(self, message: str) -> None:
        self.message("✓", message, Palette.GREEN)

    def warn(self, message: str) -> None:
        self.message("!", message, Palette.YELLOW)

    def error(self, message: str) -> None:
        self.message("×", message, Palette.RED)

    def divider(self) -> None:
        self.clear_progress()
        print(self.paint(Palette.GRAY, "  " + "─" * 58))

    def prompt(self) -> str:
        return input(f"\n  {self.paint(Palette.CYAN + Palette.BOLD, '❯')} ").strip()

    def progress(self, percent: float, speed: str, eta: str) -> None:
        width = 28
        value = min(100.0, max(0.0, percent))
        filled = round(width * value / 100)
        bar = self.paint(Palette.CYAN, "█" * filled) + self.paint(Palette.GRAY, "░" * (width - filled))
        line = f"  {bar} {value:5.1f}%  {speed:>11}  ETA {eta:<7}"
        print(f"\r{line}", end="", flush=True)
        self._progress_visible = True

    def help(self) -> None:
        self.divider()
        print(self.paint(Palette.WHITE + Palette.BOLD, "  COMMANDS"))
        commands = (
            ("URL", "許可されたメディアを保存"),
            (":status", "FFmpeg / Deno の状態を表示"),
            (":setup", "必要なランタイムを自動準備"),
            (":update", "RavenFetchの更新を確認"),
            (":help", "このヘルプを表示"),
            (":quit", "終了"),
        )
        for command, description in commands:
            print(f"  {self.paint(Palette.CYAN, command.ljust(12))} {description}")
        self.divider()


def configure_console() -> None:
    """Enable UTF-8 and ANSI output without affecting non-Windows platforms."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    if sys.platform == "win32":
        os.system("")
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(f"{APP_NAME} v{APP_VERSION}")
        except (AttributeError, OSError):
            pass


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def state_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    return base / APP_NAME


def runtime_directory() -> Path:
    return state_directory() / "runtime"


def github_latest_release(repository: str, timeout: int = 10) -> dict:
    request = Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def release_asset(release: dict, name: str) -> dict | None:
    return next((asset for asset in release.get("assets", []) if asset.get("name") == name), None)


def verified_download(asset: dict, destination: Path, ui: UI | None = None) -> Path:
    request = Request(asset["browser_download_url"], headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(request, timeout=120) as response, destination.open("wb") as output:
        total = int(response.headers.get("Content-Length", 0))
        received = 0
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
            received += len(chunk)
            if ui and total:
                ui.progress(received * 100 / total, f"{received // 1048576} MB", "--")
    if ui:
        ui.clear_progress()

    expected = str(asset.get("digest") or "")
    if expected.startswith("sha256:") and digest.hexdigest().lower() != expected.removeprefix("sha256:").lower():
        destination.unlink(missing_ok=True)
        raise ValueError("SHA-256検証に失敗しました。")
    return destination


def version_key(version: str) -> tuple[int, ...]:
    numbers: list[int] = []
    for part in version.lstrip("vV").split("."):
        match = re.match(r"\d+", part)
        numbers.append(int(match.group(0)) if match else 0)
    return tuple(numbers)


def launch_executable_update(new_executable: Path) -> None:
    helper = Path(tempfile.gettempdir()) / f"{APP_NAME}-update-{os.getpid()}.ps1"
    target = Path(sys.executable).resolve()
    helper.write_text(
        "param([int]$RavenPid,[string]$Source,[string]$Target)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "Wait-Process -Id $RavenPid -ErrorAction SilentlyContinue\n"
        "Move-Item -LiteralPath $Source -Destination $Target -Force\n"
        "Start-Process -FilePath $Target\n"
        "Remove-Item -LiteralPath $PSCommandPath -Force\n",
        encoding="utf-8-sig",
    )
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
            "-Source",
            str(new_executable),
            "-Target",
            str(target),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


def check_for_update(ui: UI, force: bool = False) -> bool:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        if force:
            ui.warn("自動更新はWindows版RavenFetch.exeで利用できます。")
        return False

    try:
        release = github_latest_release(GITHUB_REPOSITORY)
        latest = str(release.get("tag_name", "")).lstrip("vV")
        if not latest or version_key(latest) <= version_key(APP_VERSION):
            if force:
                ui.ok(f"最新版です（v{APP_VERSION}）。")
            return False

        asset = release_asset(release, UPDATE_ASSET_NAME)
        if not asset:
            raise ValueError(f"Releaseに{UPDATE_ASSET_NAME}がありません。")
        ui.info(f"新しいバージョン v{latest} を利用できます。")
        answer = input("  更新して再起動しますか？ [Y/n] ").strip().lower()
        if answer not in {"", "y", "yes"}:
            return False

        destination = Path(tempfile.gettempdir()) / f"{APP_NAME}-{latest}.exe"
        ui.info("新版をダウンロードしています…")
        verified_download(asset, destination, ui)
        ui.ok("ダウンロードと検証が完了しました。")
        launch_executable_update(destination)
        ui.info("アプリを終了し、新版へ切り替えます。")
        return True
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if force:
            ui.warn(f"更新を確認できません: {exc}")
        return False


def tool_candidates(name: str) -> list[Path]:
    candidates: list[Path] = []
    system_tool = shutil.which(name)
    if system_tool:
        candidates.append(Path(system_tool))
    candidates.extend((app_directory() / name, runtime_directory() / name))
    return candidates


def find_tool(name: str) -> str | None:
    return next((str(path) for path in tool_candidates(name) if path.is_file()), None)


def write_runtime_notice() -> None:
    path = runtime_directory() / "THIRD_PARTY_NOTICES.txt"
    path.write_text(LEGAL_NOTICE, encoding="utf-8")


def install_runtime_component(component: str, ui: UI) -> bool:
    config = RUNTIME_RELEASES[component]
    label = "FFmpeg" if component == "ffmpeg" else "Deno"
    ui.info(f"{label}を初回セットアップしています…")
    archive = Path(tempfile.gettempdir()) / config["asset"]
    try:
        release = github_latest_release(config["repository"], timeout=15)
        asset = release_asset(release, config["asset"])
        if not asset:
            raise ValueError(f"{config['asset']}が見つかりません。")
        verified_download(asset, archive, ui)
        destination = runtime_directory()
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            members = {Path(name).name.lower(): name for name in package.namelist() if not name.endswith("/")}
            for executable in config["executables"]:
                member = members.get(executable.lower())
                if not member:
                    raise ValueError(f"アーカイブに{executable}がありません。")
                temporary = destination / f"{executable}.tmp"
                with package.open(member) as source, temporary.open("wb") as target:
                    shutil.copyfileobj(source, target)
                os.replace(temporary, destination / executable)
        write_runtime_notice()
        ui.ok(f"{label}の準備が完了しました。")
        return True
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        ui.warn(f"{label}を準備できませんでした: {exc}")
        return False
    finally:
        archive.unlink(missing_ok=True)


def ensure_runtime(service: str, ui: UI) -> tuple[str | None, str | None]:
    ffmpeg = find_tool("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    deno = find_tool("deno.exe" if sys.platform == "win32" else "deno")
    if sys.platform == "win32" and not ffmpeg:
        install_runtime_component("ffmpeg", ui)
        ffmpeg = find_tool("ffmpeg.exe")
    if sys.platform == "win32" and service == "YouTube" and not deno:
        install_runtime_component("deno", ui)
        deno = find_tool("deno.exe")
    return ffmpeg, deno


def show_runtime_status(ui: UI) -> None:
    ui.divider()
    ui.key_value("FFmpeg", find_tool("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg") or "未準備")
    ui.key_value("Deno", find_tool("deno.exe" if sys.platform == "win32" else "deno") or "未準備")
    ui.key_value("キャッシュ", str(runtime_directory()))
    ui.divider()


def setup_all_runtimes(ui: UI) -> bool:
    results = []
    for component, executable in (("ffmpeg", "ffmpeg.exe"), ("deno", "deno.exe")):
        if find_tool(executable):
            ui.ok(f"{executable}は準備済みです。")
            results.append(True)
        else:
            results.append(install_runtime_component(component, ui))
    return all(results)


def detect_service(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    for domain, service in SUPPORTED_HOSTS.items():
        if host == domain or host.endswith("." + domain):
            return service
    return "Other"


def is_web_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def output_template(output_dir: Path, service: str) -> str:
    destination = output_dir.expanduser().resolve() / service.lower()
    destination.mkdir(parents=True, exist_ok=True)
    return str(destination / "%(title).180B [%(id)s].%(ext)s")


def progress_hook(ui: UI):
    def hook(status: dict) -> None:
        if status.get("status") == "downloading":
            raw_percent = str(status.get("_percent_str", "0")).replace("%", "").strip()
            try:
                percent = float(re.sub(r"\x1b\[[0-9;]*m", "", raw_percent))
            except ValueError:
                percent = 0.0
            speed = str(status.get("_speed_str", "--")).strip()
            eta = str(status.get("_eta_str", "--")).strip()
            ui.progress(percent, speed, eta)
        elif status.get("status") == "finished":
            ui.clear_progress()
            ui.ok("転送完了。メディアを仕上げています…")

    return hook


def ydl_options(url: str, output_dir: Path, ui: UI, quiet: bool = False) -> dict:
    service = detect_service(url)
    ffmpeg, deno = ensure_runtime(service, ui)
    options = {
        "format": "bestvideo*+bestaudio/best" if ffmpeg else "best[ext=mp4]/best",
        "outtmpl": output_template(output_dir, service),
        "windowsfilenames": sys.platform == "win32",
        "noplaylist": True,
        "progress_hooks": [] if quiet else [progress_hook(ui)],
        "quiet": quiet,
        "no_warnings": quiet,
    }
    if service == "YouTube" and deno:
        options["js_runtimes"] = {"deno": {"path": deno}}
    if ffmpeg:
        options.update({"ffmpeg_location": ffmpeg, "merge_output_format": "mp4"})
    return options


def list_formats(url: str, ui: UI) -> bool:
    if not is_web_url(url):
        ui.error("有効なhttp(s) URLを指定してください。")
        return False
    service = detect_service(url)
    ensure_runtime(service, ui)
    ui.info(f"{service}の形式を照会しています…")
    try:
        with yt_dlp.YoutubeDL({"listformats": True}) as ydl:
            ydl.download([url])
        return True
    except yt_dlp.utils.DownloadError as exc:
        ui.error(f"形式を取得できません: {exc}")
        return False


def download_video(url: str, output_dir: Path, ui: UI) -> bool:
    if not is_web_url(url):
        ui.error("有効なhttp(s) URLを指定してください。")
        return False

    service = detect_service(url)
    destination = output_dir.expanduser().resolve() / service.lower()
    ui.divider()
    ui.key_value("サービス", service)
    ui.key_value("保存先", str(destination))
    ui.info("メディア情報を取得しています…")
    try:
        with yt_dlp.YoutubeDL(ydl_options(url, output_dir, ui)) as ydl:
            error_code = ydl.download([url])
        if error_code:
            ui.error(f"保存に失敗しました（code: {error_code}）。")
            return False
        ui.ok("保存が完了しました。")
        return True
    except yt_dlp.utils.DownloadError as exc:
        ui.error(f"ダウンロードエラー: {exc}")
        return False
    except (OSError, ValueError) as exc:
        ui.error(f"ファイル操作エラー: {exc}")
        return False


def interactive(ui: UI, output_dir: Path, check_update: bool = True) -> int:
    ui.banner(output_dir)
    if check_update:
        ui.info("起動時の更新を確認しています…")
        if check_for_update(ui, force=True):
            return 0
    ui.warn("権利を保有するか、保存の許諾を得たメディアにのみ使用してください。")
    ui.info("URLを貼り付けてください。`:help`でコマンドを表示します。")
    while True:
        try:
            command = ui.prompt()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not command:
            continue
        normalized = command.lower()
        if normalized in {":q", ":quit", "quit", "exit"}:
            ui.info("セッションを終了します。")
            return 0
        if normalized in {":h", ":help", "help"}:
            ui.help()
        elif normalized == ":status":
            show_runtime_status(ui)
        elif normalized == ":setup":
            setup_all_runtimes(ui)
        elif normalized == ":update":
            if check_for_update(ui, force=True):
                return 0
        else:
            download_video(command, output_dir, ui)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RavenFetch - 権利を保有するメディアの個人用取得ツール")
    parser.add_argument("target", nargs="?", help="メディアページのURL")
    parser.add_argument("--url", dest="legacy_url", help=argparse.SUPPRESS)
    parser.add_argument("-o", "--output", type=Path, default=Path("downloads"), help="保存先（既定: ./downloads）")
    parser.add_argument("-F", "--list-formats", action="store_true", help="利用可能な形式を一覧表示")
    parser.add_argument("--setup-runtime", action="store_true", help="FFmpegとDenoを自動準備")
    parser.add_argument("--runtime-status", action="store_true", help="ランタイムの状態を表示")
    parser.add_argument("--check-update", action="store_true", help="GitHub Releasesの更新を今すぐ確認")
    parser.add_argument("--no-update-check", action="store_true", help="起動時の更新確認を省略")
    parser.add_argument("--no-color", action="store_true", help="ANSIカラーを無効化")
    parser.add_argument("--licenses", action="store_true", help="ライセンスと第三者表示を出力")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    ui = UI(color=not args.no_color)
    if args.licenses:
        print(LEGAL_NOTICE)
        return 0
    if args.setup_runtime:
        ui.banner()
        return 0 if setup_all_runtimes(ui) else 1
    if args.runtime_status:
        ui.banner()
        show_runtime_status(ui)
        return 0
    if args.check_update:
        ui.banner()
        check_for_update(ui, force=True)
        return 0

    url = args.target or args.legacy_url
    if not url:
        return interactive(ui, args.output, check_update=not args.no_update_check)
    ui.banner(args.output)
    success = list_formats(url, ui) if args.list_formats else download_video(url, args.output, ui)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
