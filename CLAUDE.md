# ScrollScore 專案規則

## 技術棧
- 單檔 HTML，OpenSheetMusicDisplay (OSMD) 2.0.0 渲染 MusicXML
- Web Audio API 音訊合成；鼓組音色放在本 repo 的 drums/（從 stevenmusic/drum-samples 的 web/ 複製過來；drums/ 讀不到才退回 drum-samples 的 raw.githubusercontent；v3/v4/v5 力度層 × round-robin，16-bit FLAC，v5 峰值統一約 0.5）：大鼓/小鼓/中鼓/落地鼓用 indiedrums DW Collectors Kit + Keplinger Snare（roomy 收音），Hi-Hat 用 DRSKit（CC-BY 4.0，多麥克風混成立體聲），Ride/Crash/邊擊用 THE OPEN SOURCE DRUM KIT（公有領域）；失敗退回 Tone.js 鼓組再退回合成音
- 鼓的力度：humanizeDrumHit() 算 0~1 連續力度（鬼音/一般/重音 + 正反拍律動重音 + 隨機），換成 v3/v4/v5 層 + 層內微調；時間是整拍共用 ±4ms + 各肢體 ±1.5ms
- 鼓音量平衡用響度（LUFS）量，不是峰值；drum bus 壓縮器只當峰值安全網（一般設定會把力度差壓平）
- MusicXML midi-unpitched 是 1 起算、OSMD 不會減 1，normalizeDrumKey 一律減 1
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
