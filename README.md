# ScrollScore 宣傳影片專案（promo-video 分支）

這個分支只放宣傳影片的製作檔，跟 app 本身（main 分支的 index.html）無關。

## 影片
- `video/comp.html` + `video/comp.js`：11 段 motion graphics（總長 100.03 秒），`window.setTime(t)` 是純時間函數。
- `video/render.mjs`：Playwright 開 comp.html（1920×1080、deviceScaleFactor 2 → 3840×2160），逐格截圖 pipe 給 ffmpeg。
  - `node render.mjs still <t1,t2,...> <dsf>` 輸出靜態畫面；`node render.mjs seg <f0> <f1> <out.mp4>` 輸出某段影格（30fps）。
  - 暫存資料夾路徑、ffmpeg 路徑用環境變數 `SP`、`FF` 指定（例如 `SP=/path/to/sp node render.mjs ...`）。
  - 需要本機 http server（port 8767），根目錄底下要有 `app/`（指向 ScrollScore repo）、`video/`、`sp/`（放 vid_export_*.png、樂譜）。
  - OSMD 2.0.0、jszip 3.10.1 從 npm 下載後由 render.mjs 本機供應；鋼琴/鼓的 FLAC 會被擋掉（只要畫面）。
- `video/fonts/` 沒放進來（29MB），從 Google Fonts 重新下載：Noto Sans TC、Noto Serif TC、Inter（可變字重 TTF），檔名 NotoSansTC.ttf / NotoSerifTC.ttf / Inter.ttf。
- `video/music.mp3`：Mixkit #173〈Better Times are Coming〉（可商用、免標示）。混音：開頭 0.3 秒淡入、98.3 秒起 1.7 秒淡出。
- `video/vidprev.mjs`：產生匯出畫面示意圖 vid_export_16x9 / 9x16 / 1x1.png（在 sp/ 底下執行；畫面直接取自 app，app 改版後要重新產生，例如鼓譜匯出純白底、半透明播放軸）。
- 輸出：4K H.264 原檔約 100MB；傳送版用 HEVC（libx265 crf 24, hvc1）約 21MB，另有 1080p 約 16MB。
- 結尾比照 HarmonyMap：ScrollScore（Scroll 象牙白、Score 金色）、捲動樂譜播放器、email、© 2026 Steven Tsai，不放網址。
- 開頭五線譜音符符桿依樂理：中線以上（含中線）朝下畫在左側、以下朝上畫在右側，長 3.5 個間距。

## 樂譜
- `scores/groove_dyn2.musicxml`：影片用的鼓譜（標準兩聲部：手 voice 1 符桿朝上、大鼓 voice 2 朝下、重音在上方、終止線）。由 `tools/fix_drum.py` 從舊的單聲部測試檔轉換而來。
- `scores/mozart_k545_movement1_exposition.mxl`、`scores/bach_bwv846.mxl`：鋼琴示範。

## 吉他音源調查工具（tools/guitar）
- `zipls.py <url> <out.json>`：用 HTTP Range 讀遠端 zip 的目錄（不用下載整個檔案）。
- `zipget.py <url> <index.json> <regex> <outdir>`：只抽出符合的檔案。
- `measure.py` / `demo.py`：取樣的底噪、明亮度、延音、音準分析，與試聽檔產生。

## 改版紀錄
- 2026-10-02：第 03 段「真實樂器音色」拿掉民謠吉他、古典吉他（重新找過仍沒有每個音都有錄音、可商用、品質夠好的木吉他音色；app 裡吉他也維持停用），只留鋼琴、鼓組兩張卡。依 app 最新版重新產生匯出示意圖並重新輸出影片（播放軸半透明、鼓譜匯出純白底、播放軸長度依最高最低音）。
- 2026-10-02：逐張檢查影片截圖的記譜。巴哈 BWV846 原檔左手兩個聲部符桿都寫朝下、音符擠在一起，修正 `scores/bach_bwv846.mxl`：左手較高的聲部朝上、較低的朝下，上聲部的十六分休止符放在上方；1:1 匯出示意改從第 24 小節附近（77 秒）開始（開頭的 E4 在低音譜號上方兩條加線，OSMD 畫朝上符桿會斷開）。
