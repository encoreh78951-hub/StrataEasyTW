> **公開測試候選版 1.3.0-rc1**：可以透過 GitHub Windows CI 自動建置；請見 [README_發布方式.md](README_發布方式.md)。不需要在開發者自己的電腦下載或重裝模型。

# Strata Easy TW 1.3.0-rc1

非官方繁體中文 Windows 安裝導覽器，以使用者上傳的 v1.1 整合升級，保留 Strata 官方 START-HERE.bat 互動流程。

**本交付是原始碼候選版。此環境沒有 Windows，未產生 Windows EXE，亦未完成真實模型部署；公開穩定版發布前仍須完成 Windows 驗收。**

## 新功能

- 賽博龐克雙欄介面：左側真實 ConPTY 終端機，右側依官方英文輸出辨識階段、提供詳細繁體中文說明，不自動回答問題。
- 小雪升級為 3D 渲染風格的透明雪納瑞圖像：六種姿態對應多種安裝階段，可減少動態。這是預先渲染素材，不包含可旋轉的 3D 網格。
- 首次安裝、既有安裝、失敗排除三種離線展示。
- 官方來源 commit 記錄、安全解壓、防覆蓋、取消與重啟、8080 衝突防護、日誌匯出。
- Windows 建置腳本、繁中 Inno Setup 安裝器設定與第三方授權資料。

## 先看離線展示

1. 在 Windows 解壓縮完整資料夾，不要直接在 ZIP 中執行。
2. 可使用已安裝的 **64 位元 CPython 3.10、3.11、3.12 或 3.13**。`py` Launcher 不再是必要條件：有 `python`／`python3` 在 PATH 也可以。
3. 雙擊 RUN_DEMO_WINDOWS.bat。首次啟動會連網安裝導覽器相依套件至 .guide-venv，之後重用；**展示本身離線，第一次準備套件仍需網路。**
4. 左下可切換三種情境。展示不執行 Strata、不下載模型、不偵測 8080；主動點擊來源連結仍會開啟瀏覽器。

原始碼啟動需要 Python；上一版 RC2 的 EXE 已在 GitHub Actions 成功打包。本次新增 SC117 的 1.3.0-rc1 原始碼仍需重新跑 Windows CI，產生對應新 EXE。

## 真正安裝

1. 使用 Windows 10 1809 以上／Windows 11 的 x64 環境。模型、GPU、RAM 與磁碟需求，以當次官方文件和輸出為準；大型模型可能需數十至上百 GB，請先確認容量。
2. 雙擊 RUN_WINDOWS.bat，選「從官方 GitHub 下載」或「使用既有資料夾」。下載模式在指定位置建立 Strata-Official，已存在時不覆蓋。
3. 既有資料夾應包含 START-HERE.bat、SETUP.bat、setup.py、LICENSE。請只選可信來源；本工具不驗證手動提供的 BAT 是否被修改。
4. GPU 預設沿用官方設定。「重新設定既有模型（--setup）」預設關閉，勾選可能改動模型設定。
5. 閱讀來源與模型授權，勾選非官方聲明，再按「開始官方安裝」。官方 BAT 保持原樣，在 Windows ConPTY 執行。
6. 依左側問題，在輸入欄送出選項；官方有預設時可按「按 Enter」。也可聚焦終端機直接輸入、使用方向鍵。貼上內容先進輸入欄供檢查，不接受多行貼上。
7. 右側是保守解說，不是逐字翻譯。官方問句可能改變，請以原文為準。
8. 伺服器啟動後，按「檢查並開啟聊天」。工具先檢查本機 /health，再開啟 http://127.0.0.1:8080 。健康回應未核對 PID，不能當作完整安裝驗收。

官方可能把 Strata-data 放在程式資料夾的同層。**新加入兩種模型來源選擇：**
- **官方標準模型（預設）**：完全保留 Strata 的模型選擇與 `START-HERE.bat` 問答。
- **SC117 第三方低拒答模型（實驗性）**：選取 Q2_0／IQ2_XS／IQ3_XXS／IQ3_S，直接從 SC117 的 Hugging Face 專案下載兩個 GGUF 分片、驗證 LFS SHA-256，然後將本機 GGUF 路徑交給官方腳本重建專用 Pack。

SC117 會使用 `<選擇的位置>/Strata-Easy-TW-SC117/` 下獨立的官方程式、GGUF 和 Strata-data；避免和標準模型共用 Pack。大模型本體約數十 GB，還需預留 Pack 和暫存空間。**SC117 分支尚未完成數十 GB 真實網路下載 + Pack + 推理的端到端驗收**，不能當作已保證安裝成功。中斷下載會保留 `.part` 供再次執行續傳。

詳細操作與來源請見 [SC117_INSTALL_GUIDE.zh-TW.md](SC117_INSTALL_GUIDE.zh-TW.md)。

SC117 模型不是 Strata 官方產品。Abliterated 僅意指經第三方降低某些拒答傾向，**不保證所有回答都不拒答**。請查看其獨立授權、模型卡及上游授權。

## 停止、重試與日誌

「停止工作」及關閉視窗會要求確認，可能中斷下載／封裝。停止僅針對本次啟動的程序樹，不會依程序名稱清除其他服務。8080 已占用時不啟動第二份，也不關閉原有服務。

下載官方原始碼途中取消，不會執行 BAT。若最後搬移階段失敗留下部分資料夾，請先檢查內容，再改用新空白位置重試；不會自動刪除你選定的資料。

「匯出日誌」需要手動操作，記憶體日誌上限約 400 萬字元。終端機回顯可能含路徑、帳號或 Token，分享前請遮蔽。啟動失敗可能留下 %LOCALAPPDATA%\\StrataEasyTW\\crash.log。本工具不自動上傳日誌。

| 狀況 | 處理 |
| --- | --- |
| 找不到 py／Python | 新版會自動尋找 64 位元 Python 3.10–3.13：先試 py，再試 PATH 中的 python／python3。可在 CMD 執行 `py -0p`、`where python` 和 `python --version`，或用 `set "STRATA_GUIDE_PYTHON=完整路徑\python.exe"` 手動指定 |
| pip／套件下載失敗 | 檢查網路與代理，保留錯誤訊息，不停用系統防護 |
| GitHub 403／限流 | 稍後重試，或自行從官方取得完整原始碼後選既有資料夾 |
| ConPTY／DLL 失敗 | 核對 Windows 版本、64 位元 Python 與完整相依套件 |
| 官方輸出暫停 | 先看是否仍在下載／封裝，不要只因暫時沒有新文字就停止 |
| 視窗擠壓 | 收合設定，右欄可捲動；最低 1100×680 邏輯像素，高 DPI 待 Windows 實測 |

## 建置 Windows EXE

在 Windows x64 使用 CPython 3.10–3.13（建議 3.12）與 **Inno Setup 6.5 以上**，雙擊 BUILD_WINDOWS_EXE.bat。

腳本依序測試、收集授權、PyInstaller onedir 打包、資源與真實 ConPTY fixture 測試、離線 UI 測試，再編譯安裝器。失敗就停止。

成功後預期產物（本次未產生）：

- release/StrataEasyTW-1.3.0-rc1-Windows-Portable.zip，須保留整個資料夾，不能只取出 EXE。
- release/StrataEasyTW-1.3.0-rc1-Setup.exe，繁中、每位使用者安裝，不需管理員權限。
- release/SHA256SUMS.txt、build/packaged-self-test.json、build/packaged-ui-test.json。

只建置可攜版：準備相依套件後執行 python tools/build_windows.py --portable-only。附帶 GitHub Actions 工作流程，但本次未連接倉庫、未執行雲端建置或公開發布。產物預設未簽章；請完成 Windows 驗收與簽章後再正式發布。

## 測試與架構

安裝 requirements.txt 後可執行：

    python -m unittest discover -s tests -v
    python app.py --demo
    python app.py --self-test self-test.json

Linux/macOS 僅供離線展示與可攜邏輯測試。app.py 負責介面，session.py 管理工作，terminal_backend.py 負責 ConPTY，terminal_screen.py 處理 VT，source_manager.py 下載解壓，guide_rules.py／beginner_help.py 提供中文說明，mascot.py 管理小雪。

詳見 TEST_REPORT.md、THIRD_PARTY_NOTICES.md、LEGAL_AND_RELEASE_CHECKLIST.md。原創程式沿用根目錄 MIT LICENSE；第三方元件與模型各自適用原授權。Strata 官方：https://github.com/Niko1221/Strata 。


## Python 偵測修復（RC1 補丁）

原先三個啟動 BAT **只使用 `py -3.12` 或 `py -3.11`**，且 Python 啟動器又硬性限制 3.11/3.12。若電腦有 3.10/3.13 或只有 `python.exe` 沒有 `py`，就會誤報沒有 Python。

本修補版改為：

1. 依序嘗試 `py -3.12`、`py -3.13`、`py -3.11`、`py -3.10`；若 Launcher 不存在，改試 `python`、`python3`。**只接受 64 位元 CPython 3.10 至 3.13**。
2. 若 Python 不在 PATH，於 CMD 執行 `set "STRATA_GUIDE_PYTHON=C:\...\python.exe"`，**從同一個 CMD 執行 `RUN_WINDOWS.bat`**。使用者需以實際安裝路徑取代範例。
3. 所有依賴仍安裝在本專案自己的 `.guide-venv`，不動系統 Python 套件，也不改 Strata 自己的 `.venv`。
4. **注意：** 修改使用的 Python 大版本後，若 `.guide-venv` 是舊版本建立的，請先關閉程式、只重新命名本專案內的 `.guide-venv` 為 `.guide-venv-old` 後重開 BAT；不要去動 Strata 或 ComfyUI 的環境。
5. `pywinpty==2.0.15`、`Pillow==11.3.0` 在 PyPI 有 CPython 3.13 Windows x64 wheel。不過尚未在真實 Windows 3.13 上跑完整 ConPTY／UI／EXE 實機驗證。

**一鍵 EXE 正式發布仍待 Windows 驗收。** 目前本補丁是 Python 原始碼啟動器修復，並非最終已驗證的 Windows EXE。


## 針對 BAT 雙擊立即消失的處理
請見 `啟動問題_請先看.md`。新增 `RUN_DIAGNOSTIC.bat`，並讓 `RUN_WINDOWS.bat`/`RUN_DEMO_WINDOWS.bat` 結束時停留畫面。
