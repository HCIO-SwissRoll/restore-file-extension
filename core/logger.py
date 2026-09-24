"""日志模块：同时输出到控制台和日志文件"""

import sys
from datetime import datetime


COLORS = {
    'red':    '\033[91m',
    'green':  '\033[92m',
    'yellow': '\033[93m',
    'cyan':   '\033[96m',
    'reset':  '\033[0m',
}

# 颜色 -> 日志级别标签（写入日志文件时使用）
LEVEL_LABEL = {
    'reset':  'INFO',
    'red':    'ERROR',
    'green':  'OK',
    'yellow': 'WARN',
    'cyan':   'INFO',
}


class Logger:
    """
    同时写入控制台与日志文件。
    - 控制台：可选颜色、可选静默
    - 日志文件：纯文本，带时间戳和级别标签，始终记录完整内容
    """

    def __init__(self, log_path=None, use_color=True, quiet=False, enable_file=True):
        self.use_color = use_color
        self.quiet = quiet
        self._file = None
        self.log_path = None

        if enable_file:
            if log_path is None:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                log_path = f"restore_ext_{ts}.log"
            self.log_path = log_path
            try:
                self._file = open(log_path, 'w', encoding='utf-8')
                self._file.write(f"# restore_ext 日志 - 开始于 {datetime.now():%Y-%m-%d %H:%M:%S}\n")
                self._file.flush()
            except Exception as e:
                # 无法打开日志文件时降级为仅控制台
                print(f"警告: 无法创建日志文件 {log_path}: {e}", file=sys.stderr)
                self._file = None

    # ---------- 内部 ----------
    def _write(self, text, color):
        # 写文件
        if self._file:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            level = LEVEL_LABEL.get(color, 'INFO')
            self._file.write(f"[{ts}] [{level}] {text}\n")
            self._file.flush()

        # 写控制台
        if not self.quiet:
            if self.use_color and color in COLORS and color != 'reset':
                print(f"{COLORS[color]}{text}{COLORS['reset']}")
            else:
                print(text)

    # ---------- 对外接口 ----------
    def info(self, text):    self._write(text, 'reset')
    def error(self, text):   self._write(text, 'red')
    def success(self, text): self._write(text, 'green')
    def warn(self, text):    self._write(text, 'yellow')
    def notice(self, text):  self._write(text, 'cyan')

    def close(self):
        if self._file:
            self._file.write(f"# 日志结束于 {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            self._file.close()
            self._file = None

    # 支持 with 语句
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()