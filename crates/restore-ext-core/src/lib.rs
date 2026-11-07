pub mod magic;
pub mod ogg;
pub mod mp4;

pub use magic::MagicTable;
pub use ogg::{detect_ogg_type, OggType};
pub use mp4::{detect_mp4_type, Mp4Type};

pub struct RefineResult {
    pub extension: String,
    pub detected_type: &'static str, // "audio" / "video" / "unknown"
}

/// 根据粗判扩展名和文件头部，细化扩展名。
pub fn refine_extension(
    matched_ext: &str,
    full_data: &[u8],
    header_hex: &str,
) -> Option<RefineResult> {
    let matched_lower = matched_ext.to_lowercase();

    // OGG
    if matches!(matched_lower.as_str(), "ogg" | "ogv" | "oga") {
        if header_hex.starts_with("4F6767") {
            return match detect_ogg_type(full_data) {
                OggType::Video => Some(RefineResult {
                    extension: "ogv".into(),
                    detected_type: "video",
                }),
                OggType::Audio => Some(RefineResult {
                    extension: "ogg".into(),
                    detected_type: "audio",
                }),
                OggType::Unknown => None,
            };
        }
    }

    // MP4
    if matches!(matched_lower.as_str(), "mp4" | "m4a" | "m4v") {
        // 校验 ftyp 存在
        if header_hex.len() >= 16 && &header_hex[8..16] == "66747970" {
            return match detect_mp4_type(full_data) {
                Mp4Type::Audio => Some(RefineResult {
                    extension: "m4a".into(),
                    detected_type: "audio",
                }),
                Mp4Type::Video => Some(RefineResult {
                    extension: "mp4".into(),
                    detected_type: "video",
                }),
                Mp4Type::Unknown => None,
            };
        }
    }

    None
}