# RavenFetch

[日本語](README.md) | [English](README.en.md)

RavenFetchは、`yt-dlp`を利用した学習用のシンプルなWindows向けメディア取得ツールです。
配布ファイルは`RavenFetch.exe`の1つだけです。

> [!IMPORTANT]
> 自分で作成したメディア、自分が権利を保有するメディア、または保存の許諾を得たメディアにのみ使用してください。著作権法と各サービスの最新の利用規約に従う責任は利用者にあります。RavenFetchはDRM回避機能を含まず、各メディアサービスの公式製品や提携製品ではありません。

## 使い方

1. [GitHub Releases](https://github.com/softbloomxo/RavenFetch/releases/latest)から`RavenFetch.exe`をダウンロードします。
2. 書き込み可能なフォルダーへ置いて実行します。
3. 保存が許可されたメディアURLを貼り付け、Enterキーを押します。

既定の保存先は`downloads/`です。高品質な保存に必要なFFmpegとDenoは、必要になった初回だけ公式GitHub Releasesから自動的に準備されます。

```text
╭──────────────────────────────────────────────────────────╮
│  RAVENFETCH  v0.2.1                                     │
│  PERSONAL MEDIA FETCHER                                 │
╰─────────────────────────────────────────────────────────╯
  保存先   C:\...\downloads
  ●  URLを貼り付けてください。`:help`でコマンドを表示します。

  ❯
```

## 対話コマンド

| コマンド | 動作 |
|---|---|
| URL | メディアを保存 |
| `:status` | FFmpegとDenoの状態を表示 |
| `:setup` | 必要なランタイムを事前準備 |
| `:update` | RavenFetchの更新をすぐ確認 |
| `:help` | ヘルプを表示 |
| `:quit` | 終了 |

## 自動管理

- RavenFetchは対話モード起動時に、新版を最大1日に1回確認します。
- 新版の導入前に利用者へ確認します。
- 更新対象は`RavenFetch.exe`のみです。
- FFmpegとDenoは`%LOCALAPPDATA%\RavenFetch\runtime`で管理されます。
- Releaseと外部ランタイムはSHA-256ダイジェストが提供される場合に検証します。

## コマンドライン

```powershell
RavenFetch.exe "https://example.com/your-permitted-media"
RavenFetch.exe -o "D:\Videos" "URL"
RavenFetch.exe -F "URL"
RavenFetch.exe --check-update
RavenFetch.exe --setup-runtime
RavenFetch.exe --runtime-status
RavenFetch.exe --licenses
```

## 開発とRelease

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python downloader.py
```

`downloader.py`の`APP_VERSION`を更新し、同じ番号の`vX.Y.Z`タグをpushすると、GitHub Actionsが単一の`RavenFetch.exe`を自動公開します。タグとコードのバージョンが異なる場合は、誤配布を避けるためビルドが停止します。

## ライセンス

RavenFetchのソースコードは[MIT License](LICENSE)で公開しています。第三者コンポーネントはそれぞれのライセンスに従います。実行ファイルでは`RavenFetch.exe --licenses`で確認できます。
