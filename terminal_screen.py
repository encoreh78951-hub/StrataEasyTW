"""VT model with cursor movement, erasure, colour and bounded scrollback.
OSC title/clipboard commands are not executed. Not an xterm graphics host.
"""
import app_config
import copy
import pyte

class TerminalScreen:
    def __init__(self, max_lines=1600, columns=100, rows=30, reply=None):
        self.max_lines = max_lines
        self.vt = pyte.HistoryScreen(columns, rows, history=max_lines)
        if reply is not None:
            self.vt.write_process_input = reply
        self.stream = pyte.Stream(self.vt)

    def feed(self, data):
        self.stream.feed(data)

    def resize(self, rows, columns):
        # pyte clips the top even when only unused bottom rows need removal.
        # Preserve output during panel/window resizing and archive real overflow.
        cursor_y = self.vt.cursor.y
        if rows < self.vt.lines:
            last_used = max(cursor_y + 1, max((y + 1 for y, line in self.vt.buffer.items()
                if any(c.data.strip() or c.bg != 'default' for c in line.values())), default=1))
            intermediate = max(rows, last_used)
            for y in range(intermediate, self.vt.lines):
                self.vt.buffer.pop(y, None)
            self.vt.lines = intermediate
            overflow = intermediate - rows
            for y in range(overflow):
                self.vt.history.top.append(copy.copy(self.vt.buffer[y]))
            cursor_y = max(0, cursor_y - overflow)
        self.vt.resize(lines=rows, columns=columns)
        self.vt.cursor.y = min(rows - 1, cursor_y)
        self.vt.cursor.x = min(columns - 1, self.vt.cursor.x)

    def _rows(self):
        return list(self.vt.history.top) + [self.vt.buffer[y] for y in range(self.vt.lines)]

    @property
    def lines(self):
        lines = [''.join(row[x].data for x in range(self.vt.columns)).rstrip() for row in self._rows()]
        used = max(self.vt.cursor.y+len(self.vt.history.top)+1,
                   max((i+1 for i, line in enumerate(lines) if line), default=1))
        return lines[:used][-self.max_lines:]

    def text(self):
        return '\n'.join(self.lines)

    def snapshot(self):
        rows = self._rows()
        used = max(self.vt.cursor.y+len(self.vt.history.top)+1,
                   max((i+1 for i, r in enumerate(rows) if any(c.data.strip() for c in r.values())), default=1))
        result = []
        for row in rows[:used][-self.max_lines:]:
            runs = []
            text, prev = '', None
            chars = [row[x] for x in range(self.vt.columns)]
            end = max((i+1 for i, c in enumerate(chars) if c.data.strip() or c.bg != 'default'), default=0)
            for c in chars[:end]:
                style = (c.fg, c.bg, c.bold, c.reverse)
                if style != prev and text:
                    runs.append((text, prev)); text = ''
                text += c.data
                prev = style
            if text: runs.append((text, prev))
            result.append(runs)
        return result
