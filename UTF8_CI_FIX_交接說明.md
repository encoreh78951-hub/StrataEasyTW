# GitHub Windows `UnicodeEncodeError: cp1252` 修復說明

## 根因

Windows runner 在 PowerShell/Python CLI 執行 `tools/release_gate.py --source-check` 時，Python 的輸出編碼可能是 `cp1252`。`json.dumps(..., ensure_ascii=False)` 產生繁體中文字元，在 stdout 寫入時發生 `UnicodeEncodeError`，所以三個 Python 版本都可能一起失敗。

## 修正

- `tools/release_gate.py`：Console JSON 改用 `ensure_ascii=True`；檢查本身與退出碼不變。JSON 檔案仍維持 UTF-8 中文內容。錯誤輸出也改為無法編碼時安全跳脫。
- `.github/workflows/build-windows.yml`：所有 Windows CI job 設定 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`。
- `tests/test_release_gate.py`：新增 `cp1252` 模擬測試，涵蓋成功與錯誤輸出。

## 上傳回 GitHub

1. 解壓縮「快速覆蓋包」到 GitHub Desktop 管理的 `StrataEasyTW` 專案**根目錄**，保留子資料夾結構並允許覆蓋。
2. GitHub Desktop 左下角 Summary 輸入 `Fix Windows CI cp1252 output`。
3. 按 **Commit to main**，再按 **Push origin**。
4. GitHub 網站 → 專案 → Actions。`main` 的 push 會自動啟動新的 Windows 測試，不用再次手動按 Run workflow。
5. 如果下一次仍出現紅色叉叉，展開**新的**失敗步驟，將詳細錯誤訊息貼回聊天。新的錯誤可能與 cp1252 無關。

## 驗收邊界

這次只修正 Windows CI 的控制台編碼，不會修改 Strata 模型安裝、ConPTY 行為或已發布的執行檔。未在此環境實際執行 GitHub Windows runner，也不能提前保證打包工作全部通過。
