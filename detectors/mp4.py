"""MP4 (ISO BMFF) 容器检测器：区分纯音频与含视频"""

import struct

from .base import Detector


def _read_box_header(f, end):
    if f.tell() + 8 > end:
        return None, None, 0
    data = f.read(8)
    size = struct.unpack('>I', data[:4])[0]
    box_type = data[4:8]
    header_size = 8
    if size == 1:
        if f.tell() + 8 > end:
            return None, None, 0
        ext = f.read(8)
        size = struct.unpack('>Q', ext)[0]
        header_size = 16
    elif size == 0:
        size = end - f.tell() + header_size
    return size, box_type, header_size


def _find_handler(f, start, end):
    """在 trak 内找到 mdia → hdlr，返回 handler_type（4 字节）"""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        size, box_type, header_size = _read_box_header(f, end)
        if size is None or size < header_size or pos + size > end:
            break
        if box_type == b'mdia':
            pos2, end2 = pos + header_size, pos + size
            while pos2 + 8 <= end2:
                f.seek(pos2)
                s2, t2, h2 = _read_box_header(f, end2)
                if s2 is None or s2 < h2 or pos2 + s2 > end2:
                    break
                if t2 == b'hdlr':
                    # 偏移: header + version/flags(4) + pre_defined(4)
                    f.seek(pos2 + h2 + 8)
                    h = f.read(4)
                    return h if len(h) == 4 else None
                pos2 += s2
        pos += size
    return None


def _scan_moov(f, start, end):
    has_video = False
    has_audio = False
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        size, box_type, header_size = _read_box_header(f, end)
        if size is None or size < header_size or pos + size > end:
            break
        if box_type == b'trak':
            hdlr = _find_handler(f, pos + header_size, pos + size)
            if hdlr == b'vide':
                has_video = True
            elif hdlr == b'soun':
                has_audio = True
        pos += size

    if has_video:
        return 'video'
    if has_audio:
        return 'audio'
    return 'unknown'


def _detect_mp4_type(file_path):
    """返回 'audio' / 'video' / 'unknown'"""
    try:
        file_size = file_path and __import__('os').path.getsize(file_path)
        with open(file_path, 'rb') as f:
            pos = 0
            while pos + 8 <= file_size:
                f.seek(pos)
                size, box_type, header_size = _read_box_header(f, file_size)
                if size is None or size < header_size or pos + size > file_size:
                    break
                if box_type == b'moov':
                    return _scan_moov(f, pos + header_size, pos + size)
                pos += size
    except Exception:
        return 'unknown'
    return 'unknown'


class Mp4Detector(Detector):
    name = "mp4"
    target_extensions = ["mp4", "m4a", "m4v"]

    @classmethod
    def refine(cls, file_path, header_hex):
        t = _detect_mp4_type(file_path)
        if t == 'audio':
            return 'm4a'
        if t == 'video':
            return 'mp4'
        return None