#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件扩展名还原工具（模块化 + 插件式容器检测 + 日志记录）

用法示例:
    python restore_ext.py -r D:\Media
    python restore_ext.py -r --dry-run -v D:\Media
    python restore_ext.py -r --quiet --no-color D:\Media

配置文件:
    table.json  —— 魔数映射表（与脚本同目录 或 CWD，由 MagicTable 决定）
    ignore.json —— 忽略规则，**仅从当前工作目录读取**
"""

import argparse
import os
import sys

from core.logger import Logger
from core.config import MagicTable, IgnoreRules, ConfigError
from core import registry
from core.collector import collect_files
from core.processor import process_file, Status


MAGIC_CONFIG = 'table.json'

# 忽略配置仅从当前工作目录读取
IGNORE_CONFIG = os.path.abspath('ignore.json')


def parse_args():
    p = argparse.ArgumentParser(
        description="根据文件头魔数还原扩展名（支持插件式容器检测与日志）",
        epilog="固定配置文件: table.json (魔数表), ignore.json (工作区忽略规则)"
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

    p.add_argument('--no-log', action='store_true',
                   help='不写入日志文件（仅控制台）')
    p.add_argument('--quiet', action='store_true',
                   help='不输出到控制台（仅写日志文件）')
    return p.parse_args()


def load_configs(logger):
    """加载魔数表与忽略规则"""
    try:
        magic_table = MagicTable(MAGIC_CONFIG)
    except ConfigError as e:
        logger.error(f"错误: {e}")
        sys.exit(1)

    # 显式提示忽略规则的来源
    if os.path.isfile(IGNORE_CONFIG):
        logger.info(f"忽略规则来源: {IGNORE_CONFIG}")
        try:
            ignore_rules = IgnoreRules(IGNORE_CONFIG)
        except ConfigError as e:
            logger.warn(f"警告: {e}，将不忽略任何文件。")
            ignore_rules = IgnoreRules.empty()
    else:
        logger.info(f"未找到工作区 ignore.json（{IGNORE_CONFIG}），将不忽略任何文件。")
        ignore_rules = IgnoreRules.empty()

    return magic_table, ignore_rules


def main():
    args = parse_args()

    logger = Logger(
        use_color=not args.no_color,
        quiet=args.quiet,
        enable_file=not args.no_log,
    )

    try:
        _run(args, logger)
    finally:
        if logger.log_path:
            logger.info(f"日志已保存至: {logger.log_path}")
        logger.close()


def _run(args, logger):
    if not os.path.exists(args.path):
        logger.error(f"错误: 路径不存在 - {args.path}")
        sys.exit(1)

    magic_table, ignore_rules = load_configs(logger)

    if args.verbose:
        logger.info("正在加载检测器插件...")
    registry.discover(logger=logger if args.verbose else None)
    if args.verbose:
        names = [d.name for d in registry.list_all()]
        logger.info(f"共加载 {len(names)} 个检测器: {names}")

    try:
        files = collect_files(args.path, args.recursive, ignore_rules)
    except ValueError as e:
        logger.error(f"错误: {e}")
        sys.exit(1)

    if not files:
        logger.info("没有需要处理的文件（或全部被忽略）。")
        return

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

        color = color_map[result.status]
        getattr(logger, {
            'green': 'success',
            'red':   'error',
            'reset': 'info',
        }[color])(text)

    if args.dry_run:
        logger.info(f"预览完成，共 {total} 个文件，其中 {success_count} 个将重命名。")
    else:
        logger.info(f"处理完成，共 {total} 个文件，成功重命名 {success_count} 个。")


if __name__ == '__main__':
    main()