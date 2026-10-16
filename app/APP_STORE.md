# App Store Connect 填寫內容

## 基本資料

| 欄位 | 內容 |
|---|---|
| 名稱 | ScrollScore |
| 副標題（中文） | 捲動樂譜播放與影片匯出 |
| 副標題（英文） | Scrolling sheet music & video |
| 類別 | 主要：音樂；次要：教育 |
| 年齡分級 | 4+（所有問題都答「無」） |
| 價格 | 自行決定。所有音色授權都允許商用 |
| 隱私權政策網址 | https://stevenmusic.github.io/ScrollScore/privacy.html（push 到 main 後由 GitHub Pages 提供） |
| 支援網址 | https://stevenmusic.github.io/ScrollScore/support.html（使用說明、常見問題、聯絡信箱；審核規則 1.5 要求支援網址上要有聯絡方式） |
| 聯絡信箱 | steventsaimusic@gmail.com |

## App 隱私（App Privacy）

選 **「不收集資料」（Data Not Collected）**。

App 沒有帳號、分析、廣告或追蹤功能。匯入的樂譜和匯出的影片都只存在裝置上，App 版也不連 Google Fonts。

## 描述（中文）

> ScrollScore 把樂譜變成橫向捲動的播放畫面，跟著播放軸一起看譜、聽音樂，還能一鍵匯出成影片分享到 YouTube、Instagram。
>
> ・匯入 MusicXML（.xml / .musicxml / .mxl）與 Guitar Pro（.gp / .gpx / .gp5 / .gp4 / .gp3）樂譜
> ・真實錄音的音色：16 層力度的平台鋼琴、整套錄音室鼓組
> ・自然的演奏：依樂譜的力度記號、圓滑線、踏板演奏，速度也會像真人一樣有快慢
> ・可以調速度、移調、預備拍、標示目前小節
> ・匯出影片：橫式、直式、方形，可加上鍵盤或鼓組動畫、標題與浮水印；音量自動符合 YouTube 標準
> ・內建範例樂譜，打開就能試
> ・完全離線使用，不需要帳號，不收集任何資料

## Description (English)

> ScrollScore turns sheet music into a smooth horizontally scrolling view: follow the playhead, listen, and export a video to share on YouTube or Instagram.
>
> • Import MusicXML (.xml / .musicxml / .mxl) and Guitar Pro (.gp / .gpx / .gp5 / .gp4 / .gp3) files
> • Real recorded instruments: a 16-layer grand piano and a full studio drum kit
> • Natural playback that follows dynamics, slurs and pedal markings, with human-like tempo shaping
> • Tempo, transpose, count-in and current-measure highlight
> • Video export in landscape, portrait or square, with an animated keyboard or drum kit, titles and watermark; loudness matched to YouTube
> • Built-in sample scores to try right away
> • Works fully offline. No account, no data collected

## 關鍵字（100 字元內）

- 中文：`樂譜,五線譜,鋼琴,鼓譜,MusicXML,Guitar Pro,練習,播放,影片,捲動`
- 英文：`sheet music,score,piano,drums,MusicXML,Guitar Pro,practice,playback,video,scroll`

## 給審核員的備註（App Review Information → Notes）

> No account is needed. To try the app without your own files, tap one of the sample buttons on the start screen ("Twinkle", "Ode to Joy", "Rock drums", "Funk drums"), then press Play. To export a video, tap the camera icon at the top (Export Video), choose a format and tap "Start Export"; when it finishes the video is saved to Photos automatically (the app asks for add-only photo access the first time). You can also import any MusicXML or Guitar Pro file from the Files app via the upload button. All processing happens on the device.

## 截圖

需要 iPhone 6.9 吋（1320×2868 或 2868×1320）。有勾選 iPad 支援的話，還要 iPad 13 吋（2064×2752）。建議拍 4～5 張：

1. 鋼琴樂譜播放中，下方是鍵盤，畫面有捲動中的播放軸。
2. 鼓譜播放中，下方是鼓組動畫。
3. 匯出設定：直式／橫式／方形的選擇畫面。
4. 匯出完成的直式影片畫面。
5. 設定面板（速度、移調、空間感）。

## 送審前檢查

- [ ] 在實機上測試：靜音開關打開時有聲音、匯入檔案、匯出影片並存到相簿、旋轉螢幕
- [ ] 隱私權政策、支援網址都打得開（push 到 main 後確認 GitHub Pages 已更新）
- [ ] App 圖示不是 Capacitor 預設圖示（已換成 `assets/icon-1024.png`）
- [ ] 版本號：第一次送審用 1.0 (1)
