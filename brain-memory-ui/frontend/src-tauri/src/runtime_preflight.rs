//! Pre-flight environment scan before starting / reinstalling Runtime API.



use serde::{Deserialize, Serialize};

use std::path::PathBuf;



#[derive(Debug, Clone, Serialize, Deserialize)]

pub struct PreflightConflict {

    pub kind: String,

    pub pid: u32,

    pub name: String,

    pub detail: String,

}



#[derive(Debug, Clone, Serialize, Deserialize)]

pub struct PreflightReport {

    pub conflicts: Vec<PreflightConflict>,

    pub checked_at_ms: u128,

}



impl PreflightReport {

    pub fn has_conflicts(&self) -> bool {

        !self.conflicts.is_empty()

    }



    pub fn conflict_pids(&self) -> Vec<u32> {

        let mut seen = std::collections::HashSet::new();

        let mut pids = Vec::new();

        for conflict in &self.conflicts {

            if conflict.pid > 0 && seen.insert(conflict.pid) {

                pids.push(conflict.pid);

            }

        }

        pids

    }



    pub fn summary_zh(&self) -> String {

        if self.conflicts.is_empty() {

            return "环境检查通过：未发现占用 Runtime 端口或冲突进程。".to_string();

        }

        let mut lines = vec!["检测到以下环境冲突：".to_string()];

        for (i, c) in self.conflicts.iter().enumerate() {

            lines.push(format!(

                "{}. [{}] PID {} ({}) — {}",

                i + 1,

                c.kind,

                c.pid,

                c.name,

                c.detail

            ));

        }

        lines.push(String::new());

        lines.push("继续将停止上述冲突进程并启动 CNexus Runtime（:8000）。".to_string());

        lines.join("\n")

    }

}



pub fn data_dir() -> PathBuf {

    if let Ok(local) = std::env::var("LOCALAPPDATA") {

        return PathBuf::from(local).join("CNexus").join("data");

    }

    if let Ok(home) = std::env::var("USERPROFILE") {

        return PathBuf::from(home).join(".cnexus").join("data");

    }

    PathBuf::from(".cnexus/data")

}



pub fn scan_conflicts() -> PreflightReport {

    let conflicts = scan_conflicts_impl();

    let report = PreflightReport {

        conflicts,

        checked_at_ms: std::time::SystemTime::now()

            .duration_since(std::time::UNIX_EPOCH)

            .map(|d| d.as_millis())

            .unwrap_or(0),

    };

    persist_report(&report);

    report

}



fn persist_report(report: &PreflightReport) {

    let path = data_dir().join("preflight-last.json");

    let _ = std::fs::create_dir_all(data_dir());

    if let Ok(json) = serde_json::to_string_pretty(report) {

        let _ = std::fs::write(path, json);

    }

}



#[cfg(windows)]

fn scan_conflicts_impl() -> Vec<PreflightConflict> {

    let mut conflicts = Vec::new();

    let mut seen = std::collections::HashSet::new();



    for pid in crate::win_process::pids_listening_on_port(8000) {

        if !seen.insert(pid) {

            continue;

        }

        let name = crate::win_process::process_image_for_pid(pid).unwrap_or_else(|| "unknown".into());

        conflicts.push(PreflightConflict {

            kind: "port_8000".into(),

            pid,

            name: name.clone(),

            detail: format!("listening on :8000 ({name})"),

        });

    }



    for image in ["cnexus-product.exe", "cnexus-runtime.exe"] {

        for pid in crate::win_process::pids_for_image(image) {

            if pid == std::process::id() {

                continue;

            }

            if !seen.insert(pid) {

                continue;

            }

            conflicts.push(PreflightConflict {

                kind: "cnexus_process".into(),

                pid,

                name: image.trim_end_matches(".exe").to_string(),

                detail: image.to_string(),

            });

        }

    }



    conflicts

}



#[cfg(not(windows))]

fn scan_conflicts_impl() -> Vec<PreflightConflict> {

    vec![]

}



/// Returns true if the user chose to proceed (clean up conflicts and start Runtime).

pub fn prompt_user_proceed(report: &PreflightReport) -> bool {

    if !report.has_conflicts() {

        return true;

    }

    #[cfg(windows)]

    {

        return prompt_windows(&report.summary_zh());

    }

    #[cfg(not(windows))]

    {

        let _ = report;

        true

    }

}



#[cfg(windows)]

fn prompt_windows(message: &str) -> bool {

    use std::ffi::OsStr;

    use std::os::windows::ffi::OsStrExt;

    use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONWARNING, MB_OKCANCEL, IDOK};



    fn wide(s: &str) -> Vec<u16> {

        OsStr::new(s).encode_wide().chain(std::iter::once(0)).collect()

    }



    let title = wide("CNexus 环境检查");

    let body = wide(message);



    let result = unsafe {

        MessageBoxW(

            std::ptr::null_mut(),

            body.as_ptr(),

            title.as_ptr(),

            MB_OKCANCEL | MB_ICONWARNING,

        )

    };

    result == IDOK

}


