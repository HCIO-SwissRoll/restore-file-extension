"""单文件处理"""

import os


class Status:
    SUCCESS = 'success'   # 重命名成功
    PREVIEW = 'preview'   # 预览
    EXISTS = 'exists'     # 目标文件已存在
    ERROR = 'error'       # 无法处理（未匹配 / 读取失败 / 重命名失败）


class Result:
    __slots__ = ('status', 'old_path', 'new_path', 'message')

    def __init__(self, status, old_path, new_path=None, message=''):
        self.status = status
        self.old_path = old_path
        self.new_path = new_path
        self.message = message


def read_header(file_path, read_bytes):
    """读取文件头部并返回大写的十六进制字符串；失败返回 None"""
    try:
        with open(file_path, 'rb') as f:
            return f.read(read_bytes).hex().upper()
    except Exception:
        return None


def process_file(file_path, magic_table, read_bytes, refine_fn=None, dry_run=False):
    """
    处理单个文件：
      1. 读取文件头
      2. 用 MagicTable 粗判扩展名
      3. 若有 refine_fn，调用检测器细化
      4. 按需重命名
    """
    if not os.path.isfile(file_path):
        return Result(Status.ERROR, file_path, message="不是普通文件")

    header_hex = read_header(file_path, read_bytes)
    if header_hex is None:
        return Result(Status.ERROR, file_path, message="无法读取文件头部")

    ext = magic_table.match(header_hex)
    if ext is None:
        return Result(Status.ERROR, file_path, message="未匹配到任何魔数")

    # 细化
    if refine_fn is not None:
        refined = refine_fn(ext, file_path, header_hex)
        if refined:
            ext = refined

    dirname = os.path.dirname(file_path)
    stem = os.path.splitext(os.path.basename(file_path))[0]
    new_path = os.path.join(dirname, f"{stem}.{ext}")

    if dry_run:
        return Result(Status.PREVIEW, file_path, new_path)

    if os.path.exists(new_path):
        return Result(Status.EXISTS, file_path, new_path, "目标文件已存在")

    try:
        os.rename(file_path, new_path)
        return Result(Status.SUCCESS, file_path, new_path)
    except Exception as e:
        return Result(Status.ERROR, file_path, new_path, f"重命名失败: {e}")