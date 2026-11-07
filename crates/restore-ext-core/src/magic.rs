use regex::bytes::Regex;

pub struct MagicRule {
    pub raw: String,
    pub extension: String,
    regex: Option<Regex>,
}

pub struct MagicTable {
    rules: Vec<MagicRule>,
}

impl MagicTable {
    pub fn new(entries: Vec<(String, String)>) -> Self {
        let mut rules = Vec::new();
        for (magic, ext) in entries {
            let magic_upper = magic.to_uppercase().trim().to_string();
            if magic_upper.is_empty() {
                continue;
            }
            let ext = ext.trim_start_matches('.').to_lowercase();

            if magic_upper.contains('*') || magic_upper.contains('?') {
                let pattern = magic_upper
                    .replace('?', "[0-9A-F]")
                    .replace('*', "[0-9A-F]*");
                let regex = Regex::new(&format!("^{}", pattern))
                    .expect("invalid magic pattern");
                rules.push(MagicRule {
                    raw: magic_upper,
                    extension: ext,
                    regex: Some(regex),
                });
            } else {
                rules.push(MagicRule {
                    raw: magic_upper,
                    extension: ext,
                    regex: None,
                });
            }
        }
        // 长魔数优先
        rules.sort_by(|a, b| b.raw.len().cmp(&a.raw.len()));
        Self { rules }
    }

    /// header_hex 为大写十六进制字符串
    pub fn match_header(&self, header_hex: &str) -> Option<&str> {
        for rule in &self.rules {
            match &rule.regex {
                Some(re) => {
                    if re.is_match(header_hex.as_bytes()) {
                        return Some(&rule.extension);
                    }
                }
                None => {
                    if header_hex.starts_with(&rule.raw) {
                        return Some(&rule.extension);
                    }
                }
            }
        }
        None
    }
}