# ScrollScore 音訊/記譜測試工具

不屬於 App 本體(App 維持單檔 index.html),只給開發時量測用。

```
cd tools/audiotest && npm i          # playwright 1.56.1、opensheetmusicdisplay 2.0.0、jszip、@coderline/alphatab 1.8.4(雲端環境 jsdelivr 被擋,改從 npm 拿)
pip install numpy scipy soundfile pyloudnorm
```

| 檔案 | 用途 |
|---|---|
| `render.mjs` | 用 OfflineAudioContext 離線算出 App 的實際輸出(跟網頁播放同一條音訊路徑),存 32-bit float WAV。`--taps` 多存 masterBus(限幅器之前)兩聲道;`--root` 指定要測的版本目錄(A/B 比較);`--set '{"MASTER.makeup":1.8}'` 在載入樂譜前改設定物件;`--sec` 最長秒數;`--inst`、`--tempo`、`--reverb` |
| `batch.sh` | 平行(3 個)渲染一個目錄的樂譜並跑 analyze.py |
| `analyze.py` | 整體響度 LUFS、真峰值(4 倍超取樣)、LRA、短期響度最大值、−3dBFS 以上時間比例、左右相關性;有 taps 時加上限幅器前的響度/峰值 |
| `ladder.py` + `gen_piano_dyn.py` | 鋼琴力度階梯(pp p mp mf f ff 各 2 小節):量整條鏈路最後留下多少大小聲差 |
| `limiter_test.mjs` + `limiter_tp.py` | 母帶限幅器單元測試:從 index.html 取出 AudioWorklet 原始碼在 node 跑,正弦 100Hz~20kHz、衝擊、雜訊突波,16 倍超取樣量真峰值(要整段一起升取樣,切段再升取樣邊緣會假造峰值) |
| `gen_drums.py` + `check_drums.py` | 產生測試鼓譜(搖滾、放克鬼音/開放 hi-hat、爵士三連音搖擺、抒情漸強漸弱、金屬雙大鼓)並檢查記譜規則(不跨拍、休止符對齊拍子、手上腳下、符尾不跨拍) |
| `gp_compare.mjs` | Guitar Pro 匯入比對:同一個 GP 檔用 alphaTab 照 Guitar Pro 規則排版(參考圖)與 App 匯入後的整條樂譜各存一張 PNG,另存轉出的 MusicXML、印出鼓件分布。`--track N` 指定音軌 |
| `gp_ui_test.mjs` | GP 選音軌對話框:19 種尺寸 × 中英文的版面檢查 + 隨機種子的真人操作模擬(選軌、取消、Esc、連點、旋轉、切語言、播放中匯入、重新整理),`--seed N` |
| `shot.mjs` | 樂譜畫面截圖,`--eval '<js>'` 印出頁面裡的變數(events、perfMeasures、tempoMap…) |

Guitar Pro 測試檔:alphaTab repo(github.com/CoderLine/alphaTab)packages/alphatab/test-data 裡的 .gp/.gpx/.gp5/.gp4(例如 conversion/full-song.gp、guitarpro4/fade-to-black.gp4、guitarpro7/drum-tabs.gp),只拿來測試,不放進 repo。

鋼琴測試曲:ASAP dataset(github.com/fosfrancesco/asap-dataset)的 xml_score.musicxml,只拿來測試,不放進 repo。

注意:離線渲染大約是即時的 1~5 倍時間(越密的曲子越慢);渲染時不要同時改 index.html(用 `--root` 指向快照)。
