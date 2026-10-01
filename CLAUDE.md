# ScrollScore 專案規則

## 技術棧
- 單檔 HTML，OpenSheetMusicDisplay (OSMD) 2.0.0 渲染 MusicXML
- Web Audio API 音訊合成；鼓組音色放在本 repo 的 drums/（從 stevenmusic/drum-samples 的 web/ 複製過來；drums/ 讀不到才退回 drum-samples 的 raw.githubusercontent；v3/v4/v5 力度層 × round-robin，16-bit FLAC，v5 峰值統一約 0.5）：整套鼓全部來自 DRSKit（CC-BY 4.0）同一場錄音，用同一套混音配方（近距麥克風擺位 + 共用 overhead/房間麥克風），左右位置已混在取樣裡、App 不另擺聲像。不要混用不同鼓組的取樣（房間/麥克風不同會聽起來像拼湊的）；失敗退回 Tone.js 鼓組再退回合成音
- 鼓的力度：humanizeDrumHit() 算 0~1 連續力度（鬼音/一般/重音 + 正反拍律動重音 + 隨機），換成 v3/v4/v5 層 + 層內微調；時間是整拍共用 ±4ms + 各肢體 ±1.5ms
- 鼓的整首力度：computeDrumSongDynamics() 算 ev.macro（譜上 pp~fff 與漸強/漸弱髮夾 + 依每小節密度/ride/開放 hi-hat/crash/過門自動估段落大小聲 + 過門漸強 + 緩慢隨機）
- 鼓音量平衡用響度（LUFS）量，不是峰值；鼓的匯流排繞過主輸出的 loudnessComp（那是給鋼琴的），且不壓縮（DRUM_BUS ratio 1），只有主限幅器當安全網——任何壓縮都會把力度差吃掉。鼓因此比鋼琴小聲（約 −21 LUFS），是刻意的取捨
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
