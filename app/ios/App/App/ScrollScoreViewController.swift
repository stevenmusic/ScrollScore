import UIKit
import Capacitor

/// 自訂的 Capacitor 橋接畫面:Capacitor 載入完成後註冊本地外掛(不在 npm 套件裡的外掛要手動註冊)。
class ScrollScoreViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(AudioRoutePlugin())
    }
}
