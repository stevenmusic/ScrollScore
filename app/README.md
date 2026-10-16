# ScrollScore iOS App

用 [Capacitor](https://capacitorjs.com) 8.5.3 把 `../index.html` 包成 iOS App。網頁本身不用改，App 只是把網頁和音色檔一起打包，讓它可以離線使用、上架 App Store。

## 打包哪些檔案

`npm run build`（`build-www.mjs`）會把下面這些檔案複製到 `www/`，再由 Capacitor 放進 App：

- `index.html`、`privacy.html`、`support.html`
- `vendor/`：OSMD、JSZip、alphaTab 程式庫
- `samples/`：範例樂譜
- `piano/`、`drums/`：鋼琴與鼓的音色

**不打包**的檔案：

- `guitar/`：吉他沒有在 App 裡，而且民謠吉他取樣是 GPL、古典吉他取樣不能商用，都不能放進 App Store 的 App。
- `tools/` 和各資料夾裡的 `build/` 建置腳本。

打包後約 226 MB。超過 200 MB，使用者用行動網路下載時，App Store 會先問要不要下載；用 Wi-Fi 不受影響。

## iOS 專案裡已經改好的設定（`ios/App/App/`）

- **`AppDelegate.swift`**：啟動時把音訊類別設成「播放」，iPhone 的靜音開關不會讓樂譜沒聲音。網頁裡的 `navigator.audioSession` 在 iOS 17 以上也會設定一次。
- **`Info.plist`**
  - `NSPhotoLibraryAddUsageDescription`：「儲存影片」存到相簿需要這個說明，沒有的話 App 會當掉。
  - `ITSAppUsesNonExemptEncryption = false`：App 沒有用加密，送審時不用再回答出口合規問題。
  - 裝置需求改成 `arm64`：範本原本寫的是 32 位元的舊架構 `armv7`。
- **原生外掛**:`@capacitor/filesystem`、`@capacitor-community/media`(匯出影片直接存相簿,`package.json` 已列入,`npm install` + `npm run sync` 會自動加進 Xcode 專案)。
- **App 圖示**：使用者畫的 logo（`assets/logo-original.png`），用 `assets/make_icon.py` 補掉四個角的白色、裁成 1024×1024 的不透明 PNG（`assets/icon-1024.png`）。iOS 會自己裁圓角，所以圖示本身不能先畫圓角或留白邊。
- **啟動畫面**：`assets/splash.svg` 轉成 `assets/splash-2732.png`。
- **Bundle ID**：`com.stevenmusic.scrollscore`。最低支援 iOS 15。

## 在 Mac 上編譯與送審

需要一台 Mac，安裝 Xcode（從 App Store 下載），並加入 Apple Developer Program（每年 US$99）。

```bash
cd app
npm install          # 安裝 Capacitor
npm run sync         # 複製網頁和音色到 www/,再同步到 iOS 專案
npm run open         # 用 Xcode 打開
```

在 Xcode 裡：

1. 左邊點 **App** → **Signing & Capabilities** → **Team** 選你的開發者帳號。Bundle ID 被占用的話，改成你自己的，例如 `com.你的名字.scrollscore`，同時改 `capacitor.config.json` 的 `appId`。
2. 上方裝置選你的 iPhone，按 ▶ 執行，在手機上實際測試：
   - 播放範例《歡樂頌》和搖滾鼓。打開靜音開關也要有聲音。
   - 匯入一個 MusicXML 檔案。
   - 按上方攝影機圖示匯出影片 → 開始匯出 → 完成後自動存到「照片」(第一次會問能不能加入照片,要允許)。
3. 確認沒問題後，裝置選 **Any iOS Device (arm64)** → 選單 **Product → Archive** → **Distribute App → App Store Connect → Upload**。
4. 到 [App Store Connect](https://appstoreconnect.apple.com) 建立 App，照 `APP_STORE.md` 填資料、選剛上傳的版本，送審。

**網頁更新後**，在 `app/` 裡重新執行 `npm run sync`，再從 Xcode Archive 上傳新版本。記得把 Xcode 裡的版本號（Version / Build）往上加。
