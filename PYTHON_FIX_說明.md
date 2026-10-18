# Strata Easy TW 1.2.0-rc1 – Python 偵測修復

## 根因

RC1 的 RUN_WINDOWS.bat、RUN_DEMO_WINDOWS.bat、BUILD_WINDOWS_EXE.bat 只呼叫 py -3.12 或 py -3.11；bootstrap_windows.py 再度排除其他版本。這會把有 Python 3.10/3.13、只有 PATH 中 python.exe、未安裝 py Launcher 的電腦誤判為「沒有 Python 3.12」。

## 修正

- 新增 LAUNCH_WINDOWS.bat 共用偵測邏輯，三個入口統一呼叫。
- 支援 64 位元 CPython 3.10/3.11/3.12/3.13。
- 支援 py Launcher、PATH 上的 python/python3，以及環境變數 STRATA_GUIDE_PYTHON 指定絕對路徑。
- 啟動器不會自行更動系統 Python 的版本或套件，仍使用獨立 .guide-venv。
- 增加核心 Python 相容性單元測試；原始碼測試不等同於 Windows 實機通過。

## 你先試這樣

1. 從 ZIP 取出完整資料夾（不用替換你原本 Strata 的資料夾）。
2. 雙擊 RUN_DEMO_WINDOWS.bat，確認 Python 偵測與 UI 可開啟。
3. 如果仍失敗，開 CMD 檢查 `py -0p`、`python --version`、`where python`，將結果貼回。
4. 若發現你只有 3.14 或 32 位元 Python，本版不自動使用；需使用相容的 x64 Python。

提醒：官方 Strata 安裝器的 Python 環境與我們的中文導覽器 Python 環境不同。
