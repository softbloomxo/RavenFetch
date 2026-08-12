# RavenFetch

[日本語](README.md) | [English](README.en.md)

RavenFetchは、`yt-dlp`を利用した学習用のシンプルなメディア取得ツールです。
自分で作成したメディア、自分が権利を保有するメディア、または保存の許諾を得たメディアのみを対象としています。

> [!IMPORTANT]
> RavenFetchは、法的に保存できるコンテンツにのみ使用してください。著作権法と各サービスの最新の利用規約に従う責任は利用者にあります。RavenFetchはDRM回避機能を含まず、各メディアサービスの公式製品や提携製品ではありません。

## Windowsポータブル版

1. [GitHub Releases](https://github.com/softbloomxo/RavenFetch/releases/latest)から`RavenFetch-Windows-x64.zip`をダウンロードします。
2. ZIP全体を書き込み可能なフォルダーへ展開します。
3. `RavenFetch.exe`を実行します。
4. 保存が許可されたメディURLを貼り付け、Enterキーを押します。

`RavenFetch.exe`、`deno.exe`、`ffmpeg.exe`、`ffprobe.exe`は同じフォルダーに置いてください。既定の保存先は`downloads/`です。

## 自動更新

対話モードの起動時に、GitHub Releasesを最大1日に1回確認します。新版がある場合は、確認後にインストールします。

```powershell
RavenFetch.exe --check-update
RavenFetch.exe --no-update-check
```

## コマンドライン例

```powershell
RavenFetch.exe "https://example.com/your-permitted-media"
RavenFetch.exe -o "D:\Videos" "URL"
RavenFetch.exe -F "URL"
```

## 開発

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python downloader.py
```

`v0.1.1`のようなタグをpushすると、GitHub ActionsがWindows版を自動ビルドし、ポータブルZIPをGitHub Releasesへ公開します。

バージョン更新時は、`downloader.py`の`APP_VERSION`を変更し、同じ番号の`vX.Y.Z`タグを作成してください。

## ライセンス

RavenFetchのソースコードは[MIT License](LICENSE)で公開しています。同梱コンポーネントにはそれぞれのライセンスが適用されます。詳細は[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)を参照してください。

