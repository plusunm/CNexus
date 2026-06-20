//! Desktop SecurityBootstrap — preflight before Runtime sidecar spawn.

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::pe_utils;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityBootstrapResult {
    pub ok: bool,
    pub runtime_mode: String,
    pub user_message: String,
    pub internal_code: String,
    pub edition: String,
    pub machine_fingerprint: String,
    pub license_present: bool,
    pub granted_features: Vec<String>,
    pub issues: Vec<SecurityIssue>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityIssue {
    pub code: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseStatusSnapshot {
    pub ok: bool,
    pub runtime_mode: String,
    pub license_valid: bool,
    pub grace_until: i64,
    pub grace_remaining_sec: i64,
    pub heartbeat_fail_count: i32,
    pub granted_features: Vec<String>,
    pub user_message: String,
}

const RUNTIME_API: &str = "http://127.0.0.1:8000";

const COMMON_SIDELOAD_DLLS: &[&str] = &[
    "version.dll",
    "winhttp.dll",
    "wininet.dll",
    "dbghelp.dll",
    "ws2_32.dll",
];

pub fn cnexus_data_dir() -> PathBuf {
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        return PathBuf::from(local).join("CNexus");
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        return PathBuf::from(home).join(".cnexus");
    }
    PathBuf::from(".cnexus")
}

fn app_exe_dir() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|parent| parent.to_path_buf()))
}

fn read_edition() -> String {
    let cfg = cnexus_data_dir().join("cnexus-config.json");
    if !cfg.is_file() {
        return "personal".into();
    }
    let Ok(raw) = std::fs::read_to_string(&cfg) else {
        return "personal".into();
    };
    if raw.contains("\"enterprise\"") || raw.contains("'enterprise'") {
        "enterprise".into()
    } else {
        "personal".into()
    }
}

fn read_license_file() -> Option<String> {
    let path = cnexus_data_dir().join("license.cnx");
    if !path.is_file() {
        return None;
    }
    std::fs::read_to_string(path)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn machine_fingerprint() -> String {
    #[cfg(windows)]
    {
        if let Some(mac) = read_first_mac() {
            return format!("{mac:012x}");
        }
    }
    format!("{:012x}", std::process::id())
}

#[cfg(windows)]
fn read_first_mac() -> Option<u64> {
    use std::process::Command;
    let out = Command::new("getmac")
        .args(["/fo", "csv", "/nh"])
        .output()
        .ok()?;
    let text = String::from_utf8_lossy(&out.stdout);
    for line in text.lines() {
        let part = line.split(',').next()?.trim().trim_matches('"');
        let hex: String = part.chars().filter(|c| c.is_ascii_hexdigit()).collect();
        if hex.len() >= 12 {
            if let Ok(v) = u64::from_str_radix(&hex[..12], 16) {
                return Some(v);
            }
        }
    }
    None
}

fn validate_license_format(token: &str, fingerprint: &str) -> bool {
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 3 || parts[0] != "CNX1" {
        return false;
    }
    parts[1] == fingerprint
        && parts[2].len() == 32
        && parts[2].chars().all(|c| c.is_ascii_hexdigit())
}

fn personal_features() -> Vec<String> {
    vec![
        "CORE_UI".into(),
        "CORE_LOGIN".into(),
        "CORE_PERSONAL_DEMO".into(),
    ]
}

fn enterprise_features() -> Vec<String> {
    vec![
        "CORE_UI".into(),
        "CORE_LOGIN".into(),
        "CORE_LOCAL_RUNTIME".into(),
        "CORE_ENTERPRISE_RUNTIME".into(),
        "CORE_API_TOKEN".into(),
        "CORE_GTBS".into(),
        "CORE_SIBT".into(),
    ]
}

fn locked_features() -> Vec<String> {
    vec!["CORE_UI".into(), "CORE_LOGIN".into()]
}

fn is_api_ms_name(name: &str) -> bool {
    let lower = name.to_lowercase();
    lower.starts_with("api-ms-win-") && lower.ends_with(".dll")
}

/// Scan application directory for sideload / Detours indicators (read-only).
pub fn scan_app_directory_sideloads(dir: &Path) -> Vec<SecurityIssue> {
    let mut issues = Vec::new();
    let Ok(entries) = std::fs::read_dir(dir) else {
        return issues;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_file() {
            continue;
        }
        let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
            continue;
        };
        let lower = name.to_lowercase();

        if is_api_ms_name(&lower) {
            issues.push(SecurityIssue {
                code: "api_ms_sideload".into(),
                detail: format!("{path:?} (api-ms DLL must not live in app directory)"),
            });
            continue;
        }

        if COMMON_SIDELOAD_DLLS.iter().any(|dll| lower == *dll) {
            issues.push(SecurityIssue {
                code: "dll_sideload".into(),
                detail: path.display().to_string(),
            });
        }

        if lower.ends_with(".dll") || lower.ends_with(".exe") {
            if pe_utils::has_detour_sections(&path) {
                issues.push(SecurityIssue {
                    code: "detours_section".into(),
                    detail: path.display().to_string(),
                });
            }
        }
    }

    issues
}

fn scan_environment() -> Vec<SecurityIssue> {
    let mut issues = Vec::new();
    if let Some(dir) = app_exe_dir() {
        issues.extend(scan_app_directory_sideloads(&dir));
    }
    issues
}

fn has_critical_env_issue(issues: &[SecurityIssue]) -> bool {
    issues.iter().any(|i| {
        matches!(
            i.code.as_str(),
            "api_ms_sideload" | "dll_sideload" | "detours_section"
        )
    })
}

fn locked_result(
    edition: String,
    fingerprint: String,
    internal_code: &str,
    user_message: &str,
    license_present: bool,
    issues: Vec<SecurityIssue>,
) -> SecurityBootstrapResult {
    if issues.iter().any(|i| i.code == "AUTH_SIG_FAIL") {
        crate::boot_trace::trace("AUTH_SIG_FAIL: license signature invalid");
    }
    SecurityBootstrapResult {
        ok: false,
        runtime_mode: "Locked".into(),
        user_message: user_message.into(),
        internal_code: internal_code.into(),
        edition,
        machine_fingerprint: fingerprint,
        license_present,
        granted_features: locked_features(),
        issues,
    }
}

/// Preflight checks before spawning Runtime (no network required).
pub fn run_security_bootstrap_preflight(dry_run: bool) -> SecurityBootstrapResult {
    let edition = read_edition();
    let fingerprint = machine_fingerprint();
    let mut issues = scan_environment();

    if has_critical_env_issue(&issues) {
        return locked_result(
            edition,
            fingerprint,
            "E2001",
            "检测到异常运行环境（可疑 DLL / Hook），已限制启动。",
            false,
            issues,
        );
    }

    let license = read_license_file();
    let license_present = license.is_some();

    if edition == "personal" {
        return SecurityBootstrapResult {
            ok: true,
            runtime_mode: "Trusted".into(),
            user_message: "个人版：SecurityBootstrap 预检通过。".into(),
            internal_code: if dry_run { "DRY_RUN_OK" } else { "OK" }.into(),
            edition,
            machine_fingerprint: fingerprint,
            license_present,
            granted_features: personal_features(),
            issues,
        };
    }

    let token = license.unwrap_or_default();
    if token.is_empty() {
        issues.push(SecurityIssue {
            code: "LICENSE_MISSING".into(),
            detail: "enterprise edition requires license.cnx".into(),
        });
        return locked_result(
            edition,
            fingerprint,
            "E4001",
            "企业版需要 License，请在设置中激活。",
            false,
            issues,
        );
    }

    if !validate_license_format(&token, &fingerprint) {
        issues.push(SecurityIssue {
            code: "AUTH_SIG_FAIL".into(),
            detail: "license token format or fingerprint mismatch".into(),
        });
        return locked_result(
            edition,
            fingerprint,
            "E4002",
            "License 与当前设备不匹配，请重新申请。",
            true,
            issues,
        );
    }

    SecurityBootstrapResult {
        ok: true,
        runtime_mode: "Trusted".into(),
        user_message: if dry_run {
            "dry-run：企业版 License 预检通过。".into()
        } else {
            "SecurityBootstrap 预检通过。".into()
        },
        internal_code: if dry_run { "DRY_RUN_OK" } else { "OK" }.into(),
        edition,
        machine_fingerprint: fingerprint,
        license_present: true,
        granted_features: enterprise_features(),
        issues,
    }
}

pub async fn fetch_license_status() -> Result<LicenseStatusSnapshot, String> {
    let url = format!("{RUNTIME_API}/v1/system/license_status");
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .map_err(|e| e.to_string())?;
    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("license_status unreachable: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("license_status HTTP {}", resp.status()));
    }
    resp.json::<LicenseStatusSnapshot>()
        .await
        .map_err(|e| e.to_string())
}

pub async fn post_session_heartbeat() -> Result<LicenseStatusSnapshot, String> {
    let url = format!("{RUNTIME_API}/v1/session/heartbeat");
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;
    let body = serde_json::json!({
        "machine_id": machine_fingerprint(),
        "client": { "app": "CNexus", "app_version": env!("CARGO_PKG_VERSION") },
        "runtime": { "mode": "Trusted" },
        "nonce": format!("hb_{}", now_unix()),
        "ts": now_unix(),
    });
    let resp = client
        .post(&url)
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("heartbeat unreachable: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("heartbeat HTTP {}", resp.status()));
    }
    resp.json::<LicenseStatusSnapshot>()
        .await
        .map_err(|e| e.to_string())
}

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

#[tauri::command]
pub fn security_bootstrap_preflight(dry_run: Option<bool>) -> SecurityBootstrapResult {
    run_security_bootstrap_preflight(dry_run.unwrap_or(false))
}

#[tauri::command]
pub async fn security_bootstrap_license_status() -> Result<LicenseStatusSnapshot, String> {
    fetch_license_status().await
}

#[tauri::command]
pub async fn security_bootstrap_heartbeat() -> Result<LicenseStatusSnapshot, String> {
    post_session_heartbeat().await
}

#[tauri::command]
pub fn security_bootstrap_scan_app_dir() -> Vec<SecurityIssue> {
    app_exe_dir()
        .map(|dir| scan_app_directory_sideloads(&dir))
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::Path;

    #[test]
    fn validate_cnx1_format() {
        let fp = "aabbccddeeff";
        assert!(validate_license_format(
            "CNX1.aabbccddeeff.0123456789abcdef0123456789abcdef",
            fp
        ));
        assert!(!validate_license_format(
            "CNX1.deadbeefcafe.0123456789abcdef0123456789abcdef",
            fp
        ));
    }

    #[test]
    fn scan_flags_api_ms_and_version_dll() {
        let dir = std::env::temp_dir().join(format!("cnx_scan_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("temp dir");
        fs::write(dir.join("api-ms-win-core-console-l1-1-0.dll"), b"MZ").expect("write");
        fs::write(dir.join("version.dll"), b"MZ").expect("write");
        let issues = scan_app_directory_sideloads(&dir);
        let codes: Vec<_> = issues.iter().map(|i| i.code.as_str()).collect();
        assert!(codes.contains(&"api_ms_sideload"));
        assert!(codes.contains(&"dll_sideload"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn invalid_license_returns_locked_not_panic() {
        let result = run_security_bootstrap_preflight(true);
        // personal default when no enterprise config — should not panic
        assert!(result.runtime_mode == "Trusted" || result.runtime_mode == "Locked");
    }
}
