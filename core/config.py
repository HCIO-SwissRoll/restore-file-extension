"""配置加载：魔数映射表 + 忽略规则"""

import json
import os
import re
import fnmatch


class ConfigError(Exception):
    pass


class MagicTable:
    """
    魔数映射表，支持在十六进制模式中使用 ? 和 * 通配符。
    ?  匹配任意一个十六进制字符
    *  匹配任意长度十六进制序列
    """

    def __init__(self, path):
        self.path = path
        self.rules = []  # [(raw_magic, ext, compiled_regex_or_None)]
        self._load()

    def _compile(self, pattern):
        escaped = re.escape(pattern.upper())
        escaped = escaped.replace(r'\?', '[0-9A-F]')
        escaped = escaped.replace(r'\*', '.*')
        return re.compile('^' + escaped)

    def _load(self):
        if not os.path.isfile(self.path):
            raise ConfigError(f"魔数配置文件不存在: {self.path}")
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise ConfigError(f"无法加载 {self.path}: {e}")

        for magic, ext in data.items():
            magic = magic.upper().strip()
            ext = ext.lstrip('.').lower()
            if not magic:
                continue
            if '*' in magic or '?' in magic:
                self.rules.append((magic, ext, self._compile(magic)))
            else:
                self.rules.append((magic, ext, None))

        # 长魔数优先匹配
        self.rules.sort(key=lambda r: len(r[0]), reverse=True)

    def match(self, header_hex):
        """返回扩展名（不含点），未匹配返回 None"""
        for magic, ext, regex in self.rules:
            if regex is not None:
                if regex.match(header_hex):
                    return ext
            else:
                if header_hex.startswith(magic):
                    return ext
        return None


class IgnoreRules:
    """忽略规则：支持文件名或相对路径的通配符匹配"""

    def __init__(self, path=None, patterns=None):
        self.patterns = patterns or []
        if path is not None:
            self._load(path)

    @classmethod
    def empty(cls):
        return cls(patterns=[])

    def _load(self, path):
        if not os.path.isfile(path):
            raise ConfigError(f"忽略配置文件不存在: {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise ConfigError(f"无法加载 {path}: {e}")
        if not isinstance(data, list):
            raise ConfigError(f"{path} 内容必须为 JSON 数组")
        self.patterns = data

    def is_ignored(self, file_path, base_dir=''):
        if not self.patterns:
            return False
        name = os.path.basename(file_path)
        rel = os.path.relpath(file_path, base_dir) if base_dir else file_path
        rel = rel.replace('\\', '/')
        for p in self.patterns:
            if fnmatch.fnmatch(name, p):
                return True
            if fnmatch.fnmatch(rel, p.replace('\\', '/')):
                return True
        return False