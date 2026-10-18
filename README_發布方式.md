# 公開發佈操作｜不需要在自己的電腦重新下載大型模型

> 本版為 Strata Easy TW **1.3.0-rc1（測試候選版）**，不等同已通過完整 Strata 首次安裝。

## 自動發佈流程

1. 在自己 GitHub 帳號建立新的公開或私人儲存庫，將本原始碼資料夾內容推上 `main`。不要上傳 `.guide-venv`、診斷日誌或個人資料。
2. 打開 GitHub 儲存庫的 **Actions → Windows QA and release-candidate artifacts → Run workflow**。
3. 等所有 Windows Jobs 綠燈。流程會使用 Windows 2022、Python 3.10／3.12／3.13 自動驗證，執行 ConPTY 模擬互動，使用 PyInstaller 和 Inno Setup 打包。**不會下載 125B 模型**。
4. 到執行紀錄的 **Artifacts** 下載 `Windows-RC-UNSIGNED`，裡面有 `Setup.exe`、`Portable.zip`、原始碼 ZIP、SHA256 與測試報告。若任一 Job 失敗，請先修正，不要發布。
5. 若想先建立 GitHub Release 草稿，可以推送與版本相符的 Git tag `v1.3.0-rc1`；全部 Windows QA 通過後會自動生成 **Draft + Prerelease**（不會公開）。你只要檢查發佈文字後，在 GitHub 按「Publish release」，就能提供候選版下載。

## 在 GitHub 建立 tag（僅需一次）

```bash
git tag v1.3.0-rc1
git push origin v1.3.0-rc1
```

**切勿稱為「已通過完整首次安裝」或「正式穩定版」：** 雲端測試不含完整模型下載、不同硬體效能、Windows 10 多種配置、SmartScreen / 防毒軟體與長時間穩定度。

## 使用者看到的版本聲明

- 非官方繁體中文安裝導覽器；不是 Strata、Qwen 或 SC117 官方產品。
- 保留官方 `START-HERE.bat` 安裝互動；第三方模型仍有各自授權。
- 本預覽版可能有未發現的相容性問題；使用者可以到 GitHub Issues 回報。
- 未經簽章的 EXE 可能出現 Windows SmartScreen 警示，不應引導使用者關閉防毒軟體或繞過安全機制。

## 將來升級到正式穩定版的條件

除了現有 CI，仍需透過願意參與的測試者或專業 Windows 測試環境驗證完整部署與法律合規。**使用者本人不必負責測試。**

## 1.3.0-rc1：模型來源選擇說明

新增官方標準版／SC117 第三方低拒答版選擇，以及 SC117 量化、GGUF 續傳與 SHA-256、獨立 Pack 流程。Windows CI 僅測試模擬下載器與參數組合，不下載 70–85 GB GGUF，也不驗證 SC117 真實模型推論；此功能目前是 **實驗性 Beta**。
