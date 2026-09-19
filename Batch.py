#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（模块化 + 插件式容器检测）

用法示例:
    python Batch.py -r D:\Media
    python Batch.py -r --dry-run -v D:\Media
    python Batch.py --no-color D:\file.bin
"""

import argparse
import os
import sys

from core.console import Console
from core.config import MagicTable, IgnoreRules, ConfigError
from core import registry
from core.collector import collect_files
from core.processor import process_file, Status


MAGIC_CONFIG = 'table.json'
IGNORE_CONFIG = 'ignore.json'


def parse_args():
    p = argparse.ArgumentParser(
        description="根据文件头魔数还原扩展名（支持插件式容器检测）",
        epilog=f"固定配置文件: {MAGIC_CONFIG}, {IGNORE_CONFIG}"
    )
    p.add_argument('path', help='文件或文件夹路径')
    p.add_argument('-r', '--recursive', action='store_true',
                   help='递归处理子文件夹')
    p.add_argument('-b', '--bytes', type=int, default=256,
                   help='读取文件头部的字节数（默认 256）')
    p.add_argument('--dry-run', action='store_true',
                   help='预览模式，不实际重命名')
    p.add_argument('-v', '--verbose', action='store_true',
                   help='显示更多信息')
    p.add_argument('--no-color', action='store_true',
                   help='禁用彩色输出')
    return p.parse_args()


def load_configs(console):
    """加载魔数表与忽略规则，返回 (magic_table, ignore_rules)"""
    try:
        magic_table = MagicTable(MAGIC_CONFIG)
    except ConfigError as e:
        console.error(f"错误: {e}")
        sys.exit(1)

    try:
        ignore_rules = IgnoreRules(IGNORE_CONFIG)
    except ConfigError as e:
        console.warn(f"警告: {e}，将不忽略任何文件。")
        ignore_rules = IgnoreRules.empty()

    return magic_table, ignore_rules


def main():
    args = parse_args()
    console = Console(use_color=not args.no_color)

    if not os.path.exists(args.path):
        console.error(f"错误: 路径不存在 - {args.path}")
        sys.exit(1)

    # 1) 加载配置
    magic_table, ignore_rules = load_configs(console)

    # 2) 发现检测器插件
    registry.discover(console=console if args.verbose else None)
    if args.verbose:
        names = [d.name for d in registry.list_all()]
        console.info(f"共加载 {len(names)} 个检测器: {names}")

    # 3) 收集文件
    try:
        files = collect_files(args.path, args.recursive, ignore_rules)
    except ValueError as e:
        console.error(f"错误: {e}")
        sys.exit(1)

    if not files:
        console.info("没有需要处理的文件（或全部被忽略）。")
        return

    # 4) 逐个处理
    total = len(files)
    success_count = 0

    color_map = {
        Status.SUCCESS: 'green',
        Status.PREVIEW: 'reset',
        Status.EXISTS:  'reset',
        Status.ERROR:   'red',
    }
    label_map = {
        Status.SUCCESS: '成功',
        Status.PREVIEW: '预览',
        Status.EXISTS:  '跳过',
        Status.ERROR:   '跳过',
    }

    for idx, fpath in enumerate(files, 1):
        result = process_file(
            fpath, magic_table, args.bytes,
            refine_fn=registry.refine,
            dry_run=args.dry_run,
        )
        if result.status == Status.SUCCESS:
            success_count += 1

        label = label_map[result.status]
        if result.new_path is None:
            text = f"[{idx}/{total}] {label}: {result.old_path} - {result.message}"
        else:
            text = f"[{idx}/{total}] {label}: {result.old_path} -> {result.new_path}"
            if result.message:
                text += f" - {result.message}"

        console.print(text, color_map[result.status])

    # 5) 总结
    if args.dry_run:
        console.info(f"预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。")
    else:
        console.info(f"处理完成，共 {total} 个文件，成功重命名 {success_count} 个。")


if __name__ == '__main__':
    main()