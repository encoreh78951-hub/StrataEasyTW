# 1.2.0-rc1

- 以使用者上傳 v1.1 多檔案整合重構，保留原始上傳版本。
- 賽博龐克雙欄 UI、收合設定、捲動教學、3D 風格六姿態小雪與減少動態。
- 真實 ConPTY 互動、VT 顏色與游標、縮放保留輸出，不自動回答問句。
- 執行緒事件隔離、取消／重啟、舊事件排除、錯誤／退出狀態、既有服務防護。
- 官方 commit、安全 ZIP 解壓、防覆蓋、來源雜湊與限流說明。
- Windows 建置、繁中每位使用者安裝器、授權收集與可替換 LGPL 來源。
- 回歸測試及實際離線 UI 檢查；Windows EXE 和模型端到端尚未驗證。


## 1.2.0-rc1 Python 偵測修復（2026-10-18）

- 修正啟動 BAT 只接受 `py -3.12`／`py -3.11`，導致已安裝 3.10／3.13 或無 Launcher 的使用者被誤判。
- `RUN_WINDOWS.bat`、`RUN_DEMO_WINDOWS.bat`、`BUILD_WINDOWS_EXE.bat` 共用 `LAUNCH_WINDOWS.bat`。
- 自動辨識 CPython 3.10–3.13 x64，支援 `python`／`python3` PATH 與明確指定 `STRATA_GUIDE_PYTHON`。
- `bootstrap_windows.py` 保留專屬 `.guide-venv`，若檢測到不同 Python 版本的舊虛擬環境會顯示可執行的復原方法。
- 加入 Python 啟動器測試；Windows BAT 行為仍需在 Windows 實機驗證。


### BAT 視窗瞬間關閉的診斷修復
- 新增 RUN_DIAGNOSTIC.bat：列出 Python 偵測狀態、完整堆疊與啟動記錄。
- RUN_WINDOWS.bat 和 RUN_DEMO_WINDOWS.bat 結束時不會瞬間消失。
- 明確偵測未解壓縮／缺少 app.py 等情況。

## 1.2.0-rc2｜發佈工作流程

- 新增 Windows 3.10/3.12/3.13 CI，自動測試 ConPTY 模擬互動、EXE 與 Windows 安裝包。
- 加入檢查輸出是否完整的發佈閘門，以及 SHA256、授權與檔案清單。
- 通過全部 CI 後才產生 GitHub Draft Prerelease，不會自動標為穩定版。
- 移除專門針對開發者個人電腦的隔離測試交接要求。
