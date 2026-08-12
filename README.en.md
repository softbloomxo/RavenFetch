# RavenFetch

[Japanese](README.md) | [English](README.en.md)

RavenFetch is a compact educational media fetcher for Windows powered by
`yt-dlp`. The release contains just one file: `RavenFetch.exe`.

> [!IMPORTANT]
> Use RavenFetch only for media that you created, own, or have explicit
> permission to save. You are responsible for complying with copyright law and
> each service's current terms. RavenFetch does not circumvent DRM and is not
> affiliated with or endorsed by any media service.

## Usage

1. Download `RavenFetch.exe` from the [latest release](https://github.com/softbloomxo/RavenFetch/releases/latest).
2. Place it in a writable folder and run it.
3. Paste the URL of permitted media and press Enter.

FFmpeg and Deno are obtained from their official GitHub Releases only when
first needed. RavenFetch manages them under
`%LOCALAPPDATA%\RavenFetch\runtime`, keeping the application folder clean.

Interactive commands include `:status`, `:setup`, `:update`, `:help`, and
`:quit`. Command-line usage:

```powershell
RavenFetch.exe "https://example.com/your-permitted-media"
RavenFetch.exe -o "D:\Videos" "URL"
RavenFetch.exe -F "URL"
RavenFetch.exe --check-update
RavenFetch.exe --setup-runtime
RavenFetch.exe --runtime-status
RavenFetch.exe --licenses
```

## Automatic management

- RavenFetch checks for its own updates whenever normal interactive mode starts
  and asks before installing.
- Updates replace only `RavenFetch.exe`.
- FFmpeg and Deno are managed separately in the per-user runtime cache.
- GitHub-provided SHA-256 asset digests are verified when available.

## Development and releases

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python downloader.py
```

Update `APP_VERSION` in `downloader.py`, then push the matching `vX.Y.Z` tag.
GitHub Actions validates that the versions match and publishes the single EXE.

## License

RavenFetch source is available under the [MIT License](LICENSE). Third-party
components retain their respective licenses. In the executable, run
`RavenFetch.exe --licenses` to display notices.
