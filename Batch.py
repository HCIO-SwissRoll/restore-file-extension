#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（支持通配符魔数）
根据文件开头的魔数（magic bytes）自动修正或添加扩展名。
配置映射存储在 settings.json 中，魔数支持通配符 ? 和 *。
"""

import os
import sys
import json
import re
import argparse


def compile_pattern(pattern):
    """
    将包含通配符 ? 和 * 的魔数模式编译为正则对象。
    模式为十六进制字符串，? 匹配任意一个十六进制字符，* 匹配任意长度十六进制序列。
    返回正则对象，用于从头部开头匹配。
    """
    # 转义普通字符，但保留 ? 和 * 的转义处理
    escaped = re.escape(pattern)
    # 恢复 ? 和 * 作为通配符
    escaped = escaped.replace('\\?', '[0-9A-F]')  # ? 匹配任意一个十六进制字符
    escaped = escaped.replace('\\*', '.*')        # * 匹配任意长度
    # 锚定到开头，但不强制到结尾（只需前缀匹配）
    return re.compile('^' + escaped, re.IGNORECASE)  


def load_settings(config_path):
    """加载并解析 settings.json，返回模式列表（按长度降序）"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except Exception as e:
        print(f"错误：无法加载配置文件 {config_path} - {e}")
        sys.exit(1)

    patterns = []
    for magic, ext in settings.items():
        magic = magic.upper().strip()
        ext = ext.lstrip('.')
        if not magic:
            continue
        # 检查是否包含通配符
        if '*' in magic or '?' in magic:
            regex = compile_pattern(magic)
            patterns.append((magic, ext, regex))
        else:
            patterns.append((magic, ext, None))  # None 表示普通前缀匹配

    # 按魔数长度降序排序（长魔数优先，包含通配符的长度取原始字符串长度）
    patterns.sort(key=lambda x: len(x[0]), reverse=True)
    return patterns


def find_extension_by_magic(file_path, patterns):
    """
    读取文件头部，根据 patterns 列表匹配扩展名。
    patterns 为 (magic, ext, regex_obj) 的列表。
    返回匹配的扩展名（不含点），若无匹配则返回 None。
    """
    if not patterns:
        return None

    # 读取足够多的字节以覆盖大多数魔数（至少 256 字节，但也可根据模式动态调整）
    # 读取前 256 字节，对于小文件则读取全部
    try:
        with open(file_path, 'rb') as f:
            header = f.read(256)
    except Exception:
        return None

    header_hex = header.hex().upper()

    for magic, ext, regex in patterns:
        if regex is not None:
            # 使用正则匹配（从头部开头）
            if regex.match(header_hex):
                return ext
        else:
            # 普通前缀匹配
            if header_hex.startswith(magic):
                return ext
    return None


def process_file(file_path, patterns, dry_run=False):
    """处理单个文件，返回 (success, old, new, msg)"""
    if not os.path.isfile(file_path):
        return False, file_path, None, "不是普通文件"

    ext = find_extension_by_magic(file_path, patterns)
    if ext is None:
        return False, file_path, None, "未匹配到任何魔数"

    dirname = os.path.dirname(file_path)
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)
    new_name = f"{name}.{ext}"
    new_path = os.path.join(dirname, new_name)

    if dry_run:
        return True, file_path, new_path, "预览 (将重命名)"

    if os.path.exists(new_path):
        return False, file_path, new_path, "目标文件已存在，跳过"

    try:
        os.rename(file_path, new_path)
        return True, file_path, new_path, "成功"
    except Exception as e:
        return False, file_path, new_path, f"重命名失败: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="通过文件头部魔数还原文件扩展名（支持通配符 ? 和 *）"
    )
    parser.add_argument('path', help='文件或文件夹路径（递归模式时为文件夹）')
    parser.add_argument('-c', '--config', default='settings.json',
                        help='自定义映射配置文件路径（默认：settings.json）')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='递归处理文件夹下的所有文件')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示匹配结果，不实际重命名')
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"错误：路径不存在 - {args.path}")
        sys.exit(1)

    if not os.path.isfile(args.config):
        print(f"错误：配置文件不存在 - {args.config}")
        sys.exit(1)

    patterns = load_settings(args.config)

    files_to_process = []
    if args.recursive:
        if not os.path.isdir(args.path):
            print(f"错误：递归模式要求路径为文件夹 - {args.path}")
            sys.exit(1)
        for root, _, files in os.walk(args.path):
            for f in files:
                files_to_process.append(os.path.join(root, f))
    else:
        if not os.path.isfile(args.path):
            print(f"错误：非递归模式要求路径为文件 - {args.path}")
            sys.exit(1)
        files_to_process.append(args.path)

    if not files_to_process:
        print("没有找到任何文件需要处理。")
        return

    total = len(files_to_process)
    success_count = 0
    for idx, file_path in enumerate(files_to_process, 1):
        success, old, new, msg = process_file(file_path, patterns, args.dry_run)
        if success:
            success_count += 1
            if args.dry_run:
                print(f"[{idx}/{total}] 预览: {old} -> {new}")
            else:
                print(f"[{idx}/{total}] 成功: {old} -> {new}")
        else:
            if new is None:
                print(f"[{idx}/{total}] 跳过: {old} - {msg}")
            else:
                print(f"[{idx}/{total}] 跳过: {old} -> {new} - {msg}")

    if args.dry_run:
        print(f"预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。")
    else:
        print(f"处理完成，共 {total} 个文件，成功重命名 {success_count} 个。")


if __name__ == '__main__':
    main()