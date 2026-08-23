#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（高性能版）
根据文件开头的魔数自动修正扩展名。
魔数映射表: table.json，忽略规则: ignore.json（均支持通配符）
"""

import os
import sys
import json
import re
import argparse
import fnmatch
from collections import OrderedDict

# ---------- 颜色控制 ----------
COLORS = {
    'red': '\033[91m',
    'green': '\033[92m',
    'reset': '\033[0m'
}
USE_COLOR = True  # 由 --no-color 控制


def print_colored(text, color='reset'):
    if USE_COLOR and color in COLORS:
        print(f"{COLORS[color]}{text}{COLORS['reset']}")
    else:
        print(text)


# ---------- 配置加载器 ----------
class MagicLoader:
    """魔数映射表加载器，支持通配符并预编译正则"""
    def __init__(self, config_path):
        self.config_path = config_path
        self.patterns = []  # 元素: (raw_magic, ext, regex_or_none)
        self._load()

    def _compile_pattern(self, pattern):
        """将包含 ? 和 * 的十六进制模式编译为正则对象"""
        escaped = re.escape(pattern.upper())
        escaped = escaped.replace('\\?', '[0-9A-F]')
        escaped = escaped.replace('\*', '.*')  # 注意顺序
        return re.compile('^' + escaped)

    def _load(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print_colored(f"错误：无法加载魔数配置文件 {self.config_path} - {e}", 'red')
            sys.exit(1)

        for magic, ext in data.items():
            magic = magic.upper().strip()
            ext = ext.lstrip('.')
            if not magic:
                continue
            if '*' in magic or '?' in magic:
                regex = self._compile_pattern(magic)
                self.patterns.append((magic, ext, regex))
            else:
                self.patterns.append((magic, ext, None))

        # 按魔数长度降序排序（精确匹配优先）
        self.patterns.sort(key=lambda x: len(x[0]), reverse=True)

    def match(self, header_hex):
        """在头部十六进制字符串中匹配魔数，返回扩展名或 None"""
        for magic, ext, regex in self.patterns:
            if regex is not None:
                if regex.match(header_hex):
                    return ext
            else:
                if header_hex.startswith(magic):
                    return ext
        return None


class IgnoreLoader:
    """忽略规则加载器，支持路径和文件名通配"""
    def __init__(self, ignore_path):
        self.ignore_path = ignore_path
        self.patterns = []
        self._load()

    def _load(self):
        if not os.path.isfile(self.ignore_path):
            print(f"提示：忽略配置文件 {self.ignore_path} 不存在，不忽略任何文件。")
            return
        try:
            with open(self.ignore_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("忽略配置必须为 JSON 数组")
            self.patterns = data
        except Exception as e:
            print_colored(f"错误：忽略配置文件 {self.ignore_path} 加载失败 - {e}", 'red')
            sys.exit(1)

    def is_ignored(self, file_path, base_dir=''):
        """判断文件或目录是否应被忽略"""
        if not self.patterns:
            return False

        name = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, base_dir) if base_dir else file_path
        rel_path = rel_path.replace('\\', '/')

        for pattern in self.patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
            if fnmatch.fnmatch(rel_path, pattern.replace('\\', '/')):
                return True
        return False


# ---------- 核心处理 ----------
def get_file_header(file_path, read_bytes):
    """读取文件头部，返回十六进制字符串；若失败返回 None"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(read_bytes)
        return header.hex().upper()
    except Exception:
        return None


def process_file(file_path, magic_loader, read_bytes, dry_run=False, verbose=False):
    """
    处理单个文件，返回 (status, old, new, msg)
    status: 'success' | 'exists' | 'preview' | 'error'
    """
    if not os.path.isfile(file_path):
        return 'error', file_path, None, "不是普通文件"

    header_hex = get_file_header(file_path, read_bytes)
    if header_hex is None:
        return 'error', file_path, None, "无法读取文件头部"

    ext = magic_loader.match(header_hex)
    if ext is None:
        if verbose:
            return 'error', file_path, None, f"未匹配魔数 (头: {header_hex[:20]}...)"
        return 'error', file_path, None, "未匹配到任何魔数"

    dirname = os.path.dirname(file_path)
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)
    new_name = f"{name}.{ext}"
    new_path = os.path.join(dirname, new_name)

    if dry_run:
        return 'preview', file_path, new_path, "预览 (将重命名)"

    if os.path.exists(new_path):
        return 'exists', file_path, new_path, "目标文件已存在，跳过"

    try:
        os.rename(file_path, new_path)
        return 'success', file_path, new_path, "成功"
    except Exception as e:
        return 'error', file_path, new_path, f"重命名失败: {e}"


def collect_files(root_path, recursive, ignore_loader):
    """收集待处理文件列表，应用忽略规则"""
    files = []
    if recursive:
        if not os.path.isdir(root_path):
            print_colored(f"错误：递归模式要求路径为文件夹 - {root_path}", 'red')
            sys.exit(1)
        for root, dirs, dir_files in os.walk(root_path):
            # 如果当前目录被忽略，跳过整个子树
            if ignore_loader.is_ignored(root, root_path):
                dirs[:] = []
                continue
            for f in dir_files:
                full = os.path.join(root, f)
                if not ignore_loader.is_ignored(full, root_path):
                    files.append(full)
    else:
        if not os.path.isfile(root_path):
            print_colored(f"错误：非递归模式要求路径为文件 - {root_path}", 'red')
            sys.exit(1)
        if not ignore_loader.is_ignored(root_path, os.path.dirname(root_path)):
            files.append(root_path)
    return files


# ---------- 主程序 ----------
def main():
    parser = argparse.ArgumentParser(
        description="根据文件头魔数还原扩展名（高性能版）",
        epilog="配置文件: table.json (魔数映射), ignore.json (忽略规则)"
    )
    parser.add_argument('path', help='文件或文件夹路径（递归模式时为文件夹）')
    parser.add_argument('-c', '--config', default='table.json',
                        help='魔数映射表路径 (默认: table.json)')
    parser.add_argument('-i', '--ignore-config', default='ignore.json',
                        help='忽略规则路径 (默认: ignore.json)')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='递归处理子文件夹')
    parser.add_argument('-b', '--bytes', type=int, default=256,
                        help='读取头部字节数 (默认: 256)')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式，不实际重命名')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示更多信息（如匹配的魔数头）')
    parser.add_argument('--no-color', action='store_true',
                        help='禁用彩色输出')
    args = parser.parse_args()

    global USE_COLOR
    if args.no_color:
        USE_COLOR = False

    # 检查路径和配置文件
    if not os.path.exists(args.path):
        print_colored(f"错误：路径不存在 - {args.path}", 'red')
        sys.exit(1)
    if not os.path.isfile(args.config):
        print_colored(f"错误：魔数配置文件不存在 - {args.config}", 'red')
        sys.exit(1)

    # 加载配置
    magic_loader = MagicLoader(args.config)
    ignore_loader = IgnoreLoader(args.ignore_config)

    # 收集文件
    file_list = collect_files(args.path, args.recursive, ignore_loader)
    if not file_list:
        print("没有找到任何需要处理的文件（或全部被忽略）。")
        return

    total = len(file_list)
    success_count = 0
    status_color = {
        'success': 'green',
        'preview': 'reset',
        'exists': 'reset',
        'error': 'red'
    }

    for idx, fpath in enumerate(file_list, 1):
        status, old, new, msg = process_file(fpath, magic_loader, args.bytes, args.dry_run, args.verbose)
        if status == 'success':
            success_count += 1

        # 构建输出消息
        if status == 'success':
            label = "成功"
        elif status == 'preview':
            label = "预览"
        elif status == 'exists':
            label = "跳过"
        else:
            label = "跳过"

        if new is None:
            output = f"[{idx}/{total}] {label}: {old} - {msg}"
        else:
            output = f"[{idx}/{total}] {label}: {old} -> {new} - {msg}"

        print_colored(output, status_color.get(status, 'reset'))

    # 总结
    if args.dry_run:
        print(f"预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。")
    else:
        print(f"处理完成，共 {total} 个文件，成功重命名 {success_count} 个。")


if __name__ == '__main__':
    main()