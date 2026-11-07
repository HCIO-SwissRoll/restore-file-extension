pub enum OggType { Audio, Video, Unknown }

pub fn detect_ogg_type(data: &[u8]) -> OggType {
    if data.len() < 4 || &data[..4] != b"OggS" {
        return OggType::Unknown;
    }
    // 页头27字节: version(1) flags(1) granule(8) serial(4) seq(4) crc(4) segments(1)
    if data.len() < 27 { return OggType::Unknown; }
    let flags = data[5];
    if flags & 0x02 == 0 { return OggType::Unknown; } // 非BOS页

    let seg_count = data[26] as usize;
    if data.len() < 27 + seg_count { return OggType::Unknown; }

    // 计算第一个packet长度
    let mut packet_len = 0usize;
    let mut idx = 27;
    for _ in 0..seg_count {
        let seg = data[idx];
        packet_len += seg as usize;
        idx += 1;
        if seg < 255 { break; }
    }
    if packet_len == 0 || data.len() < idx + packet_len {
        return OggType::Unknown;
    }

    let packet = &data[idx..idx + packet_len];
    if packet.len() < 6 { return OggType::Unknown; }

    let ident = String::from_utf8_lossy(&packet[..6]).to_lowercase();
    match ident.as_str() {
        "vorbis" | "opushe" | "flac" | "speex" => OggType::Audio,
        "theora" | "tarkin" => OggType::Video,
        _ => OggType::Unknown,
    }
}