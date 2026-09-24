"""日志模块：同时输出到控制台和日志文件"""

import os
import sys
from datetime import datetime


COLORS = {
    'red':    '\033[91m',
    'green':  '\033[92m',
    'yellow': '\033[93m',
    'cyan':   '\033[96m',
    'reset':  '\033[0m',
}

LEVEL_LABEL = {
    'reset':  'INFO',
    'red':    'ERROR',
    'green':  'OK',
    'yellow': 'WARN',
    'cyan':   'INFO',
}

# 项目根目录 = core/ 的上一级目录（即与 restore_ext.py、table.json 同级）
_HERE = os.path.dirname(os.path.abspath(__file__))    # .../core
_ROOT = os.path.dirname(_HERE)                        # 项目根目录

# 日志目录（跟随脚本位置，固定为 <项目根>/log）
LOG_DIR = os.path.join(_ROOT, 'log')


class Logger:
    """
    同时写入控制台与日志文件。
    - 控制台：可选颜色、可选静默
    - 日志文件：纯文本，带时间戳和级别标签，始终记录完整内容
    - 日志路径: <项目根>/log/restore_ext_<时间戳>.log（目录不存在时自动创建）
    """

    def __init__(self, use_color=True, quiet=False, enable_file=True):
        self.use_color = use_color
        self.quiet = quiet
        self._file = None
        self.log_path = None

        if enable_file:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"restore_ext_{ts}.log"
            log_path = os.path.join(LOG_DIR, log_file)

            try:
                os.makedirs(LOG_DIR, exist_ok=True)
                self._file = open(log_path, 'w', encoding='utf-8')
                self._file.write(
                    f"# restore_ext 日志 - 开始于 {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                )
                self._file.flush()
                self.log_path = log_path
            except Exception as e:
                print(f"警告: 无法创建日志文件 {log_path}: {e}", file=sys.stderr)
                self._file = None
                self.log_path = None

    # ---------- 内部 ----------
    def _write(self, text, color):
        if self._file:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            level = LEVEL_LABEL.get(color, 'INFO')
            self._file.write(f"[{ts}] [{level}] {text}\n")
            self._file.flush()

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
            self._file.write(
                f"# 日志结束于 {datetime.now():%Y-%m-%d %H:%M:%S}\n"
            )
            self._file.close()
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()