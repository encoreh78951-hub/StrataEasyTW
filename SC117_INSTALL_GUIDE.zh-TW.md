# 模型來源選擇｜Strata Easy TW 1.3.0-rc1

本專案是**非官方**繁體中文導覽工具，並非 Strata、Qwen 或 SC117 的官方發行者。模型權重均在使用者選擇後由原始來源下載，本專案不附帶任何 GGUF 權重。

## 有哪兩個選擇？

**官方標準模型（預設）**：Strata 官方 `START-HERE.bat` 自行詢問模型系列、量化及其他設定。本工具只負責顯示終端機和中文解說，不改變官方預設。

**SC117 第三方低拒答版本（實驗性）**：使用者自行選擇 Q2_0、IQ2_XS、IQ3_XXS 或 IQ3_S。導覽器會讀取 Hugging Face 的模型版本與兩個分片的大小、LFS SHA-256，下載到 `.part` 暫存檔；續傳、大小和完整 SHA-256 驗證成功後才改名為 `.gguf`。完成後啟動原版 `START-HERE.bat --setup --family qwen --model ... --gguf-dir ... --data-dir ...`，由 Strata 官方程式處理本機 GGUF 和專用 Pack。

「Abliterated／低拒答」是第三方改寫模型的名稱與特性說明，**並不等於保證完全不拒答**。其他風險、相容性、內容品質仍需依模型卡和官方資料判斷。

來源：https://huggingface.co/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF

## 檔案存放位置

標準模型仍遵循 Strata 官方的資料夾與設定。

SC117 使用者所選根目錄下的：

```text
Strata-Easy-TW-SC117/
  Strata-Official/    ← 從原版 GitHub 取得的官方 Strata
  SC117-GGUF/
    IQ2_XS/           ← 選定量化的兩個 GGUF 分片與來源紀錄
  Strata-data/        ← SC117 專屬 Pack、設定與執行資料
```

這是**不同模型必須隔開 Pack 的一般產品設計**，不是針對開發者電腦量身製作的測試隔離。不得將舊標準模型的 Pack 直接套用到 SC117。

若下載中斷，保留 `.part`，重新選相同根目錄和量化再開始。導覽器會再次比對遠端 SHA-256 和檔案大小。來源改版、驗證不符、磁碟空間不足或 HTTP 不支援續傳時會停止；**不會偷偷換成官方標準權重繼續安裝**。

## 資源與風險

每種量化都是兩個大型分片，總下載量約數十 GB，Pack、MTP、索引及暫存可能需要額外數十 GB。UI 的磁碟預留建議只是粗略估計，實際應以當次 Strata 與模型來源為準。穩定的高速 SSD 很重要。

SC117 從 Hugging Face 下載時需能連線該網站及其 HTTPS 下載轉址服務。檔案大，可能耗費數小時。若無法使用網路或來源變更，導覽器會顯示錯誤；不會把未驗證的檔案交給 Strata。

## 目前測試限制

已在原始碼層進行：模式分支、量化白名單、官方啟動參數、來源檔案資訊驗證、SHA-256、HTTP Range 續傳、下載失敗不啟動官方程式、獨立目錄選擇和小雪提示測試。

**尚未**在 Windows 下載完整 SC117（數十 GB）分片、完成原生 Pack、MTP、健康檢查和實際推論，因此此模式標註**實驗性 Beta**。GitHub Actions 雲端綠燈仍只代表合成測試與 Windows EXE 建置成功，不是完整模型安裝已驗收。
