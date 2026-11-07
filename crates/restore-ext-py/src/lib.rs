use pyo3::prelude::*;
// ★ 关键：给核心库的函数起别名，避免与 PyO3 导出函数同名
use restore_ext_core::{refine_extension as core_refine_extension, MagicTable};

/// 魔数表（Python 侧持有一个 Rust MagicTable）
#[pyclass]
struct PyMagicTable {
    inner: MagicTable,
}

#[pymethods]
impl PyMagicTable {
    #[new]
    fn new(entries: Vec<(String, String)>) -> Self {
        Self {
            inner: MagicTable::new(entries),
        }
    }

    /// header_hex: 大写十六进制字符串
    fn match_header(&self, header_hex: &str) -> Option<String> {
        self.inner.match_header(header_hex).map(|s| s.to_string())
    }
}

/// 细化扩展名（OGG / MP4）
/// 返回 (refined_ext, detected_type) 或 None
#[pyfunction]
fn refine_extension(
    matched_ext: &str,
    file_data: &[u8],
    header_hex: &str,
) -> Option<(String, String)> {
    // ★ 调用核心库函数，显式转换 RefineResult -> (String, String)
    match core_refine_extension(matched_ext, file_data, header_hex) {
        Some(r) => Some((r.extension, r.detected_type.to_string())),
        None => None,
    }
}

#[pymodule]
fn restore_ext_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMagicTable>()?;
    m.add_function(wrap_pyfunction!(refine_extension, m)?)?;
    Ok(())
}