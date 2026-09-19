"""文件收集：应用忽略规则"""

import os


def collect_files(root_path, recursive, ignore_rules):
    """
    返回待处理的文件列表。
    递归模式下遍历子目录；忽略规则命中时跳过整个子树或单个文件。
    """
    if recursive:
        if not os.path.isdir(root_path):
            raise ValueError(f"递归模式要求路径为文件夹: {root_path}")
        files = []
        for root, dirs, filenames in os.walk(root_path):
            if ignore_rules.is_ignored(root, root_path):
                dirs[:] = []
                continue
            for f in filenames:
                full = os.path.join(root, f)
                if not ignore_rules.is_ignored(full, root_path):
                    files.append(full)
        return files
    else:
        if not os.path.isfile(root_path):
            raise ValueError(f"非递归模式要求路径为文件: {root_path}")
        if ignore_rules.is_ignored(root_path, os.path.dirname(root_path)):
            return []
        return [root_path]