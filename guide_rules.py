"""Conservative Chinese commentary for upstream Strata installer stdout.

The output is untrusted. We never execute commands parsed out of output and we never
pretend to know an upstream decision. If no phrase is recognised, retain the last
known stage and ask the user to consult the original terminal.
"""
from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Guide:
    code: str
    title: str
    body: str
    next_step: str
    progress: int


GUIDES: dict[str, Guide] = {
    'welcome': Guide('welcome', '等待開始', '左邊會執行真正的 Strata 官方安裝程式；右邊只提供中文說明。所有選項仍由你親自決定。', '選擇安裝資料夾，或選擇既有的 Strata 資料夾。', 0),
    'source': Guide('source', '取得官方原始碼', '從 Niko1221/Strata 的 GitHub 官方倉庫下載某個固定 commit 的 ZIP。導覽器不修改原始安裝檔案。', '下載完成後會開始執行 START-HERE.bat。', 8),
    'existing': Guide('existing', '偵測到可能已部署的 Strata', '資料夾含有模型啟動檔或模型設定。官方程式通常會直接啟動既有模型，略過第一次才需要做的 GPU、下載、MTP 等步驟。這不代表導覽器漏掉畫面。', '若只是要使用既有模型，請沿用官方設定；需要重選模型才主動勾選「--setup」。', 13),
    'already_running': Guide('already_running', '本機已有 AI 聊天服務', '8080 已有服務回報 ready，不能將它當成本次安裝成功的證據。本導覽器沒有再次啟動另一份 Strata。', '可以檢查並開啟現有網頁；如要啟動另一份，先停止原本使用 8080 的程序。', 0),
    'port_busy': Guide('port_busy', '8080 已被其他程式占用', '目前無法確認占用連接埠的程式身分。為避免雙重啟動或錯誤歸因，導覽器停止了這次啟動。', '先結束占用 8080 的程序，再由導覽器執行官方安裝。', 0),
    'speed': Guide('speed', '選擇實驗性加速', '官方正在詢問是否啟用實驗性 speed projection；這可能改變回覆品質或相容性。', '不確定時沿用左側官方預設，不會自動替你啟用。', 50),
    'demo_ready': Guide('demo_ready', '離線展示完成', '這次只有重播模擬日誌，沒有執行官方程式、下載模型或檢查本機服務。', '可以切換其他展示情境，或關閉後啟動實際安裝模式。', 100),
    'cancelled': Guide('cancelled', '工作已取消', '已停止這次導覽工作。官方模型檔案未刪除；若要續傳，重新啟動官方腳本。', '檢查日誌，確認停止狀態後再重試。', 0),
    'startup': Guide('startup', '正在啟動官方安裝精靈', '左側是 Strata 官方程式的實際輸出。請閱讀選項並在左側下方輸入，或直接按 Enter 接受預設值。', '等待官方程式輸出下一個問題。', 12),
    'hardware': Guide('hardware', '正在檢查電腦硬體', 'Strata 正在辨識 CPU、顯示卡、顯示記憶體、系統 RAM、驅動與磁碟空間。硬體不合需求時應以官方警告為準。', '等待偵測結果；不用急著輸入。', 18),
    'family': Guide('family', '請選擇模型系列', '此處選的是模型「種類」，不是模型大小。不同系列可能有不同的擅長用途與授權。', '看左邊編號與預設選項，輸入對應數字或按 Enter。', 25),
    'size': Guide('size', '請選擇模型大小', '量化越精細通常能保存更多模型資訊，但會占用更多 RAM／磁碟空間。請優先看左側官方依你的硬體提供的建議，並保留系統記憶體餘裕。', '請依左側當前選單選擇；右側不會代替你選模型。', 30),
    'context': Guide('context', '正在設定 Context 長度', 'Context 是 AI 能同時處理的上下文長度。較大的數值可能提高 KV Cache 的 RAM／VRAM 使用量；新手通常可先接受官方建議。', '可直接按 Enter 使用官方預設值。', 39),
    'vision': Guide('vision', '選擇是否啟用圖片理解', 'Vision 讓 AI 可以閱讀照片與圖片。是否支援由硬體、模型及官方安裝流程決定；可能需要額外下載元件。', '依左側提示輸入 yes/no 或按 Enter；不要猜選項格式。', 47),
    'download': Guide('download', '正在下載大型模型', '模型常有數十 GB，下載速度取決於網路及來源伺服器。先不要關閉視窗，某些階段可能長時間沒有新訊息。', '等待下載；若中斷，官方安裝器通常可再次執行以續傳。', 57),
    'environment': Guide('environment', '正在準備執行環境', '官方腳本正在安裝或檢查 Python、相依套件或推論引擎元件。Windows 可能詢問權限或顯示額外安裝訊息。', '等待官方環境部署完成。', 64),
    'pack': Guide('pack', '正在建立模型 Pack', 'Strata 正在把下載的 GGUF 整理成適合引擎執行的資料結構。這段可能大量讀寫 SSD。', '等待封裝結束，勿強制關閉。', 76),
    'mtp': Guide('mtp', '正在準備 MTP 加速', 'MTP 是模型推論時可能使用的草稿／預測加速機制；它不是另一個聊天模型。是否啟用、是否下載由官方腳本決定。', '請等待官方 MTP 步驟完成。', 83),
    'calibration': Guide('calibration', '正在測量或調校效能', '安裝器可能會測試 GPU、CPU 或推論速度，找出較適合這台電腦的設定。此時短時間高負載是可能的。', '請等待測試或按左側的官方選項回覆。', 88),
    'starting': Guide('starting', '正在載入 Strata 模型', '大模型載入 RAM／VRAM 時可能花數十秒到數分鐘。只有確定本地服務已準備好，才算可以使用。', '等待左側出現 ready 訊息；可按「檢查並開啟聊天網頁」。', 93),
    'ready': Guide('ready', '聊天服務已就緒', '本機 /health 回報 status=ok 且 loaded=true；這只是端點狀態，未核對服務 PID，也不等於完整安裝驗收。', '點選「開啟本地聊天網頁」，使用時請保持官方程序開啟。', 100),
    'error': Guide('error', '官方程序可能發生錯誤', '偵測到疑似失敗訊息。請檢查左側實際錯誤內容；右側解說不是官方診斷。', '可複製日誌排查，或回到官方文件尋求協助。', 0),
    'stopped': Guide('stopped', '官方程序已結束', 'Strata 程序已離開。若沒有確認服務 ready，請參考終端機最後的訊息。', '如需再次使用，請啟動官方 START-HERE.bat 或 run-*.bat。', 0),
}

# Ordering is important: exact prompts first, general informational lines later.
RULES: tuple[tuple[str, tuple[str,...]], ...] = (
    ('family', (r'(which|choose|select|pick)\s+.*(model\s+(family|version)|family)', r'模型系列', r'which\s+model\s*\?')),
    ('size', (r'(which|choose|select|pick)\s+.*(model\s+size|size|quant)', r'model\s+size\s*[:?]', r'quantization\s*[:?]')),
    ('context', (r'(how\s+much|choose|select|enter).*context', r'context\s+(length|size|window|tokens)\s*[:?]', r'context\s*\(.*\)', r'context\s*\?')),
    ('vision', (r'(images?|vision)\s*\?\s*(\[|\(|$)', r'(enable|use|read|process).*images?\s*\?', r'(enable|use)\s+vision')),
    ('mtp', (r'\bmtp\b.*\b(download|install|prepar|setup|build|load|pack)', r'(download|install|prepar|setup|build|load|pack).*\bmtp\b')),
    ('speed', (r'(turn on|enable).*experimental speed projection\s*\?',)),
    ('calibration', (r'\b(calibrat|benchmark|tuning)\b', r'\bcalibrat\w*')),
    ('pack', (r'\b(prepar|build|creat|writ|conver|pack)\w*\b.*\b(native\s+)?pack\b', r'\bpack(ing)?\s+(expert|model|weight)', r'\biq[_-]?pack\b')),
    ('download', (r'\bdownloading\b', r'\b(download|fetch)\w*\s+.*(model|gguf|shard|weight)', r'\bhugging\s*face\b.*\b(download|fetch)', r'\b\d+(?:\.\d+)?\s*(?:gb|gib|mb|mib)\s*/\s*\d+(?:\.\d+)?\s*(?:gb|gib|mb|mib)\b')),
    ('environment', (r'\b(install|setting up|prepar)\w*\b.*\b(python|pytorch|cuda|dependency|dependencies|venv|engine)\b', r'\b(create|build)\w*\b.*\b(venv|engine)\b')),
    ('hardware', (r'\b(check|detect|prob|inspect)\w*\b.*\b(hardware|gpu|vram|cpu|ram|memory|driver|disk)\b', r'\bhardware\s+check\b')),
    ('starting', (r'\b(starting|launching|loading)\b.*\b(server|model|strata)\b', r'\bwaiting\b.*\bserver\b', r'\b127\.0\.0\.1:8080\b')),
)

COMPILED = tuple((key, tuple(re.compile(p, re.IGNORECASE) for p in patterns)) for key,patterns in RULES)
ERROR_RE = re.compile(r'(?:^|[\s\[(])(?:fatal\s+error|traceback|installation\s+failed|download\s+failed|\berror\s*:|\[error\])', re.IGNORECASE)

class PlainStream:
    """Stateful stripping of CSI/OSC/DCS, including split escape sequences."""
    def __init__(self): self.state='text'
    def feed(self, data):
        out=[]
        for ch in data:
            if self.state=='esc':
                self.state={'[':'csi',']':'osc','P':'osc','^':'osc','_':'osc'}.get(ch,'text')
            elif self.state=='csi':
                if '@'<=ch<='~': self.state='text'
            elif self.state=='osc':
                if ch=='\x07': self.state='text'
                elif ch=='\x1b': self.state='osc_esc'
            elif self.state=='osc_esc': self.state='text' if ch=='\\' else 'osc'
            elif ch=='\x1b': self.state='esc'
            elif ch in '\r\n': out.append('\n')
            elif ch=='\t' or ch>=' ' and ch!='\x7f': out.append(ch)
        return ''.join(out)

class StageTracker:
    def __init__(self):
        self.state=GUIDES['welcome']
        self.recent=''
        self.plain=PlainStream()

    def feed(self, text):
        fresh=self.plain.feed(text)
        if not fresh: return None
        previous=self.recent[-800:]
        sample=previous+fresh
        boundary=len(previous)
        candidates=[]
        for priority,(key,patterns) in enumerate(COMPILED):
            for pattern in patterns:
                for match in pattern.finditer(sample):
                    if match.end()>boundary:
                        candidates.append((match.start(), -priority, key))
        for match in ERROR_RE.finditer(sample):
            if match.end()>boundary: candidates.append((match.start(),1000,'error'))
        # A read may begin a new line even when a fixture omits its newline.
        # Prefer complete matches in fresh text, but still match split prompts.
        for priority,(key,patterns) in enumerate(COMPILED):
            for pattern in patterns:
                for match in pattern.finditer(fresh):
                    candidates.append((boundary+match.start(),-priority,key))
        for match in ERROR_RE.finditer(fresh):
            candidates.append((boundary+match.start(),1000,'error'))
        self.recent=sample[-2000:]
        if not candidates: return None
        key=max(candidates)[2]
        if key==self.state.code: return None
        self.state=GUIDES[key]
        return self.state

    def set(self, code):
        self.state=GUIDES[code]
        return self.state
