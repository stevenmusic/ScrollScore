# ScrollScore 音訊/記譜測試工具

不屬於 App 本體(App 維持單檔 index.html),只給開發時量測用。

```
cd tools/audiotest && npm i          # playwright 1.56.1、opensheetmusicdisplay 2.0.0、jszip、@coderline/alphatab 1.8.4(雲端環境 jsdelivr 被擋,改從 npm 拿)
pip install numpy scipy soundfile pyloudnorm
```

| 檔案 | 用途 |
|---|---|
| `render.mjs` | 用 OfflineAudioContext 離線算出 App 的實際輸出(跟網頁播放同一條音訊路徑),存 32-bit float WAV。`--taps` 多存 masterBus(限幅器之前)兩聲道;`--root` 指定要測的版本目錄(A/B 比較);`--set '{"MASTER.makeup":1.8}'` 在載入樂譜前改設定物件;`--sec` 最長秒數;`--inst`、`--tempo`、`--reverb`;`--taps --tapsrc verb` 3、4 聲道改存鋼琴殘響回送 |
| `batch.sh` | 平行(3 個)渲染一個目錄的樂譜並跑 analyze.py |
| `analyze.py` | 整體響度 LUFS、真峰值(4 倍超取樣)、LRA、短期響度最大值、−3dBFS 以上時間比例、左右相關性;有 taps 時加上限幅器前的響度/峰值 |
| `ladder.py` + `gen_piano_dyn.py` | 鋼琴力度階梯(pp p mp mf f ff 各 2 小節):量整條鏈路最後留下多少大小聲差 |
| `limiter_test.mjs` + `limiter_tp.py` | 母帶限幅器單元測試:從 index.html 取出 AudioWorklet 原始碼在 node 跑,正弦 100Hz~20kHz、衝擊、雜訊突波,16 倍超取樣量真峰值(要整段一起升取樣,切段再升取樣邊緣會假造峰值) |
| `gen_drums.py` + `check_drums.py` | 產生測試鼓譜(搖滾、放克鬼音/開放 hi-hat、爵士三連音搖擺、抒情漸強漸弱、金屬雙大鼓)並檢查記譜規則(不跨拍、休止符對齊拍子、手上腳下、符尾不跨拍) |
| `gp_compare.mjs` | Guitar Pro 匯入比對:同一個 GP 檔用 alphaTab 照 Guitar Pro 規則排版(參考圖)與 App 匯入後的整條樂譜各存一張 PNG,另存轉出的 MusicXML、印出鼓件分布。`--track N` 指定音軌 |
| `gp_ui_test.mjs` | GP 選音軌對話框:19 種尺寸 × 中英文的版面檢查 + 隨機種子的真人操作模擬(選軌、取消、Esc、連點、旋轉、切語言、播放中匯入、重新整理),`--seed N` |
| `piano_tone_eval.py` | 鋼琴音色校正:用 App 的取樣與播放規則(含 PIANO_TONE、PIANO_EQ)彈 MAESTRO 真人演奏的 MIDI,跟同一份演奏的真實 Yamaha 錄音逐音比較各力度的亮度、起音高頻、1/3 八度頻譜。`python3 piano_tone_eval.py <放 曲名.flac + 曲名.mid 的目錄> 設定.json [秒數]`(MAESTRO 只拿來測試,不放 repo;另需 `pip install mido`) |
| `ir_compare.py` | 殘響 IR 比較(`python3 ir_compare.py a.flac b.flac …`):各倍頻程 EDT/T30、C80、左右相關性、單聲道相容、後段頻譜、殘響密度(Abel & Huang,1 = 完全擴散)、尾端剩多少、聽得到的音量內的離散回聲。換 IR 後的音量用 `render.mjs --taps --tapsrc verb` 直接量殘響回送(ConvolverNode 會自動正規化,不能用檔案音量算) |
| `gmd_stats.py` | 真人鼓手統計(Groove MIDI Dataset):各鼓件力度、hi-hat/ride 各拍位置的相對力度、鬼音、各肢體時間差、扣掉節奏型後的力度起伏與相鄰相關。對照 App 的 humanizeDrumHit(用法與 2026-10 的數字寫在檔案開頭) |
| `staff_gap.mjs` | 大譜表上下兩行的間距(格):App 現在的排版 vs 不畫圓滑線,看圓滑線撐開多少 |
| `score_crop.mjs` | 樂譜局部截圖(指定小節,或 0 = 自動找上下兩行最擠的地方),可帶 OSMD 排版規則 |
| `text_wrap_check.mjs` | 中文換行檢查:打開每個畫面(開始畫面、設定、匯出各步驟、快捷鍵…)× 8 種寬度,逐字算換行位置,列出括號被拆開、數字和單位被拆開、最後一行只剩 1~2 字、標點在行首。`--lang en` 掃英文 |
| `page_export_check.mjs` | 直式翻頁影片:實際跑一段直式匯出(`<樂譜> <輸出目錄> [開始秒] [結束秒] [piano\|drum]`),列出每次換頁的時間、應該在哪一頁 vs 畫出哪一頁(反覆記號跳回時要立刻換),存下換頁那一格的畫面 |
| `export_sheet_check.mjs` | 匯出頁版面(20 種尺寸 × 橫/直/方 × 中英文):預覽圖有沒有超出區塊(上面被切、下面蓋住選項)、變形、跟選項重疊,按鈕超出畫面/被截斷、橫向捲動(`<樂譜> [截圖目錄]`) |
| `fast_export_check.mjs` | 匯出影片(快速匯出 / 即時錄影):實際跑一次「開始匯出」,存下影片、印出花的時間(`<樂譜> <輸出目錄> [landscape\|portrait\|square] [開始秒] [結束秒] [--realtime] [--webmtest] [--mp4test] [--inst drum]`)。雲端沒有硬體編碼器,快速匯出會因為試編太慢自動改即時錄影;--webmtest / --mp4test 強制走快速匯出檢查輸出。模擬 iPhone Safari:--dropmeta(編碼器不給 decoderConfig)、--nosuspend(離線合成不回報進度)、--failmux(封裝出錯要退回即時錄影)、--cancel N;--twice 同一頁匯出兩次(第二次用記住的試編結果);匯出後檢查 audioCtx 有換回即時的;印出標題最久幾秒沒變(看起來卡住)、時間有沒有超過樂曲長度,--log 列出每次變化。用 ffprobe / ffmpeg ebur128 看長度與響度 |
| `mux_check.mjs` | MP4 封裝:ffmpeg 做真的 H.264 + AAC,模擬 Safari/Chrome 四種編碼器輸出餵給 muxVideoChunkFn / muxAudioChunkFn,解碼要跟原始串流逐位元相同 |
| `rotate_check.mjs` | 旋轉螢幕:手機尺寸 × 載入前後 × 設定/匯出/主畫面 × 直橫來回(連轉、轉的時候切語言主題、快速轉),轉回來每個元素的字級與高度要跟直接打開一樣;--nofix 拿掉 text-size-adjust 對照 |
| `cover_sheet_check.mjs` | 封面樣式選擇框:17 種尺寸 × 橫/直/方,量縮圖大小與佔畫面比例,檢查縮圖不超出框/畫面、取消鈕看得到、不用捲動 |
| `feature_check.mjs` | 功能總檢查:範例載入、頂欄、播放/暫停/從頭、跳轉、速度、移調、所有開關、色票、背景圖、深淺模式、語言、重新整理後記住設定、鼓譜、匯出頁三種格式預覽、Guitar Pro 匯入(用 alphaTab 把歡樂頌轉成 .gp)、全程沒有錯誤訊息 |
| `shot.mjs` | 樂譜畫面截圖,`--eval '<js>'` 印出頁面裡的變數(events、perfMeasures、tempoMap…) |

Guitar Pro 測試檔:alphaTab repo(github.com/CoderLine/alphaTab)packages/alphatab/test-data 裡的 .gp/.gpx/.gp5/.gp4(例如 conversion/full-song.gp、guitarpro4/fade-to-black.gp4、guitarpro7/drum-tabs.gp),只拿來測試,不放進 repo。

鋼琴測試曲:ASAP dataset(github.com/fosfrancesco/asap-dataset)的 xml_score.musicxml,只拿來測試,不放進 repo。

注意:離線渲染大約是即時的 1~5 倍時間(越密的曲子越慢);渲染時不要同時改 index.html(用 `--root` 指向快照)。

## 力度文字(dynamicWordActions)
- 覆蓋率檢查:把 ASAP 所有 xml_score.musicxml 的 <words> 抽出來(`grep -ho "<words[^>]*>[^<]*</words>"` | 去標籤 | sort | uniq -c),
  用 node 把 index.html 裡 DYN_LEVEL_STEPS ~ dynamicWordActions 那段 eval 出來逐行跑,看命中與漏掉的。2026-10:cresc. 238、dim. 89、decresc. 29、dolce 27、smorz. 18、poco cresc. 14、marcato 13、una corda 12 …全部命中;漏掉的都是速度、踏板、指法、標題
- 行為檢查:做一份每小節一個文字的測試譜(soft / cresc. / loud / dolce / più forte / sotto voce / dim.+虛線 / subito ff / una corda / fade out / 漸強 / 強 / sehr leise / cresc. al ff),載入後印 pianoLevelAt() 與每拍 n.pvel

