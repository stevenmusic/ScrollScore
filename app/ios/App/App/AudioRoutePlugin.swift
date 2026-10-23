import Foundation
import AVFoundation
import Capacitor

/// ScrollScore 本地外掛 AudioRoute:告訴網頁「現在聲音從哪裡出來」。
/// 網頁只在 builtInSpeaker 為 true(手機/iPad 內建喇叭)時,才在鋼琴母帶鏈多開一段「手機喇叭補償」(收掉小喇叭發不出的低頻)。
/// 只讀 AVAudioSession 的目前路由(portType 與名稱),不收集、不傳出任何資料;不屬於 Apple 必要理由 API,不需要改隱私權清單。
/// JS:Capacitor.Plugins.AudioRoute.getRoute() → { builtInSpeaker, portType, portName };
///    Capacitor.Plugins.AudioRoute.addListener('routeChange', cb)(同樣的物件;耳機插拔、藍牙連線、AirPlay 切換時觸發)
@objc(AudioRoutePlugin)
public class AudioRoutePlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "AudioRoutePlugin"
    public let jsName = "AudioRoute"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "getRoute", returnType: CAPPluginReturnPromise)
    ]

    private var observer: NSObjectProtocol?

    override public func load() {
        observer = NotificationCenter.default.addObserver(
            forName: AVAudioSession.routeChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            guard let self = self else { return }
            self.notifyListeners("routeChange", data: self.currentRoute())
        }
    }

    deinit {
        if let o = observer { NotificationCenter.default.removeObserver(o) }
    }

    @objc func getRoute(_ call: CAPPluginCall) {
        call.resolve(currentRoute())
    }

    /// 目前輸出路由。builtInSpeaker = 輸出裡有內建喇叭(.builtInSpeaker);
    /// 聽筒(.builtInReceiver)、耳機、藍牙(A2DP/LE/HFP)、AirPlay、HDMI、車用、USB 都不算。
    private func currentRoute() -> [String: Any] {
        let outputs = AVAudioSession.sharedInstance().currentRoute.outputs
        let first = outputs.first
        let speaker = outputs.contains { $0.portType == .builtInSpeaker }
        return [
            "builtInSpeaker": speaker,
            "portType": first?.portType.rawValue ?? "",
            "portName": first?.portName ?? ""
        ]
    }
}
