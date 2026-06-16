//! Hidden Windows subprocess helpers — avoid flashing CMD during startup/cleanup.

#[cfg(windows)]
use std::collections::HashSet;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[cfg(windows)]
const DETACHED_PROCESS: u32 = 0x0000_0008;

#[cfg(windows)]
fn hidden_creation_flags() -> u32 {
    CREATE_NO_WINDOW | DETACHED_PROCESS
}

#[cfg(windows)]
pub fn pids_listening_on_port(port: u16) -> Vec<u32> {
    let Ok(output) = std::process::Command::new("netstat")
        .args(["-ano", "-p", "tcp"])
        .creation_flags(hidden_creation_flags())
        .output()
    else {
        return vec![];
    };
    if !output.status.success() {
        return vec![];
    }

    let text = String::from_utf8_lossy(&output.stdout);
    let needle = format!(":{port}");
    let mut seen = HashSet::new();
    let mut pids = Vec::new();

    for line in text.lines() {
        let upper = line.to_uppercase();
        if !upper.contains("LISTENING") || !line.contains(&needle) {
            continue;
        }
        let Some(pid_raw) = line.split_whitespace().last() else {
            continue;
        };
        let Ok(pid) = pid_raw.parse::<u32>() else {
            continue;
        };
        if pid > 0 && seen.insert(pid) {
            pids.push(pid);
        }
    }
    pids
}

#[cfg(windows)]
pub fn process_image_for_pid(pid: u32) -> Option<String> {
    if pid == 0 {
        return None;
    }
    let filter = format!("PID eq {pid}");
    let Ok(output) = std::process::Command::new("tasklist")
        .args(["/FI", &filter, "/FO", "CSV", "/NH"])
        .creation_flags(hidden_creation_flags())
        .output()
    else {
        return None;
    };
    if !output.status.success() {
        return None;
    }
    let line = String::from_utf8_lossy(&output.stdout);
    let line = line.trim();
    if line.is_empty() || line.contains("No tasks") {
        return None;
    }
    // "Image Name","PID","Session Name","Session#","Mem Usage"
    let first = line.split(',').next()?;
    Some(first.trim_matches('"').to_string())
}

#[cfg(windows)]
pub fn pids_for_image(image: &str) -> Vec<u32> {
    let filter = format!("IMAGENAME eq {image}");
    let Ok(output) = std::process::Command::new("tasklist")
        .args(["/FI", &filter, "/FO", "CSV", "/NH"])
        .creation_flags(hidden_creation_flags())
        .output()
    else {
        return vec![];
    };
    if !output.status.success() {
        return vec![];
    }

    let mut pids = Vec::new();
    for line in String::from_utf8_lossy(&output.stdout).lines() {
        let line = line.trim();
        if line.is_empty() || line.contains("No tasks") {
            continue;
        }
        let fields: Vec<&str> = line.split(',').collect();
        if fields.len() < 2 {
            continue;
        }
        let pid_raw = fields[1].trim_matches('"');
        if let Ok(pid) = pid_raw.parse::<u32>() {
            if pid > 0 {
                pids.push(pid);
            }
        }
    }
    pids
}

#[cfg(windows)]
pub fn hidden_taskkill_pid(pid: u32) {
    if pid == 0 {
        return;
    }
    let _ = std::process::Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .creation_flags(hidden_creation_flags())
        .output();
}

#[cfg(windows)]
pub fn hidden_taskkill_image(image: &str) {
    let _ = std::process::Command::new("taskkill")
        .args(["/F", "/T", "/IM", image])
        .creation_flags(hidden_creation_flags())
        .output();
}

#[cfg(windows)]
pub fn kill_port_listeners(port: u16) {
    let pids = pids_listening_on_port(port);
    let mut seen = HashSet::new();
    for pid in pids {
        if seen.insert(pid) {
            hidden_taskkill_pid(pid);
        }
    }
}

#[cfg(windows)]
pub fn kill_unique_pids(pids: impl IntoIterator<Item = u32>) {
    let mut seen = HashSet::new();
    for pid in pids {
        if pid > 0 && seen.insert(pid) {
            hidden_taskkill_pid(pid);
        }
    }
}

#[cfg(not(windows))]
pub fn pids_listening_on_port(_port: u16) -> Vec<u32> {
    vec![]
}

#[cfg(not(windows))]
pub fn process_image_for_pid(_pid: u32) -> Option<String> {
    None
}

#[cfg(not(windows))]
pub fn pids_for_image(_image: &str) -> Vec<u32> {
    vec![]
}

#[cfg(not(windows))]
pub fn hidden_taskkill_pid(_pid: u32) {}

#[cfg(not(windows))]
pub fn hidden_taskkill_image(_image: &str) {}

#[cfg(not(windows))]
pub fn kill_port_listeners(_port: u16) {}

#[cfg(not(windows))]
pub fn kill_unique_pids(_pids: impl IntoIterator<Item = u32>) {}
