#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OGG 容器流类型检测模块
提供 detect_ogg_type 函数，用于判断 OGG 文件是纯音频还是视频。
"""

import struct

def detect_ogg_type(file_path):
    """
    检测 OGG 文件内部第一个逻辑流的类型。
    返回 'audio' 或 'video' 或 'unknown'。
    若检测失败或不是 OGG，返回 'unknown'。
    """
    try:
        with open(file_path, 'rb') as f:
            # 验证 OggS 标识
            header = f.read(4)
            if header != b'OggS':
                return 'unknown'

            # 读取页头前 27 字节
            page_header = f.read(27)
            if len(page_header) < 27:
                return 'unknown'

            # flags 在第 5 个字节（索引 5）
            flags = page_header[5]
            if not (flags & 0x02):  # 不是 BOS 页
                return 'unknown'

            # segment table 长度（第 26 字节）
            seg_count = page_header[26]
            seg_table = f.read(seg_count)
            if len(seg_table) < seg_count:
                return 'unknown'

            # 计算第一个 packet 的总长度（考虑 segment 分段）
            packet_len = 0
            for i in range(seg_count):
                packet_len += seg_table[i]
                if seg_table[i] < 255:
                    break
            if packet_len == 0:
                return 'unknown'

            # 读取 packet 数据
            packet_data = f.read(packet_len)
            if len(packet_data) < 6:
                return 'unknown'

            # 解码前 6 字节作为标识
            ident = packet_data[:6].decode('ascii', errors='ignore').lower()

            # 已知音频编码
            audio_codes = ('vorbis', 'opushe', 'flac', 'speex')
            # 已知视频编码
            video_codes = ('theora', 'tarkin')

            if ident in audio_codes:
                return 'audio'
            elif ident in video_codes:
                return 'video'
            else:
                return 'unknown'

    except Exception:
        return 'unknown'