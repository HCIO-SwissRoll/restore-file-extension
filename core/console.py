"""彩色控制台输出"""

COLORS = {
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'cyan': '\033[96m',
    'reset': '\033[0m',
}


class Console:
    def __init__(self, use_color=True):
        self.use_color = use_color

    def print(self, text, color='reset'):
        if self.use_color and color in COLORS:
            print(f"{COLORS[color]}{text}{COLORS['reset']}")
        else:
            print(text)

    def info(self, text):    self.print(text, 'reset')
    def error(self, text):   self.print(text, 'red')
    def success(self, text): self.print(text, 'green')
    def warn(self, text):    self.print(text, 'yellow')
    def notice(self, text):  self.print(text, 'cyan')