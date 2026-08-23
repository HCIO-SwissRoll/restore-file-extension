#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（支持通配符魔数、独立忽略文件、彩色输出）
根据文件开头的魔数（magic bytes）自动修正或添加扩展名。
魔数映射存储在 table.json，忽略模式存储在 ignore.json（可自定义）。
"""

import os
import sys
import json
import re
import argparse
import fnmatch


# ANSI 颜色码
COLOR_RED = '\033[91m'
COLOR_GREEN = '\033[92m'
COLOR_RESET = '\033[0m'


def print_colored(text, color=COLOR_RESET):
    """以指定颜色打印文本（颜色码需包含 RESET）"""
    print(f"{color}{text}{COLOR_RESET}")


def load_settings(config_path):
    """加载 table.json，返回魔数模式列表（按长度降序）"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except Exception as e:
        print_colored(f"错误：无法加载配置文件 {config_path} - {e}", COLOR_RED)
        sys.exit(1)

    patterns = []
    for magic, ext in settings.items():
        magic = magic.upper().strip()
        ext = ext.lstrip('.')
        if not magic:
            continue
        if '*' in magic or '?' in magic:
            regex = compile_pattern(magic)
            patterns.append((magic, ext, regex))
        else:
            patterns.append((magic, ext, None))

    patterns.sort(key=lambda x: len(x[0]), reverse=True)
    return patterns


def compile_pattern(pattern):
    """编译包含通配符 ? 和 * 的魔数模式为正则对象"""
    escaped = re.escape(pattern)
    escaped = escaped.replace('\\?', '[0-9A-F]')
    escaped = escaped.replace('\\*', '.*')
    return re.compile('^' + escaped, re.IGNORECASE)


def load_ignore_patterns(ignore_path):
    """加载 ignore.json，返回忽略模式列表（若文件不存在则返回空）"""
    if not os.path.isfile(ignore_path):
        print(f"提示：忽略配置文件 {ignore_path} 不存在，将不忽略任何文件。")
        return []

    try:
        with open(ignore_path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        if isinstance(patterns, list):
            return patterns
        else:
            print_colored(f"错误：忽略配置文件 {ignore_path} 格式错误，应为 JSON 数组。", COLOR_RED)
            return []
    except Exception as e:
        print_colored(f"错误：无法加载忽略配置文件 {ignore_path} - {e}", COLOR_RED)
        return []


def is_ignored(file_path, ignore_patterns, base_dir=''):
    """判断文件或文件夹是否应被忽略"""
    if not ignore_patterns:
        return False

    name = os.path.basename(file_path)
    rel_path = os.path.relpath(file_path, base_dir) if base_dir else file_path
    rel_path = rel_path.replace('\\', '/')

    for pattern in ignore_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel_path, pattern.replace('\\', '/')):
            return True
    return False


def find_extension_by_magic(file_path, patterns, read_bytes):
    """读取文件头并匹配魔数，返回扩展名或 None"""
    if not patterns:
        return None

    try:
        with open(file_path, 'rb') as f:
            header = f.read(read_bytes)
    except Exception:
        return None

    header_hex = header.hex().upper()

    for magic, ext, regex in patterns:
        if regex is not None:
            if regex.match(header_hex):
                return ext
        else:
            if header_hex.startswith(magic):
                return ext
    return None


def process_file(file_path, patterns, read_bytes, dry_run=False):
    """
    处理单个文件，返回 (status, old_path, new_path, message)
    status: 'success' | 'exists' | 'error' | 'preview'
    """
    if not os.path.isfile(file_path):
        return 'error', file_path, None, "不是普通文件"

    ext = find_extension_by_magic(file_path, patterns, read_bytes)
    if ext is None:
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


def collect_files(path, recursive, ignore_patterns):
    """收集待处理的文件列表（应用忽略规则）"""
    files = []
    if recursive:
        if not os.path.isdir(path):
            print_colored(f"错误：递归模式要求路径为文件夹 - {path}", COLOR_RED)
            sys.exit(1)
        for root, dirs, dir_files in os.walk(path):
            if is_ignored(root, ignore_patterns, path):
                dirs[:] = []
                continue
            for f in dir_files:
                full = os.path.join(root, f)
                if is_ignored(full, ignore_patterns, path):
                    continue
                files.append(full)
    else:
        if not os.path.isfile(path):
            print_colored(f"错误：非递归模式要求路径为文件 - {path}", COLOR_RED)
            sys.exit(1)
        if not is_ignored(path, ignore_patterns, os.path.dirname(path)):
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(
        description="通过文件头部魔数还原文件扩展名（支持通配符魔数、独立忽略文件、彩色输出）"
    )
    parser.add_argument('path', help='文件或文件夹路径（递归模式时为文件夹）')
    parser.add_argument('-c', '--config', default='table.json',
                        help='魔数映射配置文件路径（默认：table.json）')
    parser.add_argument('-i', '--ignore-config', default='ignore.json',
                        help='忽略模式配置文件路径（默认：ignore.json）')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='递归处理文件夹下的所有文件')
    parser.add_argument('-b', '--bytes', type=int, default=256,
                        help='读取文件头部的字节数（默认 256）')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示匹配结果，不实际重命名')
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print_colored(f"错误：路径不存在 - {args.path}", COLOR_RED)
        sys.exit(1)

    if not os.path.isfile(args.config):
        print_colored(f"错误：魔数配置文件不存在 - {args.config}", COLOR_RED)
        sys.exit(1)

    patterns = load_settings(args.config)
    ignore_patterns = load_ignore_patterns(args.ignore_config)

    files_to_process = collect_files(args.path, args.recursive, ignore_patterns)

    if not files_to_process:
        print("没有找到任何文件需要处理（或全部被忽略）。")
        return

    total = len(files_to_process)
    success_count = 0
    for idx, file_path in enumerate(files_to_process, 1):
        status, old, new, msg = process_file(file_path, patterns, args.bytes, args.dry_run)

        # 根据状态选择颜色
        if status == 'success':
            color = COLOR_GREEN
            success_count += 1
        elif status == 'error':
            color = COLOR_RED
        else:  # 'exists' 或 'preview'
            color = COLOR_RESET  # 默认颜色

        # 构建输出信息
        if new is None:
            output = f"[{idx}/{total}] 跳过: {old} - {msg}"
        else:
            output = f"[{idx}/{total}] 跳过: {old} -> {new} - {msg}" if status != 'success' else f"[{idx}/{total}] 成功: {old} -> {new}"

        # 打印（若为默认颜色则直接 print，否则用彩色）
        if color == COLOR_RESET:
            print(output)
        else:
            print_colored(output, color)

    # 最终总结
    if args.dry_run:
        print(f"预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。")
    else:
        print(f"处理完成，共 {total} 个文件，成功重命名 {success_count} 个。")


if __name__ == '__main__':
    main()