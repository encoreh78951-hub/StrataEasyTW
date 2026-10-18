"""Author-written Chinese plain-language step guidance; does not translate untrusted terminal output blindly."""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class BeginnerHint:
    action: str
    wait: str
    detail: str
    caution: str

HINTS = {
 'speed':BeginnerHint('依官方提示選擇是否啟用，預設不替你回答。','等待你輸入。','實驗性投影加速可能影響品質與相容性。','請先閱讀官方的實驗性功能說明。'),
 'demo_ready':BeginnerHint('可改播其他展示情境。','展示已結束。','這是離線模擬，未檢查服務、未安裝模型。','請用實際安裝模式才能執行官方腳本。'),
 'cancelled':BeginnerHint('確認停止後可重新啟動。','取消已完成。','取消不會刪除既有模型。','下載能否續傳由官方安裝程式決定。'),
 'welcome':BeginnerHint('先選擇「新下載」或「使用已安裝的 Strata」，再選資料夾。', '目前不需要等待。', '這套程式只是協助你看懂官方流程，不會偷偷回答 Y。', '真正的模型可能需要數十 GB，請先確認 SSD 容量。'),
 'source':BeginnerHint('先等待程式下載 GitHub 官方原始碼。', '通常比模型下載快很多，實際取決於網路。','這只是原版 Strata 的安裝程式，模型檔案會由官方腳本另外取得。','若網路中斷，不要直接刪除已有的其他 Strata 資料夾。'),
 'existing':BeginnerHint('若你只想聊天，直接啟動原有模型即可；不需要重裝。','通常幾十秒到數分鐘，依硬體和模型大小而異。','已安裝的 Strata 可能直接跳過首次設定；這是正常行為。','不要勾選重新設定，也不要隨意更改 GPU，除非你真的想改。'),
 'startup':BeginnerHint('看左側是否出現「Which ...?」之類問題；有預設值時可以按 Enter。','啟動前可能先檢查套件或環境。','左側每一個問題都是真正的官方程式，不是我們模擬出來的問答。','遇到不懂的問題可以先停下來看右側解說。'),
 'hardware':BeginnerHint('現在只要等官方偵測；若出現問號或編號選項再回答。','可能需要數秒到數十秒。','CPU 是處理器，GPU 是顯示卡，RAM 是系統記憶體，VRAM 是顯示卡記憶體。','硬體是否足夠以官方輸出為準，別只看你有幾 GB RAM。'),
 'family':BeginnerHint('依左側顯示的編號選擇模型系列；不確定時按 Enter 採官方推薦。','等待你輸入。','模型系列代表不同版本、設計與回覆特性；不是記憶體大小。','這是官方模型，並不代表會安裝 SC117 Abliterated。'),
 'size':BeginnerHint('查看官方標示的推薦項目；若不了解量化，可先按 Enter。','等待你輸入。','Q2/IQ2 通常比較節省 RAM，IQ3 通常保留更多精度。差異要用相同測試任務才知道。','預留其他程式的 RAM；容量剛好卡線時可能嚴重變慢。'),
 'context':BeginnerHint('新手先按 Enter 使用 Strata 推薦的 Context。','等待你輸入。','Context 就像桌上的工作空間，越長可以同時放越多對話與文件，但 RAM/VRAM 成本可能增加。','不是越大越聰明；32K 不夠時可以後續再調。'),
 'vision':BeginnerHint('想讓 AI 看圖片，就依官方問題選 yes；若不確定，先用預設。','等待你輸入。','Vision 是圖片理解，可讓模型處理圖片內容，可能多下載圖片編碼器。','圖片理解會多用資源，不等於生成圖片。'),
 'download':BeginnerHint('不用輸入，也不要關閉程式；請耐心等候。','70GB 左右的大模型下載可能花數十分鐘或數小時。','下載總量、速度和剩餘時間請看左側官方數字；右側流程條不是檔案下載進度。','進度短暫停住不一定是壞掉，下載中斷通常可重新執行官方腳本續傳。'),
 'environment':BeginnerHint('等官方把執行環境準備好。','幾分鐘到更久，取決於網路與磁碟速度。','這一步可能安裝 Python、推論引擎等執行工具。','若出現錯誤，保留原文並查看日誌，勿隨意複製不明網路指令。'),
 'pack':BeginnerHint('不要操作，請讓 Strata 完成模型封裝。','可能需要數分鐘或更久。','Pack 是把 GGUF 轉成 Strata 引擎使用的索引/資料格式，磁碟可能持續大量讀寫。','不要在封裝中途強制關閉、拔 SSD 或刪暫存資料。'),
 'mtp':BeginnerHint('不必按鍵，等待 MTP 準備完畢。','視下載與處理速度可能需要幾分鐘。','MTP 是加速文字生成的輔助預測元件；不是又在下載完整 125B 模型。','不同 Strata 版本不一定都有完全相同的 MTP 步驟。'),
 'calibration':BeginnerHint('等待測試完畢。','可能需 5–10 分鐘，也可能因版本不同而變動。','官方在測量這台電腦的推論參數，CPU/GPU 暫時提高負載是正常的。','此時電腦變慢不代表程式壞掉。'),
 'starting':BeginnerHint('等模型載入完成；等到本機 /health 回報 loaded=true 再開網頁。','官方指出首次載入可能需要 1–3 分鐘。','模型要先讀入系統記憶體和顯示卡，這個過程不是重新下載。','如果 RAM 不足會很慢，請先關閉不必要的軟體。'),
 'ready':BeginnerHint('按「開啟本地聊天網頁」，就能開始使用。','已經就緒。','127.0.0.1 是這台電腦自己，不是公開的網路服務。','聊天時要保持執行 Strata 的終端機開啟。'),
 'already_running':BeginnerHint('若想使用現有模型，按「檢查並開啟聊天網頁」。','已經有一個服務在執行。','已有服務並不表示本次導覽器剛完成新安裝。','請勿為了測試隨意關閉你原本正常工作的模型。'),
 'port_busy':BeginnerHint('先確認 8080 是哪個程式在使用，再決定是否關閉。','等待你處理。','同一個連接埠無法同時讓兩個 Strata 服務占用。','不要直接終止不認識的 Windows 程序。'),
 'error':BeginnerHint('先複製最後的官方日誌，再查詢具體錯誤。','等待排除。','常見原因是網路下載、磁碟不足、顯示卡驅動或環境套件。','不要因為看見 ERROR 就立刻刪除數十 GB 模型。'),
 'stopped':BeginnerHint('若還沒看到就緒訊息，請先閱讀官方終端機最後幾行。','程序已結束。','離開可能是正常結束，也可能是安裝失敗，不能只看視窗關閉判定。','停止 Strata 後本地聊天頁面通常無法再回答。')
}

# Specific English log fragments -> optional extra explanation. Exact prose is authored here.
TRANSLATIONS = (
 (r'which\s+(gpu|gpus)|which graphics card', '正在請你選擇使用哪張顯示卡，請看官方編號；多顯卡不一定更快。'),
 (r'which\s+model|choose.*model', '正在詢問模型類型或大小；不確定時可採用官方建議。'),
 (r'context', '目前涉及上下文長度設定；越長可能占用更多記憶體。'),
 (r'\b(images?|vision)\b', '這裡與圖片理解功能有關；不是圖片生成。'),
 (r'\bmtp\b', '目前涉及 MTP 生成加速元件。'),
 (r'\b(download|fetch)\w*\b', '官方正在下載檔案；實際進度請看左側數值。'),
 (r'\b(pack|prepare|convert|build)\w*\b', '正在準備模型或程式元件，可能會使用大量 SSD 資源。'),
 (r'\b(starting|loading|launching)\b', '可能正在載入服務與模型，請等待。'),
 (r'\b(error|failed|traceback)\b', '這行包含疑似錯誤，請保存官方原文以便查找問題。'),
)
_COMPILED = [(re.compile(p,re.I),t) for p,t in TRANSLATIONS]

def explain_excerpt(raw: str) -> tuple[str,str]:
    """Return bounded raw line and a hint, never invent an exact translation."""
    lines=[re.sub(r'\x1b\[[0-9;?]*[ -/]*[@-~]','',x).strip() for x in raw.splitlines()]
    lines=[x for x in lines if x and not x.startswith('[導覽器]')]
    if not lines:
        return '等待官方訊息…','尚未收到需要解釋的英文訊息。'
    line=lines[-1][:240]
    for pattern, hint in _COMPILED:
        if pattern.search(line):return line,hint
    return line,'這行未匹配到已知說明；請以左側官方原文為準。'

GLOSSARY = (
 ('模型系列', '不同用途與特性的版本，例如官方原版或微調版。'),
 ('量化（Q2 / IQ3）', '把模型權重以較少位元儲存，減少記憶體使用，但可能損失精度。'),
 ('RAM / VRAM', 'RAM 是電腦主記憶體，VRAM 是顯示卡上的記憶體。兩者都可能影響模型配置。'),
 ('Context', '單次請求能同時處理的對話、文件與圖片等上下文。'),
 ('Vision', '讓模型理解圖片，而不是生成圖片。'),
 ('MTP', 'Multi-Token Prediction：模型生成時的加速方法。'),
 ('Pack', 'Strata 將模型檔案準備成引擎能使用的結構。'),
 ('127.0.0.1:8080', '只有這台電腦的本地網址；要讓其他裝置連線需另作安全設定。'),
)
