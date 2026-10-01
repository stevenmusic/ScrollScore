# ScrollScore 專案規則

## 技術棧
- 單檔 HTML，OpenSheetMusicDisplay (OSMD) 2.0.0 渲染 MusicXML
- Web Audio API 音訊合成；鼓組音色放在本 repo 的 drums/（從 stevenmusic/drum-samples 的 web/ 複製；drums/ 讀不到才退回 raw.githubusercontent）：Naked Drums（Wilkinson Audio，CC-BY 4.0，商業規格），照原廠 CR 立體聲混音預製成 nk-<鼓件>-L<層>.<rr>.flac，drums/manifest.json 記錄各鼓件力度層與 round-robin。全部力度層都載入；round-robin 依記憶體預算（桌機全載、iOS 160MB、低記憶體 Android 100~220MB）分輪背景補齊。不要混用不同鼓組的取樣
- 鼓的力度照原廠 sfz：s(0~1)×127 = MIDI 力度，依原廠力度分區挑層，音量 = 0.01 + 0.99×(力度/127)²（amp_veltrack 99）；一般擊打 s≈0.72（≈91）、鬼音 0.3、重音 0.95
- humanizeDrumHit() 算 0~1 力度（鬼音/一般/重音 + 正反拍律動重音 + 隨機 + 整首力度 ev.macro）；時間是整拍共用 ±4ms + 各肢體 ±1.5ms
- 鼓的整首力度：computeDrumSongDynamics() 算 ev.macro（譜上 pp~fff 與漸強/漸弱髮夾 + 依每小節密度/ride/開放 hi-hat/crash/過門自動估段落大小聲 + 過門漸強 + 緩慢隨機）
- 鼓的演奏細節：computeDrumPerformance()（肢體分配、AR(1) 連續起伏、越快越輕、重音前後、過門左右手、開放 hi-hat、樂句）放在 n.perf，播放/匯出前依當下速度重算
- 鼓的混音（getDrumBus / DRUM_BUS）：乾聲不壓縮 + 平行壓縮 + 鼓用 plate 殘響（RT60 2.2s，跟著殘響滑桿）+ 輕微 EQ，繞過鋼琴用的 loudnessComp，只有主限幅器當安全網。plate 的雜訊用固定種子，不要用 Math.random
- 鼓音量平衡用響度（LUFS）量，不是峰值；鼓約 −20 LUFS，比鋼琴小聲，是保留力度的取捨
- MusicXML midi-unpitched 是 1 起算、OSMD 不會減 1，normalizeDrumKey 一律減 1
- 鋼琴音色放在本 repo 的 piano/：Accurate-Salamander Grand Piano V6.2（Salamander V3 by Alexander Holm，CC-BY 3.0），30 個取樣音 × 16 層力度 + 放鍵弦共鳴（harmL/harmS）+ 放鍵機械聲（rel）+ 踏板聲，48k/16-bit FLAC + piano/manifest.json;讀不到才退回 raw.githubusercontent，manifest 都讀不到才退回 Tone.js 單層鋼琴
- 鋼琴取樣已做過「單聲道相容」處理（AB 立體聲對某些音加成單聲道會抵消 10dB）：逐 STFT 頻格保留能量的 mid、side×0.45、低音左高音右 ±0.25，再還原原本響度;重建取樣要用同一套處理（piano/build/pf_build.py、stereo_fix.py）
- 鋼琴力度照 Accurate-Salamander V6.2：各層錄音已校正成一樣大聲，依力度分區挑層（VEL_16），音量 = 0.015 + 0.985×（力度/127）²（amp_veltrack 98.5）;PIANO_GAIN 1.4（整首約 −11 LUFS、不削波）
- computePianoDynamics() 算每個音的 n.pvel(1~127)與 n.pdt(和弦內聲部最多晚 7ms):力度記號/髮夾(sf/sfz 只影響當下)、旋律較重、內聲部與左手較輕、拍子輕重、旋律起伏、4 小節樂句、重音、左右手 AR(1) 起伏 + 隨機
- 鋼琴只載入樂譜用到的（音 × 力度層）;記憶體預算（桌機 1.2GB、iOS 220MB、4GB Android 280MB、2GB Android 120MB，共鳴/機械聲也算在內）不夠時依序：截短到需要的長度 → 單聲道 → 合併最少用到的層。制音器落下時加 harm/rel（音量用 manifest 的 d 換算成原廠 V3 的相對音量，依按住時間 rt_decay 衰減）;F#6（MIDI 89）以上沒有制音器
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
