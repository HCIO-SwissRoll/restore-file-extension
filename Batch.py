
"""
文件扩展名还原工具
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
        print(f"错误：无法读取文件 {file_path} - {e}")
        return None

    header_hex = header.hex().upper()

    # 按魔数长度降序匹配（长魔数更精确）
    for magic, ext in sorted(settings.items(), key=lambda x: len(x[0]), reverse=True):
        if header_hex.startswith(magic):
            return ext

    return None


def main():
    parser = argparse.ArgumentParser(
        description="通过文件头部魔数还原文件扩展名"
    )
    parser.add_argument('file', help='需要修复扩展名的文件路径')
    parser.add_argument('-c', '--config', default='settings.json',
                        help='自定义映射配置文件路径（默认：settings.json）')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示匹配结果，不实际重命名')
    args = parser.parse_args()

    # 检查文件和配置是否存在
    if not os.path.isfile(args.file):
        print(f"错误：文件不存在 - {args.file}")
        sys.exit(1)
    if not os.path.isfile(args.config):
        print(f"错误：配置文件不存在 - {args.config}")
        sys.exit(1)

    settings = load_settings(args.config)

    ext = find_extension_by_magic(args.file, settings)
    if ext is None:
        print(f"未找到匹配的魔数，文件 '{args.file}' 保持不变。")
        return

    # 构建新文件名
    dirname = os.path.dirname(args.file)
    basename = os.path.basename(args.file)
    name, _ = os.path.splitext(basename)          # 去掉原有扩展名
    new_name = f"{name}.{ext}"
    new_path = os.path.join(dirname, new_name)

    if args.dry_run:
        print(f"[DRY RUN] 将重命名：{args.file} -> {new_path}")
        return

    # 避免覆盖已存在的文件
    if os.path.exists(new_path):
        print(f"警告：目标文件已存在，跳过重命名 - {new_path}")
        return

    # 执行重命名
    try:
        os.rename(args.file, new_path)
        print(f"成功重命名：{args.file} -> {new_path}")
    except Exception as e:
        print(f"重命名失败：{e}")


if __name__ == '__main__':
    main()