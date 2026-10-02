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
- 鼓譜記譜：drumStemFixMusicXML()（送進 OSMD 前、autoBeam 之前）讓「同一拍有大鼓 + 手打 hi-hat（GM 42/46，或顯示位置 G5；大鼓 GM 35/36 或 E4/F4）」的和弦符桿一律朝上，這些音符的 articulations / technical 記號（開放 hi-hat 的「o」）設 placement="above"。OSMD 預設把演奏記號放在符頭那側，符桿朝上時「o」會跑到大鼓下面（使用者要求改）
- 鼓譜符尾一律水平（renderScore 裡 osmd.EngravingRules.FlatBeams = 樂譜有 percussion 譜號）：符尾斜度應該看最靠近符尾的音（hi-hat 都在同一位置），VexFlow 卻照符桿頂端算、被大鼓/小鼓帶歪
- 鼓譜（只限鼓譜，使用者強調「往上」只套用在鼓譜）：所有音符的 articulations / technical 記號（開放 hi-hat 的「o」、重音）一律 placement="above"（畫面與匯出影片同一份 SVG）；原檔沒寫 <stem> 的鼓譜音符一律朝上（單聲部鼓譜慣例），有寫的照原檔
- 鋼琴、吉他的符桿方向：stemConventionMusicXML()（在 autoBeam 之後，同一組符尾要一起決定）只補原檔沒寫的 <stem>：同譜表同小節兩個以上聲部時上聲部朝上、其他朝下；單一聲部看離中線最遠的音（和弦、同組符尾一起看），中線以上朝下、以下朝上、一樣遠朝下。中線依譜號（G 線 2 = B4、F 線 4 = D3、C 線 3 = C4，含 clef-octave-change；吉他高音譜號下方 8 是 B3）。OSMD 原本沒寫就一律朝上。有寫的照原檔（例如莫札特 K545 的檔案本來就有）
- 鋼琴音色放在本 repo 的 piano/：Accurate-Salamander Grand Piano V6.2（Salamander V3 by Alexander Holm，CC-BY 3.0），30 個取樣音 × 16 層力度 + 放鍵弦共鳴（harmL/harmS）+ 放鍵機械聲（rel）+ 踏板聲，48k/16-bit FLAC + piano/manifest.json;讀不到才退回 raw.githubusercontent，manifest 都讀不到才退回 Tone.js 單層鋼琴
- 鋼琴取樣已做過「單聲道相容」處理（AB 立體聲對某些音加成單聲道會抵消 10dB）：逐 STFT 頻格保留能量的 mid、side×0.8（不要再縮：錄音房間的殘響幾乎都在 side，縮到 0.45 會把真實房間聲砍掉約 6dB、鋼琴變乾，再靠人工殘響補就不自然）、低音左高音右 ±0.25，每個取樣的響度用「立體聲與單聲道響度的平均」對齊原本校正；重建取樣要用同一套處理（piano/build/pf_build.py、stereo_fix.py）
- 鋼琴力度照 Accurate-Salamander V6.2：各層錄音已校正成一樣大聲，依力度分區挑層（VEL_16），音量 = 0.015 + 0.985×（力度/127）²（amp_veltrack 98.5）;PIANO_GAIN 1.5（整首約 −11.5 LUFS、不削波）
- computePianoDynamics() 算每個音的 n.pvel(1~127)與 n.pdt(和弦內聲部最多晚 7ms):力度記號/髮夾(sf/sfz 只影響當下)、旋律較重、內聲部與左手較輕、拍子輕重、旋律起伏、4 小節樂句、重音、左右手 AR(1) 起伏 + 隨機；pianoAutoMacro() 依每小節織度（音符密度、和弦厚度、旋律高度，平滑後標準化）給 ±10 力度的段落大小聲 + 4/8 小節兩層樂句弧線 + 曲尾兩小節漸弱，譜上沒力度記號時全用、有記號時只用四成（網路上很多古典 MusicXML 完全沒力度記號，不加的話整首只有約 4dB 起伏）
- 鋼琴只載入樂譜用到的（音 × 力度層）;記憶體預算（桌機 1.2GB、iOS 220MB、4GB Android 280MB、2GB Android 120MB，共鳴/機械聲也算在內）不夠時依序：截短到需要的長度 → 單聲道 → 合併最少用到的層。制音器落下時加 harm/rel（音量用 manifest 的 d 換算成原廠 V3 的相對音量，依按住時間 rt_decay 衰減）;F#6（MIDI 89）以上沒有制音器
- 鋼琴混音：voice → getPianoBus()（PIANO_EQ：450Hz −2dB、2.8kHz −3.5dB（手機喇叭共振峰，避免尖）、9kHz 高頻架式 +1.5dB）→ masterGain → loudnessComp → 限幅器。試過鋼琴專用慢起音壓縮器，p→ff 被壓扁、清晰度沒變好，不要再換。注意 Web Audio 的 DynamicsCompressor 會自動補增益（makeup），loudnessComp 實際約 +7dB
- 總輸出（MASTER 設定）：masterGain → loudnessComp → makeup 1.82 → masterBus ← 鼓組匯流排；masterBus → 母帶限幅器（AudioWorklet，MASTER_LIMITER_SRC：預讀 5ms、16 點 Kaiser 內插 4 倍超取樣真峰值、立體聲連動、快 90ms/慢 0.7s 依壓的時間自動切換，上限 −1.3dBFS，實測 ≤ −1.0dBTP）→ masterOut → 喇叭與匯出影片。不支援 AudioWorklet 時才用備援（DynamicsCompressor + 4 倍超取樣軟削波，前面先扣 1.6dB 對齊音量）；播放/匯出前最多等 0.5 秒讓限幅器載好。舊的 DynamicsCompressor 限幅器會自動把整個訊號加約 1.1dB，所以 makeup 從 1.6 改 1.82、鼓 0.62 改 0.70，整體響度跟以前一樣（11 首 A/B 差 ≤ 0.3 LU、LRA 相同、−3dBFS 以上的時間少 2~13 倍）
- 鋼琴用自己的殘響 getPianoVerb()（buildPianoHallIR，參數跟 Surrey 大學真實房間量測比對過）：8 個同極性早期反射（3~40ms，越晚越暗）、四頻段各自指數衰減（RT60 1.5/1.3/0.95/0.55s）、各頻段左右相關性（低音 0.75 → 高音 0.08，真實殘響低音左右幾乎一樣）、預延遲 8ms、送入前 180Hz 高通、固定種子、wet 0.33×殘響滑桿。不用共用的 buildImpulseResponse（(1−t)^2.4 衰減不自然、高頻不衰減、早期反射左右反相、左右完全不相關）；吉他也不用（見下面吉他的殘響）
- 鋼琴殘響送出：一般 0.5、譜上有踏板 ×1.7。harmonyEndSec 一定有值（至少是同時最長音的結尾），不能拿來判斷踏板
- 譜上沒踏板、由和聲自動延長的音用「半踏板」：放鍵後依 pianoHalfPedalTau（PIANO_HALF_PEDAL 0.7）較快衰減，避免級進旋律全部疊在一起變糊；譜上有踏板才完全延音
- 「圓滑/踏板」開關已移除（使用者要求）：圓滑線、踏板記號、和聲延音一律開啟，不要再加回開關
- 民謠吉他音色放在本 repo 的 guitar/steel/：FSS Steel-String Acoustic Guitar（FreePats 2020-05-21，FlameStudios「FS Seagull」取樣的子集，GPL-3.0 + FreePats 音色例外，授權檔 guitar/steel/LICENSE.txt、gpl.txt）。E2~C6 每個半音都有錄音（重彈 HV 42 個、中彈 MV 17 個，L1=MV 1-85、L2=HV 86-127），44.1kHz 單聲道。重建：python3 guitar/build/fss_build.py <FSS SFZ 目錄> guitar/steel（音準校正、48kHz、降噪、音色連續性修正：原錄音 B3 以上 8kHz 以上亮約 20dB，兩層各自對音高做線性趨勢、偏離部分修 70%、±9dB；響度對齊 −18 LKFS），共 59 檔 5.3MB。原本的 Ella Gitauru 已移除：真正的錄音只有 5 個音高、其他音都要升調（最多 +17 半音），使用者聽了覺得很難聽、要求每個音都要有取樣
- 使用者要求「每個音都要有取樣」。古典吉他（MF）只有 8 個音高，不符合，但找不到可轉散布、每個音都有、音質好的尼龍弦：FreePats 西班牙古典吉他缺音且錄音差；NSynth（CC-BY 4.0）37 把木吉他裡只有 6 把每個音是獨立錄音，多數 0.2~0.6 秒就衰減 20dB，只有 guitar_acoustic_032/004 接近真實吉他，但只有 16kHz、每音 4 秒；Iowa、Philharmonia 網站被擋。使用者說太花時間就停，所以古典吉他維持 MF
- 古典吉他音色放在本 repo 的 guitar/nylon/：MF Concert Guitar（Markus Fiedler，CC-BY-NC-SA 3.0 + 可用於商業音樂製作的例外；處理後的檔案同授權，授權檔 guitar/nylon/LICENSE.txt）。來源是 bigcat 的 Kontakt monolith（.nki，mediafire 要用瀏覽器 User-Agent），guitar/build/nylon_build.py 內含 NCW 解碼器。E2 A2 D3 G3 B3 E4 A4 D5 × pp/p/f/ff（1-40/41-74/75-104/105-127）× 2~4 輪替（5 組完全重複的檔案已去掉）+ 6 個放音聲（off，對齊到比音符小 26dB，弦真的被止住時才播）+ 9 個換把位擦弦聲（fret，整段 −40 LKFS；computeGuitarDynamics 標 n.gslide：同一條纏弦〔第 6~4 弦〕移到按弦位置 3 格以上、間隔 ≤ 四分之一全音符，在新音前 70ms 播）。原檔單聲道、峰值正規化、標示 44000Hz，轉 48kHz FLAC，共 13MB。播放時取最近的音（最多升降 2.5 半音），amp_veltrack 96，不加把位濾波、力度明暗 ±4dB
- Pettinhouse（ClassicGuitar FREE / AcousticGuitar FREE）不能用：授權禁止把聲音上傳到任何伺服器。tonejs-instruments、Martin HD28、FreePats 都比過，比較差
- 兩把吉他共用引擎：GTR_INSTS（各自 manifest/buf/loading/fallback/gain）、loadGuitarSamples(inst)、playGuitarNote(inst, …)；manifest 讀不到才退回 REAL_INSTRUMENTS 的 tonejs 取樣
- 吉他技法：tech.pizzicato（MusicXML <note pizzicato="yes">）、tech.harmonic 兩把都用濾波模擬（FSS、MF 都沒有悶音/泛音錄音）
- 吉他左右擺位：依弦 (s − 2.5) × 0.048（低音弦偏左、高音弦偏右，±0.12），gtrConnect(node, send, inst, pan)。StereoPanner 對單聲道是等功率擺位，置中時 −3dB，所以前面補 √2（沒補的話整體小 3dB）
- 吉他的弦/把位：computeGuitarStringRinging() 在空著的候選弦裡挑品格最低的（開放把位），存在 n.gstr；兩把都是「取最近的錄音」（gtrNearestSample），不再有把位濾波；gtrVelTone() 力度明暗高頻架（鋼弦 ±6dB、尼龍 ±4dB）。音量 = (1−t) + t×（力度/127）²，t = amp_veltrack（鋼弦 98、尼龍 96），放開 tau 0.05s（低音空弦 0.09）
- computeGuitarDynamics() 算 n.gvel / n.gdt / n.gseed：力度記號/髮夾/段落起伏（共用 pianoLevelAt / pianoAutoMacro）、拍子輕重、力度記號幅度 74 + 170×level（比鋼琴的 150 寬：ff ≈ 106、pp ≈ 33）、5 音以上才當刷弦（4 音和弦在指彈/古典是四指同時撥，當刷弦會被逐弦掃開，使用者覺得很不自然；正拍下刷低→高、反拍上刷高→低，上刷最低兩條 −16 幾乎刷不到，弦距 6~16ms 越大聲越快）、2~4 音手指同時撥（2~3 音 ≤4ms、4 音 ≤6ms）、單音旋律起伏、AR(1) + 隨機
- 吉他混音：getGuitarBus(inst)，兩把各自的 GTR_EQ：鋼弦 75Hz 高通、220Hz −2dB、2.8kHz −1.5dB（FSS 本身就亮，不加高頻）；尼龍 70Hz 高通、130Hz −4dB（MF 麥克風近音孔，基音比第 2 諧波大 19dB、琴身 102Hz 共振）、3.5kHz 高頻架 +2dB → masterGain。殘響 getGuitarVerb() 用 buildPianoHallIR(GTR_VERB)（較小房間，RT60 1.15/1.0/0.75/0.45s、早期反射 2.4~29ms），送出 0.45。增益兩把都 1.6：FSS 巴哈 BWV846 −11.1、刷弦 −10.7、pp→ff 12.8dB；（以下是 Ella 時的量測）巴哈 BWV846 鋼弦 −12.1、尼龍 −11.6 LUFS（鋼琴同曲 −10.8），刷弦 −10.9 / −11.1；pp/p/mf/f/ff 各一小節的 G 和弦：鋼弦 −20.7/−15.2/−9.6/−8.4/−7.8、尼龍 −20.0/−15.7/−10.4/−9.3/−8.3（p→ff 約 7.4dB，跟鋼琴差不多）
- 試過吉他繞過 loudnessComp、改用自己的母帶段（慢起音壓縮 + 補增益，像鼓那樣）：mf→ff 還是只有約 3dB（瓶頸是最後的限幅器上限，不是壓縮器），整體要小聲 2.5dB 才換到 pp→ff 多 2dB，不划算，維持走 masterGain → loudnessComp。也不要把門檻設在音量之下（−26dB、2:1 會把所有大小聲差砍半）
- 測試：tools/audiotest/render.mjs 用 OfflineAudioContext 離線渲染（比即時錄 masterOut 快、結果固定），jsdelivr 在雲端環境被擋，要從 npm 拿 OSMD/JSZip 再用 page.route 攔截
- 樂器只保留鋼琴、吉他（民謠、古典兩把）、鼓組
- 民謠吉他、古典吉他目前標「開發中」並停用（使用者要求）：樂器選單的 <option disabled>，文字加「・開發中」；舊設定存了吉他時退回鋼琴。程式與取樣都保留，拿掉 disabled 即可恢復
- 匯出影片用 canvas.captureStream + MediaRecorder
- 時間軸(buildTimeline):OSMD 2.0 的 cursor 會照反覆記號/第一二結尾跳,但 currentTimeStamp(= CurrentSourceTimestamp)是記譜位置、跳回去會變小(以前重播段跟第一遍疊在同一時間、兩遍一起響,反覆根本沒播)。現在 ev.tWhole = 演奏位置(it.CurrentEnrolledTimestamp,OSMD 自己展開好的),ev.srcT = 記譜位置,ev.mIdx = 演奏小節編號;perfMeasures = 演奏順序的小節。查原始 XML 來的資料(articEntries、arpEntries、pedalRanges、slurRanges、repeatChordRanges、vibratoRanges、guitarTechEntries、鬼音/邊擊符頭、力度記號/髮夾、measureRanges、measurePixels)一律用 srcT;排程、捲動、計時用 tWhole。範圍結尾換回演奏位置:ev.tWhole + (r.end − srcT)
- 速度變化(tempo map):buildTempoMap() 依 perfMeasures 的 OSMD TempoInBPM,只在原檔該小節真的有 <sound tempo>/<metronome> 時換速度(OSMD 會把「Allegro」文字自己換成預設速度,不信);第一個速度記號之前的小節(OSMD 填 120)當成開頭速度。速度滑桿 = 開頭速度,後面等比例縮放。wholeToSec(位置)/secToWholeTempo/spanSec(起點, 長度)(音長一定要用 spanSec,不能用 wholeToSec(長度));預備拍用當下位置的速度。小節中間的速度變化套在小節開頭;漸快/漸慢(rit./accel.)不處理
- 單行排版的版面保護(renderScore):SheetMaximumWidth = 1e7(OSMD 預設 32767 是 canvas 限制,長曲子會被折成第二行);SlurPlacementUseSkyBottomLine = true(長圓滑線舊算法會往下彎很深,撐開譜表間距);tameFarDirectionsMusicXML() 把掛在上譜表、放在下方的踏板記號改掛最後一個譜表、拿掉 |default-y| > 120 的位置;排完如果譜表間距 > 45 或最下方輪廓 > 40(scoreLayoutTooTall)就不畫踏板記號再排一次(OSMD 某些檔案的踏板記號會一層層往下疊,播放照樣依原檔踏板)
- 鼓譜顯示轉換(drumStemFixCore,只限有 <unpitched> 的鼓譜音):MuseScore 4 的開放 hi-hat「o」是 <technical><open/>,OSMD 只認得 <open-string/>,要換;邊擊 slashed 符頭 OSMD 不會畫(變一般小鼓符頭),改成 x
- 排程時間不早於 audioCtx.currentTime(鼓的人性化時間偏移可能是負的,第一拍會變成過去時間被整個丟掉)
- 測試工具在 tools/audiotest/(見該目錄 README):離線渲染(OfflineAudioContext)量響度/真峰值/LRA、力度階梯、限幅器單元測試、測試鼓譜產生與記譜檢查、截圖。鋼琴測試曲用 ASAP dataset 的 MusicXML(只測試,不放 repo)
- 測試鼓譜的記譜規則(使用者強調,寫錯過好幾次):照 Weinberg/PAS 與 MuseScore 4 預設鼓組(drumset.cpp)——音符與休止符不跨拍、休止符對齊拍子(空兩拍且從第 1 或 3 拍開始才用二分休止)、手(符桿上)腳(符桿下)兩個聲部各自寫滿、符尾以拍為單位、搖擺用三連音記、開放 hi-hat 是 x 符頭 + 上方「o」、中鼓 48 E5 / 47 D5 / 45 B4、落地鼓 43 A4 / 41 G4。MuseScore 網站上使用者上傳的譜品質參差,不能拿來當記譜依據

## Git 流程
- 所有改動完成後直接 commit 並 push 到 main，不用先問我

## 絕不能做的事
- 不要把單檔拆成多檔案，除非我明確要求（PWA部署依賴單檔架構）
- 改 OSMD 版本前先確認 CDN 版本號存在且穩定

## 已知踩過的坑
- OSMD 1.8.4 的 cursor 不會處理反覆記號，2.0.0 版本才支援
- 移調要先設定 osmd.TransposeCalculator 再設 osmd.Sheet.Transpose，否則不會生效
- 匯出影片時 SVG 點陣化要切成4000px的tile，避免iOS canvas尺寸限制
