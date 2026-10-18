# 非官方聲明與第三方授權

Strata Easy TW 是社群非官方導覽器，與 Strata、模型作者及硬體廠商無官方合作或背書。相容性與效能依官方文件及當次實際結果為準。

原創程式碼沿用根目錄 MIT LICENSE 與原著作權資訊，不改變第三方元件或模型授權。

| 元件 | 用途／版本 | 授權資料 |
| --- | --- | --- |
| Strata | 執行時取得官方原始碼 | MIT，licenses/STRATA.txt；https://github.com/Niko1221/Strata |
| pywinpty | 2.0.15，ConPTY | MIT，licenses/PYWINPTY.txt 與完整 sdist；https://github.com/andfoy/pywinpty |
| pyte | 0.8.2，VT 解析 | LGPL-3.0-or-later，licenses/PYTE.txt、GPL-3.0.txt、作者名單、完整 sdist；https://github.com/selectel/pyte |
| wcwidth | 0.2.13，字元寬度 | MIT，licenses/WCWIDTH.txt 與完整 sdist；https://github.com/jquast/wcwidth |
| Pillow | 11.3.0，圖像處理 | HPND 與內含元件條款，licenses/PILLOW.txt；https://python-pillow.org/ |
| CPython／Tcl/Tk | 打包執行環境與 UI | PSF 及隨附條款；licenses/TCL-TK.txt；Windows 建置另收集 CPython LICENSE.txt |
| PyInstaller | 6.16.0，建置／bootloader | GPL 與 bootloader 例外等，建置時收集原文；https://pyinstaller.org/ |
| Inno Setup | 6.5+，安裝器 | licenses/INNOSETUP.txt；https://jrsoftware.org/isinfo.php |
| Inno 繁中翻譯 | ChineseTraditional.isl | 保留檔頭來源／譯者，來源雜湊見 licenses/SOURCE_RECORD.json |

tools/collect_licenses.py 在 Windows 建置時收集實際套件授權與 inventory。目前未產生 Windows 二進位，原生 DLL 與 Rust 靜態相依的最終授權核對仍是發布阻擋項目，以上不宣稱已涵蓋尚未產生的二進位。

## LGPL 來源與替換

未修改 pyte 上游程式。對應完整來源在 third_party_sources/pyte-0.8.2.tar.gz。原始碼版使用獨立套件；EXE 規格排除凍結 pyte，將 .py 原始碼放在可攜資料夾的 _internal/third_party/pyte，wcwidth 同理。可備份後替換為相容修改版，再重新啟動測試。整體重建步驟見 README 與建置腳本；實際替換仍待 Windows 驗證。

不限制為除錯修改之 LGPL 元件所需的逆向工程；原 LGPL／GPL 條款優先。

## 模型、圖像與隱私

本交付沒有模型權重。Qwen 或其他模型的權利、下載條件、使用限制請依官方模型頁與 LICENSE 個別核對，Strata 的 MIT 授權無法代替模型授權。

小雪是本專案描述生成的 3D 風格透明圖集，來源記錄見 docs/ASSET_PROVENANCE.md；不代表廠商品牌，沒有附帶 3D 網格。

導覽器不自動上傳日誌。官方下載、套件／模型安裝及主動點擊連結會連線各自服務，其隱私條款另行適用。

## SC117 第三方 Abliterated GGUF（使用者主動選用時）

模型來源：https://huggingface.co/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF 。該模型卡標示 Apache-2.0 並要求尊重所有上游模型的授權。Strata Easy TW 不夾帶、不重新發布模型權重。選用第三方模式時，僅在使用者確認後連線 Hugging Face 下載指定的公開 GGUF，建立來源版本及 SHA-256 紀錄。SC117 模型不是官方 Strata 所提供的標準權重；本導覽工具不聲明其回答品質、安全性、相容性或完全不拒答。
