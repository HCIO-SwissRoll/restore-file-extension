"""OGG 容器检测器：区分纯音频与含视频"""

from .base import Detector


def _detect_ogg_type(file_path):
    """返回 'audio' / 'video' / 'unknown'"""
    try:
        with open(file_path, 'rb') as f:
            if f.read(4) != b'OggS':
                return 'unknown'
            page_header = f.read(27)
            if len(page_header) < 27:
                return 'unknown'
            flags = page_header[5]
            if not (flags & 0x02):        # 非 BOS 页
                return 'unknown'
            seg_count = page_header[26]
            seg_table = f.read(seg_count)
            if len(seg_table) < seg_count:
                return 'unknown'

            packet_len = 0
            for i in range(seg_count):
                packet_len += seg_table[i]
                if seg_table[i] < 255:
                    break
            if packet_len == 0:
                return 'unknown'

            packet = f.read(packet_len)
            if len(packet) < 6:
                return 'unknown'
            ident = packet[:6].decode('ascii', errors='ignore').lower()

            if ident in ('vorbis', 'opushe', 'flac', 'speex'):
                return 'audio'
            if ident in ('theora', 'tarkin'):
                return 'video'
            return 'unknown'
    except Exception:
        return 'unknown'


class OggDetector(Detector):
    name = "ogg"
    target_extensions = ["ogg", "ogv", "oga"]

    @classmethod
    def refine(cls, file_path, header_hex):
        t = _detect_ogg_type(file_path)
        if t == 'video':
            return 'ogv'
        if t == 'audio':
            return 'ogg'
        return None