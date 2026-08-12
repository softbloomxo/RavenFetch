RAVENFETCH
==========

対応OS: Windows 10/11 x64

使い方
------
1. RavenFetch.exe をダブルクリックします。
2. TVer または YouTube のURLを貼り付け、Enterキーを押します。
3. 動画は downloads\tver または downloads\youtube に保存されます。

コマンドライン例
----------------
RavenFetch.exe "URL"
RavenFetch.exe -o "D:\Videos" "URL"
RavenFetch.exe -F "URL"

注意
----
このフォルダ内の deno.exe、ffmpeg.exe、ffprobe.exe は移動・削除せず、
RavenFetch.exe と同じ場所に置いてください。
本ツールは学習・技術検証用です。自分が権利を保有するか、保存の許諾を得た
コンテンツにのみ使用してください。著作権法と各サービスの最新の利用規約に従う
責任は利用者にあります。本ツールは各メディアサービスの公式製品ではありません。

同梱コンポーネント
------------------
Deno: https://github.com/denoland/deno (MIT License)
FFmpeg build: https://github.com/yt-dlp/FFmpeg-Builds (GPLv3 build)
yt-dlp: https://github.com/yt-dlp/yt-dlp (The Unlicense and bundled third-party licenses)
