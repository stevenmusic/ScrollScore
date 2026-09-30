# ScrollScore 專案規則

## 技術棧
- 單檔 HTML，OpenSheetMusicDisplay (OSMD) 2.0.0 渲染 MusicXML
- Web Audio API 音訊合成；鼓組音色放在本 repo 的 drums/（從 stevenmusic/drum-samples 的 web/ 複製過來；drums/ 讀不到才退回 drum-samples 的 raw.githubusercontent；v3/v4/v5 力度層 × round-robin，16-bit FLAC，v5 峰值統一約 0.5）：大鼓/小鼓/中鼓/落地鼓用 indiedrums DW Collectors Kit + Keplinger Snare（roomy 收音），Hi-Hat/Ride/Crash/邊擊用 THE OPEN SOURCE DRUM KIT（公有領域）；失敗退回 Tone.js 鼓組再退回合成音
- 鼓的力度：鬼音（括號符頭）→ v3、一般 → v4、重音記號 → v5
- 樂器只保留鋼琴、吉他（民謠、古典兩把）、鼓組
- 匯出影片用 canvas.captureStream + MediaRecorder

## Git 流程
- 所有改動完成後直接 commit 並 push 到 main，不用先問我

## 絕不能做的事
- 不要把單檔拆成多檔案，除非我明確要求（PWA部署依賴單檔架構）
- 改 OSMD 版本前先確認 CDN 版本號存在且穩定

## 已知踩過的坑
- OSMD 1.8.4 的 cursor 不會處理反覆記號，2.0.0 版本才支援
- 移調要先設定 osmd.TransposeCalculator 再設 osmd.Sheet.Transpose，否則不會生效
- 匯出影片時 SVG 點陣化要切成4000px的tile，避免iOS canvas尺寸限制
