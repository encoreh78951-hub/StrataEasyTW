"""Six prerendered 3D poses; a sprite UI, not a real-time 3D mesh."""
import math
import tkinter as tk
from PIL import Image, ImageTk
from app_config import resource
POSES = ('welcome', 'explain', 'working', 'waiting', 'concerned', 'success')
STAGE_POSES = {
    'welcome': 'welcome', 'source': 'working', 'sc117_download':'waiting',
    'sc117_prepare':'working', 'existing': 'explain',
    'startup': 'explain', 'hardware': 'working', 'family': 'explain',
    'size': 'explain', 'context': 'explain', 'vision': 'explain',
    'speed': 'explain', 'download': 'waiting', 'environment': 'working',
    'pack': 'working', 'mtp': 'working', 'calibration': 'working',
    'starting': 'waiting', 'ready': 'success', 'demo_ready': 'success',
    'already_running': 'explain', 'port_busy': 'concerned',
    'error': 'concerned', 'stopped': 'waiting', 'cancelled': 'waiting',
}
TIPS = {
    'welcome': '嗨，我是小雪！選好資料夾後，我會陪你看懂每一步。',
    'source': '先取得官方程式。這一步還沒有下載大型模型喔。',
    'existing': '找到舊部署了！沿用原設定，就不用重新選模型。',
    'sc117_download':'正在下載 SC117 的兩個分片，完成後會核對雜湊；可續傳喔。',
    'sc117_prepare':'這次用的是第三方模型，Pack 要重新建，不能沿用標準版的。',
    'startup': '我準備好了。出現選單時，在左側輸入你的選擇。',
    'hardware': '讓官方檢查這台電腦。顯卡、RAM 和 SSD 都很重要。',
    'family': '這次選的是模型系列。先看用途，再看官方推薦的編號。',
    'size': '這次選的是量化大小。記得替其他程式留一些 RAM。',
    'context': 'Context 是同時能處理的文字量；先用官方建議就好。',
    'vision': '想讓 AI 看圖片嗎？請依左側的選項格式回答。',
    'speed': '這是實驗性加速。不了解時，可以保留官方預設。',
    'download': '下載要一點耐心，我陪你等。實際進度請看左邊。',
    'environment': '正在準備執行工具，這時先不用輸入。',
    'pack': '模型正在整理成 Pack，SSD 可能會忙一陣子。',
    'mtp': '正在準備加速元件，不是再裝一個完整聊天模型。',
    'calibration': '正在測試適合這台電腦的設定，讓它跑完。',
    'starting': '快了！等本機健康檢查確認，才知道服務能不能用。',
    'ready': '本機服務回報就緒！使用時，記得保持官方程序開啟。',
    'demo_ready': '示範走完啦！這只是離線演練，還沒有安裝模型。',
    'already_running': '8080 已有服務；我們先確認它，不重複啟動。',
    'port_busy': '8080 被占用了。先找出是哪個程式，再繼續。',
    'error': '先別急著重裝。匯出日誌，從最後一個錯誤找原因。',
    'stopped': '程序已結束。先看最後幾行，再決定是否重試。',
    'cancelled': '這次工作已取消。已下載的官方模型請交由官方續傳。',
}

class Mascot(tk.Canvas):
    def __init__(self, parent, bg, size=156):
        super().__init__(parent, width=size, height=size+10, bg=bg, highlightthickness=0)
        self.motion = True
        self.phase = 0
        self.job = None
        self.size = size
        self.images = {}
        with Image.open(resource('assets', 'xiaoxue-atlas.png')) as atlas:
            w, h = atlas.size
            for i, pose in enumerate(POSES):
                cell = atlas.crop((i%3*w//3, i//3*h//2, (i%3+1)*w//3, (i//3+1)*h//2))
                cell.thumbnail((size, size), Image.Resampling.LANCZOS)
                self.images[pose] = ImageTk.PhotoImage(cell, master=self)
        self.item = self.create_image(size//2, size//2+4, image=self.images['welcome'])
        self.pose = 'welcome'
        self.bind('<Destroy>', self._destroy)
        self._tick()

    def set_stage(self, code):
        self.pose = STAGE_POSES.get(code, 'explain')
        self.itemconfigure(self.item, image=self.images[self.pose])

    def _tick(self):
        self.phase += .09
        dy = math.sin(self.phase)*2 if self.motion else 0
        self.coords(self.item, self.size//2, self.size//2+4+dy)
        self.job = self.after(80, self._tick)

    def _destroy(self, event):
        if event.widget is self and self.job:
            self.after_cancel(self.job)
            self.job = None
