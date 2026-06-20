//! PE helpers: section scan, export resolution without GetProcAddress.

use std::path::Path;

pub const DETOUR_SECTIONS: &[&[u8]] = &[b".detourc", b".detourd"];

/// Read PE section names from disk; detect Detours hook frameworks.
pub fn has_detour_sections(path: &Path) -> bool {
    let Ok(data) = std::fs::read(path) else {
        return false;
    };
    pe_section_names(&data)
        .iter()
        .any(|name| DETOUR_SECTIONS.iter().any(|m| name.starts_with(m)))
}

fn pe_section_names(data: &[u8]) -> Vec<Vec<u8>> {
    if data.len() < 0x40 {
        return vec![];
    }
    let pe_off = u32::from_le_bytes(data[0x3c..0x40].try_into().unwrap_or([0; 4])) as usize;
    if pe_off + 24 > data.len() || &data[pe_off..pe_off + 4] != b"PE\0\0" {
        return vec![];
    }
    let num_sections = u16::from_le_bytes(data[pe_off + 6..pe_off + 8].try_into().unwrap_or([0; 2]))
        as usize;
    let opt_hdr_size =
        u16::from_le_bytes(data[pe_off + 20..pe_off + 22].try_into().unwrap_or([0; 2])) as usize;
    let sec_off = pe_off + 24 + opt_hdr_size;
    let mut names = Vec::new();
    for i in 0..num_sections {
        let off = sec_off + i * 40;
        if off + 8 > data.len() {
            break;
        }
        names.push(data[off..off + 8].to_vec());
    }
    names
}

/// Resolve an exported symbol RVA from a DLL on disk (no GetProcAddress).
#[allow(dead_code)]
pub fn resolve_export_rva(dll_path: &Path, func_name: &str) -> Option<u32> {
    let data = std::fs::read(dll_path).ok()?;
    parse_export_rva(&data, func_name)
}

fn parse_export_rva(data: &[u8], func_name: &str) -> Option<u32> {
    if data.len() < 0x40 {
        return None;
    }
    let pe_off = u32::from_le_bytes(data[0x3c..0x40].try_into().ok()?) as usize;
    if pe_off + 24 > data.len() || &data[pe_off..pe_off + 4] != b"PE\0\0" {
        return None;
    }
    let opt_off = pe_off + 24;
    let magic = u16::from_le_bytes(data[opt_off..opt_off + 2].try_into().ok()?);
    let is_pe32_plus = magic == 0x20b;
    let export_dir_offset = if is_pe32_plus { 112 } else { 96 };
    if opt_off + export_dir_offset + 8 > data.len() {
        return None;
    }
    let dir_off = opt_off + export_dir_offset;
    let export_rva = u32::from_le_bytes(data[dir_off..dir_off + 4].try_into().ok()?);
    let export_size = u32::from_le_bytes(data[dir_off + 4..dir_off + 8].try_into().ok()?);
    if export_rva == 0 || export_size == 0 {
        return None;
    }
    let export_offset = rva_to_offset(data, export_rva)?;
    if export_offset + 40 > data.len() {
        return None;
    }
    let names_rva = u32::from_le_bytes(data[export_offset + 24..export_offset + 28].try_into().ok()?);
    let ordinals_rva =
        u32::from_le_bytes(data[export_offset + 32..export_offset + 36].try_into().ok()?);
    let functions_rva =
        u32::from_le_bytes(data[export_offset + 28..export_offset + 32].try_into().ok()?);
    let num_names =
        u32::from_le_bytes(data[export_offset + 16..export_offset + 20].try_into().ok()?);
    let names_off = rva_to_offset(data, names_rva)?;
    let ordinals_off = rva_to_offset(data, ordinals_rva)?;
    let functions_off = rva_to_offset(data, functions_rva)?;

    for i in 0..num_names as usize {
        let name_ptr_off = names_off + i * 4;
        if name_ptr_off + 4 > data.len() {
            break;
        }
        let name_rva = u32::from_le_bytes(data[name_ptr_off..name_ptr_off + 4].try_into().ok()?);
        let name_off = rva_to_offset(data, name_rva)?;
        let export_name = read_cstring(&data[name_off..])?;
        if export_name != func_name {
            continue;
        }
        let ord_off = ordinals_off + i * 2;
        if ord_off + 2 > data.len() {
            return None;
        }
        let ordinal = u16::from_le_bytes(data[ord_off..ord_off + 2].try_into().ok()?) as usize;
        let func_off = functions_off + ordinal * 4;
        if func_off + 4 > data.len() {
            return None;
        }
        return Some(u32::from_le_bytes(
            data[func_off..func_off + 4].try_into().ok()?,
        ));
    }
    None
}

fn rva_to_offset(data: &[u8], rva: u32) -> Option<usize> {
    if data.len() < 0x40 {
        return None;
    }
    let pe_off = u32::from_le_bytes(data[0x3c..0x40].try_into().ok()?) as usize;
    let num_sections = u16::from_le_bytes(data[pe_off + 6..pe_off + 8].try_into().ok()?) as usize;
    let opt_hdr_size =
        u16::from_le_bytes(data[pe_off + 20..pe_off + 22].try_into().ok()?) as usize;
    let sec_off = pe_off + 24 + opt_hdr_size;
    for i in 0..num_sections {
        let off = sec_off + i * 40;
        if off + 40 > data.len() {
            break;
        }
        let virt_addr = u32::from_le_bytes(data[off + 12..off + 16].try_into().ok()?);
        let raw_size = u32::from_le_bytes(data[off + 16..off + 20].try_into().ok()?);
        let raw_ptr = u32::from_le_bytes(data[off + 20..off + 24].try_into().ok()?);
        if rva >= virt_addr && rva < virt_addr + raw_size.max(1) {
            return Some((raw_ptr + (rva - virt_addr)) as usize);
        }
    }
    None
}

fn read_cstring(bytes: &[u8]) -> Option<String> {
    let end = bytes.iter().position(|&b| b == 0).unwrap_or(bytes.len());
    std::str::from_utf8(&bytes[..end]).ok().map(|s| s.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_detour_section_names_in_buffer() {
        let mut data = vec![0u8; 512];
        data[0] = b'M';
        data[1] = b'Z';
        data[0x3c..0x40].copy_from_slice(&128u32.to_le_bytes());
        let pe_off = 128usize;
        data[pe_off..pe_off + 4].copy_from_slice(b"PE\0\0");
        data[pe_off + 6..pe_off + 8].copy_from_slice(&1u16.to_le_bytes());
        data[pe_off + 20..pe_off + 22].copy_from_slice(&224u16.to_le_bytes());
        let sec_off = pe_off + 24 + 224;
        data[sec_off..sec_off + 8].copy_from_slice(b".detourc");
        assert!(pe_section_names(&data)
            .iter()
            .any(|n| n.starts_with(b".detourc")));
    }
}
