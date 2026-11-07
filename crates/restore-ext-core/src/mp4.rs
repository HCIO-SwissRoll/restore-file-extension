pub enum Mp4Type { Audio, Video, Unknown }

fn read_box_header(data: &[u8], pos: usize) -> Option<(usize, &[u8], usize)> {
    // 返回 (box_size, box_type, header_size)
    if pos + 8 > data.len() { return None; }
    let size = u32::from_be_bytes(data[pos..pos + 4].try_into().ok()?) as usize;
    let box_type = &data[pos + 4..pos + 8];
    let mut header_size = 8;
    let mut size = size;
    if size == 1 {
        if pos + 16 > data.len() { return None; }
        size = u64::from_be_bytes(data[pos + 8..pos + 16].try_into().ok()?) as usize;
        header_size = 16;
    } else if size == 0 {
        size = data.len() - pos;
    }
    if size < header_size || pos + size > data.len() { return None; }
    Some((size, box_type, header_size))
}

fn find_handler(data: &[u8], start: usize, end: usize) -> Option<[u8; 4]> {
    let mut pos = start;
    while pos + 8 <= end {
        let (size, box_type, hdr) = read_box_header(&data[..end], pos)?;
        if box_type == b"mdia" {
            let inner_start = pos + hdr;
            let inner_end = pos + size;
            let mut p = inner_start;
            while p + 8 <= inner_end {
                let (s2, t2, h2) = read_box_header(&data[..inner_end], p)?;
                if t2 == b"hdlr" {
                    // hdlr: version/flags(4) + pre_defined(4) + handler_type(4)
                    let ht_pos = p + h2 + 8;
                    if ht_pos + 4 <= inner_end {
                        let mut ht = [0u8; 4];
                        ht.copy_from_slice(&data[ht_pos..ht_pos + 4]);
                        return Some(ht);
                    }
                    return None;
                }
                p += s2;
            }
        }
        pos += size;
    }
    None
}

pub fn detect_mp4_type(data: &[u8]) -> Mp4Type {
    let mut pos = 0usize;
    while pos + 8 <= data.len() {
        let Some((size, box_type, hdr)) = read_box_header(data, pos) else { break };
        if box_type == b"moov" {
            let moov_start = pos + hdr;
            let moov_end = pos + size;

            let mut has_video = false;
            let mut has_audio = false;
            let mut p = moov_start;
            while p + 8 <= moov_end {
                let Some((s2, t2, h2)) = read_box_header(&data[..moov_end], p) else { break };
                if t2 == b"trak" {
                    if let Some(ht) = find_handler(data, p + h2, p + s2) {
                        match &ht {
                            b"vide" => has_video = true,
                            b"soun" => has_audio = true,
                            _ => {}
                        }
                    }
                }
                p += s2;
            }
            if has_video { return Mp4Type::Video; }
            if has_audio { return Mp4Type::Audio; }
            return Mp4Type::Unknown;
        }
        pos += size;
    }
    Mp4Type::Unknown
}