# Strata Easy TW 1.2.0-rc1 測試報告

測試日期：2026-10-18（台灣時間）。來源為使用者上傳的 v1.1，多檔案整合後另存新版本，原始上傳檔不覆寫。

**結論：原始碼與離線介面檢查通過；Windows EXE 未建置，Windows 安裝／解除安裝與官方模型端到端測試尚未完成。此版標示 RC1，不宣稱已達正式穩定版發布驗收。**

## 已執行與證據

| 項目 | 結果 | 範圍／證據 |
| --- | --- | --- |
| 自動化單元與回歸測試 | 50 通過、1 跳過，共 51 項 | docs/test-results/unit-tests.txt；跳過真實 Windows ConPTY |
| Python 語法編譯檢查 | 通過 | source-verification.json 記錄實際檔案數 |
| 導覽文案檢查 | 通過 | 產品程式／文案統一使用新手或初次使用者 |
| 原始碼資源自測 | 通過 | 圖集 RGBA／尺寸、各階段對應、三個展示檔、授權檔、VT；source-self-test.json |
| 實際啟動 GUI | 通過 | Linux Xvfb、Tk 8.6，非 Windows；ui-qa.json |
| 23 個導覽階段 | 通過 | 逐一切換標題與小雪，無 Tk 回呼例外 |
| 三種展示 | 通過 | 首次／既有到 demo_ready；失敗保留 error，不執行官方 BAT |
| 視窗版面 | 通過兩種尺寸 | 1420×940、1100×680；輸入／停止控制可見，右欄可捲動 |
| 縮放輸出保留 | 通過 | 修正 pyte 縮小時裁掉早期輸出的問題；保留短輸出及溢出歷史 |
| Windows 建置能力 | 此環境不支援 | build_windows.py 實際執行退出碼 1，理由為非 Windows；windows-build-attempt.txt |

環境：Linux x86_64、Python 3.12.14、Pillow 11.3.0、pyte 0.8.2、wcwidth 0.2.13。pywinpty 是 Windows 相依套件，本環境未安裝。GUI 測試另使用本地 Xvfb／Tk 8.6 與 Noto CJK 字型，這些測試工具不放入產品。

最初測試環境的 Tk 9.0 未正常繪出中文字；改用 Tk 8.6 後重新擷取全部畫面，已人工查看歡迎、下載及小視窗畫面。這不能代替 Windows 字型與 DPI 驗證。

## 重要測試情境

測試包含真實官方問句樣本的階段辨識、分段 ANSI、同一段輸出的最新階段、OSC 不觸發指南、錯誤保留、輸出文字不得直接標為健康檢查完成、ANSI 顏色與游標、中文寬字、VT 裝置回覆、單行輸入限制、日誌上限。

來源處理測試涵蓋路徑穿越、Windows 保留名稱／非法字元、大小寫衝突、符號連結、取消、磁碟不足、固定 commit 記錄、防止覆蓋；網路下載測試使用 mock，不宣稱完成真實 GitHub ZIP 下載與官方安裝。公開官方腳本僅供問句核對，未執行。

生命週期測試包含 8080 已占用不啟動、下載取消後不啟動 BAT、重複啟動防護、停止後可重新開始、舊事件忽略、不得自動回答、展示不呼叫下載或健康檢查。

## 畫面證據

docs/test-results/UI-welcome.png、UI-installing.png、UI-compact.png、UI-error.png 均為真實程式視窗擷取。左側文字為明確的離線模擬輸出，不能視為已執行 Strata 的證據。UI-installing 中的容量與下載數字是 fixture，不是實測進度。

小雪使用六姿態 3D 渲染風格透明圖集與輕微浮動；圖集已驗證並整合。未製作可旋轉網格或即時骨架動畫，詳見 docs/ASSET_PROVENANCE.md。

## 尚未完成

- Windows 10／11 真實 ConPTY、輸入法、Ctrl+C、程序樹停止與中文／空白路徑。
- PyInstaller 打包、凍結後資源／DLL、替換 LGPL 來源、Inno 安裝／升級／解除安裝。
- GitHub Actions 雲端建置；附帶工作流程未執行。
- 官方大型模型完整下載、封裝、MTP、GPU 部署、聊天回覆與續傳。
- Windows Defender／SmartScreen、程式碼簽章、高 DPI、乾淨無 Python 電腦。
- 最終 Windows 二進位的原生 DLL／Rust 靜態依賴授權及依賴安全稽核。

**沒有附帶 Setup.exe、Portable EXE 或 MSI。**建置腳本與安裝器設定已提供，但須在 Windows 成功建置及驗收後才有可用安裝程式。完整清單見 LEGAL_AND_RELEASE_CHECKLIST.md。

## 重現

在安裝 requirements.txt 的環境執行：

    python tools/verify_source.py

這會執行測試、語法與文案檢查、資源自測，寫入 docs/test-results。Linux 會實際檢查建置腳本的非 Windows 阻擋行為。

在可顯示 GUI 的桌面（或準備好 Xvfb DISPLAY）執行：

    python tools/verify_ui.py

程式會重播三種展示、切換所有階段、調整視窗並擷取測試視窗。請使用沒有敏感內容的測試桌面。

Windows 建置請用 BUILD_WINDOWS_EXE.bat；成功後必須保存 packaged-self-test.json、packaged-ui-test.json、授權 inventory 與產物雜湊，再做乾淨系統驗收。


## RC1 Python 偵測補丁（2026-10-18）

此次不是重新建置 Windows EXE，而是以原始碼修正啟動器誤判。

- 經查 `RUN_WINDOWS.bat`、`RUN_DEMO_WINDOWS.bat`、`BUILD_WINDOWS_EXE.bat` 全都只找 `py -3.12`／`py -3.11`，`bootstrap_windows.py` 再限制版本，是確定的邏輯缺陷。
- 新增 `LAUNCH_WINDOWS.bat` 及 `tests/test_python_launcher.py`，支援 CPython 3.10–3.13 x64／PATH／明確路徑。
- 在 Linux Python 3.13 環境搭配附帶的 pyte 0.8.2／wcwidth 0.2.13 原始套件與既有 Pillow 執行 **55 項 unittest：54 通過、1 項跳過（Windows 真實 ConPTY）**。
- `tools/verify_source.py` 進一步通過語法、文案、模型導覽資源自測。
- 三個 BAT 以 CRLF 編碼，仍未在 Windows CMD 上實機執行；Windows 3.13 的 pip 套件安裝與 GUI 效果尚待使用者實測。

備註：本報告前段為原始 rc1 的歷史測試結果。以補丁後的 `docs/test-results/source-verification.json` 與 `unit-tests.txt` 為最新測試依據。
