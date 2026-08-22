#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（支持递归目录）
根据文件开头的魔数（magic bytes）自动修正或添加扩展名。
配置映射存储在 settings.json 中。
"""

import os
import sys
import json
import argparse


def load_settings(config_path):
    """加载并解析 settings.json"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        # 将键转为大写十六进制字符串，值去除多余点号
        return {k.upper(): v.lstrip('.') for k, v in settings.items()}
    except Exception as e:
        print(f"错误：无法加载配置文件 {config_path} - {e}")
        sys.exit(1)


def find_extension_by_magic(file_path, settings):
    """
    读取文件头，根据 settings 中的魔数匹配扩展名。
    返回匹配的扩展名（不含点），若无匹配则返回 None。
    """
    if not settings:
        return None

    # 计算需要读取的最大字节数（键为十六进制字符串，长度/2）
    max_hex_len = max(len(k) for k in settings.keys())
    max_bytes = (max_hex_len + 1) // 2  # 向上取整，保证足够

    try:
        with open(file_path, 'rb') as f:
            header = f.read(max_bytes)
    except Exception as e:
        # 读取失败，返回 None
        return None

    header_hex = header.hex().upper()

    # 按魔数长度降序匹配（长魔数更精确）
    for magic, ext in sorted(settings.items(), key=lambda x: len(x[0]), reverse=True):
        if header_hex.startswith(magic):
            return ext

    return None


def process_file(file_path, settings, dry_run=False):
    """
    处理单个文件：根据魔数匹配并重命名。
    返回 (success, old_path, new_path, message)
    """
    if not os.path.isfile(file_path):
        return False, file_path, None, "不是普通文件"

    ext = find_extension_by_magic(file_path, settings)
    if ext is None:
        return False, file_path, None, "未匹配到任何魔数"

    # 构建新文件名
    dirname = os.path.dirname(file_path)
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)          # 去掉原有扩展名
    new_name = f"{name}.{ext}"
    new_path = os.path.join(dirname, new_name)

    if dry_run:
        return True, file_path, new_path, "预览 (将重命名)"

    # 避免覆盖已存在的文件
    if os.path.exists(new_path):
        return False, file_path, new_path, "目标文件已存在，跳过"

    # 执行重命名
    try:
        os.rename(file_path, new_path)
        return True, file_path, new_path, "成功"
    except Exception as e:
        return False, file_path, new_path, f"重命名失败: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="通过文件头部魔数还原文件扩展名"
    )
    parser.add_argument('path', help='文件或文件夹路径（递归模式时为文件夹）')
    parser.add_argument('-c', '--config', default='settings.json',
                        help='自定义映射配置文件路径（默认：settings.json）')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='递归处理文件夹下的所有文件')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示匹配结果，不实际重命名')
    args = parser.parse_args()

    # 检查路径是否存在
    if not os.path.exists(args.path):
        print(f"错误：路径不存在 - {args.path}")
        sys.exit(1)

    # 检查配置文件
    if not os.path.isfile(args.config):
        print(f"错误：配置文件不存在 - {args.config}")
        sys.exit(1)

    settings = load_settings(args.config)

    # 收集待处理文件列表
    files_to_process = []
    if args.recursive:
        if not os.path.isdir(args.path):
            print(f"错误：递归模式要求路径为文件夹 - {args.path}")
            sys.exit(1)
        for root, dirs, files in os.walk(args.path):
            for f in files:
                full_path = os.path.join(root, f)
                files_to_process.append(full_path)
    else:
        if not os.path.isfile(args.path):
            print(f"错误：非递归模式要求路径为文件 - {args.path}")
            sys.exit(1)
        files_to_process.append(args.path)

    if not files_to_process:
        print("没有找到任何文件需要处理。")
        return

    # 处理每个文件
    total = len(files_to_process)
    success_count = 0
    for idx, file_path in enumerate(files_to_process, 1):
        success, old, new, msg = process_file(file_path, settings, args.dry_run)
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

    # 汇总信息
    if args.dry_run:
        print(f"预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。")
    else:
        print(f"处理完成，共 {total} 个文件，成功重命名 {success_count} 个。")

if __name__ == '__main__':
    main()