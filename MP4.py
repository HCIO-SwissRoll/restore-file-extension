#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MP4 容器流类型检测模块
通过解析 ISO BMFF / QuickTime 盒子结构，判断 MP4 文件是纯音频还是含视频。
提供 detect_mp4_type 函数。
"""

import struct
import os


def detect_mp4_type(file_path):
    """
    检测 MP4 文件内部的流类型。
    返回 'video'、'audio' 或 'unknown'。
    """
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            return _detect(f, 0, file_size)
    except Exception:
        return 'unknown'


def _read_box_header(f, end):
    """
    读取盒子头部。返回 (size, type, header_size)。
    失败返回 (None, None, 0)。
    """
    if f.tell() + 8 > end:
        return None, None, 0
    data = f.read(8)
    size = struct.unpack('>I', data[:4])[0]
    box_type = data[4:8]
    header_size = 8
    if size == 1:
        # 64 位扩展大小
        if f.tell() + 8 > end:
            return None, None, 0
        ext = f.read(8)
        size = struct.unpack('>Q', ext)[0]
        header_size = 16
    elif size == 0:
        # 盒子延伸到文件末尾
        size = end - f.tell() + header_size
    return size, box_type, header_size


def _detect(f, start, end):
    """遍历顶层盒子，找到 moov 后继续扫描。"""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        size, box_type, header_size = _read_box_header(f, end)
        if size is None or size < header_size or pos + size > end:
            break
        if box_type == b'moov':
            return _scan_moov(f, pos + header_size, pos + size)
        pos += size
    return 'unknown'


def _scan_moov(f, start, end):
    """扫描 moov 中的 trak 盒子。"""
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
    elif has_audio:
        return 'audio'
    return 'unknown'


def _find_handler(f, start, end):
    """在 trak 内找到 mdia → hdlr，返回 handler_type 字节。"""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        size, box_type, header_size = _read_box_header(f, end)
        if size is None or size < header_size or pos + size > end:
            break
        if box_type == b'mdia':
            pos2 = pos + header_size
            end2 = pos + size
            while pos2 + 8 <= end2:
                f.seek(pos2)
                s2, t2, h2 = _read_box_header(f, end2)
                if s2 is None or s2 < h2 or pos2 + s2 > end2:
                    break
                if t2 == b'hdlr':
                    # 跳过 版本+标志(4) 和 预定义/组件类型(4)
                    f.seek(pos2 + h2 + 8)
                    handler = f.read(4)
                    if len(handler) == 4:
                        return handler
                    return None
                pos2 += s2
        pos += size
    return None