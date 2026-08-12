# RavenFetch

RavenFetch is a small, educational Python front end for `yt-dlp`. It is intended
for downloading media that you own, created yourself, or have explicit
permission to download.

> [!IMPORTANT]
> Use RavenFetch only for content you are legally entitled to save. You are
> responsible for complying with copyright law and the current terms of each
> service. RavenFetch does not include DRM circumvention and is not affiliated
> with or endorsed by any media service.

## Windows portable edition

1. Download `RavenFetch-Windows-x64.zip` from the latest GitHub Release.
2. Extract the complete ZIP into a writable folder.
3. Run `RavenFetch.exe`.
4. Paste a permitted media URL and press Enter.

Keep `RavenFetch.exe`, `deno.exe`, `ffmpeg.exe`, and `ffprobe.exe` together.
Downloads are saved below `downloads/` by default.

RavenFetch checks GitHub Releases at most once every 24 hours when interactive
mode starts. It asks before installing an update. You can also use:

```powershell
RavenFetch.exe --check-update
RavenFetch.exe --no-update-check
```

## Command-line examples

```powershell
RavenFetch.exe "https://example.com/your-permitted-media"
RavenFetch.exe -o "D:\Videos" "URL"
RavenFetch.exe -F "URL"
```

## Development

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python downloader.py
```

Pushing a tag such as `v0.1.0` runs the GitHub Actions release workflow. It
builds the Windows executable, obtains Deno and the GPLv3 FFmpeg build from
their upstream release pages, and publishes the portable ZIP to GitHub
Releases.

When changing the version, update `APP_VERSION` in `downloader.py`, commit it,
and create a matching `vX.Y.Z` tag.

## License

RavenFetch source code is available under the [MIT License](LICENSE). Bundled
dependencies retain their respective licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

