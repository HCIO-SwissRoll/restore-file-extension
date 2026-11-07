#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（Rust 核心 + Python 外壳）
魔数匹配与 OGG/MP4 流检测由 Rust 原生模块完成。

用法:
    python restore_ext.py -r D:\Media
    python restore_ext.py -r --dry-run D:\Media
    python restore_ext.py --no-log D:\file.bin
"""

import json
import os
import sys
import argparse
import fnmatch
from pathlib import Path
from datetime import datetime

# 导入 Rust 原生模块（需先: pip install restore-ext-native 或 maturin develop）
try:
    import restore_ext_native
except ImportError:
    print("错误: 未找到 restore_ext_native。")
    print("开发时: cd crates/restore-ext-py && maturin develop --release")
    print("安装时: pip install restore-ext-native")
    sys.exit(1)


# ---------- 颜色 ----------
COLORS = {'red': '\033[91m', 'green': '\033[92m', 'reset': '\033[0m'}


def color(text, c=None):
    return f"{COLORS[c]}{text}{COLORS['reset']}" if c in COLORS else text


# ---------- 路径常量 ----------
# 脚本所在目录（项目根目录）
ROOT_DIR = Path(__file__).resolve().parent
# 日志目录：跟随脚本位置
LOG_DIR = ROOT_DIR / 'log'
# 魔数表：优先脚本目录，其次工作目录
TABLE_CANDIDATES = [ROOT_DIR / 'table.json', Path('table.json')]
# 忽略规则：仅从工作区（CWD）读取
IGNORE_PATH = Path.cwd() / 'ignore.json'


# ---------- 配置加载 ----------
def find_table_path():
    for p in TABLE_CANDIDATES:
        if p.is_file():
            return p
    return None


def load_table():
    path = find_table_path()
    if path is None:
        print(color("错误: 未找到 table.json（脚本目录或工作目录）", 'red'))
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    entries = [(k, v) for k, v in data.items()]
    return restore_ext_native.PyMagicTable(entries), path


def load_ignore():
    if not IGNORE_PATH.is_file():
        return []
    try:
        with open(IGNORE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(color(f"警告: ignore.json 加载失败 - {e}", 'red'))
        return []


# ---------- 忽略匹配 ----------
def is_ignored(file_path, patterns, base_dir):
    if not patterns:
        return False
    name = os.path.basename(file_path)
    rel = os.path.relpath(file_path, base_dir).replace('\\', '/')
    for p in patterns:
        if fnmatch.fnmatch(name, p):
            return True
        if fnmatch.fnmatch(rel, p.replace('\\', '/')):
            return True
    return False


def collect_files(root, recursive, ignore_patterns):
    if not recursive:
        if os.path.isfile(root) and not is_ignored(root, ignore_patterns, os.path.dirname(root)):
            return [root]
        return []
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        if is_ignored(dirpath, ignore_patterns, root):
            dirnames[:] = []
            continue
        for f in filenames:
            full = os.path.join(dirpath, f)
            if not is_ignored(full, ignore_patterns, root):
                files.append(full)
    return files


# ---------- 单文件处理 ----------
def process_one(file_path, table, read_bytes=256, dry_run=False):
    """返回 (status, old_path, new_path, message)"""
    if not os.path.isfile(file_path):
        return ('error', file_path, None, '不是普通文件')

    # 头部读取（魔数匹配 + ftyp 校验）
    try:
        with open(file_path, 'rb') as f:
            header_data = f.read(read_bytes)
    except Exception:
        return ('error', file_path, None, '无法读取文件')

    header_hex = header_data.hex().upper()

    # Rust: 粗判扩展名
    matched = table.match_header(header_hex)
    if matched is None:
        return ('error', file_path, None, '未匹配到任何魔数')

    # Rust: 细化（OGG / MP4）
    # 容器检测可能需要较深位置的数据（如 MP4 的 moov 常在尾部）
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            if file_size <= 50 * 1024 * 1024:
                full_data = f.read()
            else:
                f.seek(max(0, file_size - 1024 * 1024))
                full_data = f.read()
    except Exception:
        return ('error', file_path, None, '无法读取文件内容')

    refined = restore_ext_native.refine_extension(matched, full_data, header_hex)
    ext = refined[0] if refined else matched

    dirname = os.path.dirname(file_path)
    stem = os.path.splitext(os.path.basename(file_path))[0]
    new_path = os.path.join(dirname, f"{stem}.{ext}")

    if dry_run:
        return ('preview', file_path, new_path, '预览 (将重命名)')
    if os.path.exists(new_path):
        return ('exists', file_path, new_path, '目标文件已存在')
    try:
        os.rename(file_path, new_path)
        return ('success', file_path, new_path, '成功')
    except Exception as e:
        return ('error', file_path, new_path, f'重命名失败: {e}')


# ---------- 日志 ----------
def write_log(lines):
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"restore_ext_{datetime.now():%Y%m%d_%H%M%S}.log"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"# restore_ext 日志 - {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        for line in lines:
            f.write(line + '\n')
    return log_file


# ---------- 主流程 ----------
def main():
    parser = argparse.ArgumentParser(
        description='文件扩展名还原（Rust 核心）',
        epilog='固定配置: table.json (脚本目录或工作区), ignore.json (工作区)'
    )
    parser.add_argument('path', help='文件或文件夹路径')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='递归处理子文件夹')
    parser.add_argument('-b', '--bytes', type=int, default=256,
                        help='读取文件头部的字节数（默认 256）')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式，不实际重命名')
    parser.add_argument('--no-color', action='store_true',
                        help='禁用彩色输出')
    parser.add_argument('--no-log', action='store_true',
                        help='不写入日志文件')
    args = parser.parse_args()

    use_color = not args.no_color

    if not os.path.exists(args.path):
        print(color(f'错误: 路径不存在 - {args.path}', 'red'))
        sys.exit(1)

    # 加载配置
    table, table_path = load_table()
    ignore_patterns = load_ignore()
    print(f"魔数表: {table_path}")
    if ignore_patterns:
        print(f"忽略规则: {IGNORE_PATH} ({len(ignore_patterns)} 条)")
    else:
        print(f"忽略规则: 无 ({IGNORE_PATH} 不存在或为空)")

    # 收集文件
    files = collect_files(args.path, args.recursive, ignore_patterns)
    if not files:
        print('没有需要处理的文件（或全部被忽略）。')
        return

    # 逐个处理
    total = len(files)
    success_count = 0
    log_lines = []

    label_map = {'success': '成功', 'preview': '预览',
                 'exists': '跳过', 'error': '跳过'}
    color_map = {'success': 'green', 'error': 'red'}

    for idx, fpath in enumerate(files, 1):
        status, old, new, msg = process_one(fpath, table, args.bytes, args.dry_run)
        if status == 'success':
            success_count += 1

        label = label_map[status]
        line = f'[{idx}/{total}] {label}: {old}'
        if new:
            line += f' -> {new}'
        if msg:
            line += f' - {msg}'
        log_lines.append(line)

        print(color(line, color_map.get(status)))

    # 日志
    if not args.no_log:
        log_file = write_log(log_lines)
        print(f'日志已保存: {log_file}')

    # 总结
    if args.dry_run:
        summary = f'预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。'
    else:
        summary = f'处理完成，共 {total} 个文件，成功重命名 {success_count} 个。'
    print(color(summary, 'green') if use_color else summary)


if __name__ == '__main__':
    main()