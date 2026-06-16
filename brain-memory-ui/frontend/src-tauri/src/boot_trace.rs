use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;

fn trace_path() -> PathBuf {
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        return PathBuf::from(local).join("CNexus").join("data").join("boot-trace.log");
    }
    PathBuf::from("boot-trace.log")
}

pub fn trace(msg: &str) {
    let path = trace_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(f, "[cnexus-boot] {msg}");
    }
}

pub fn reset_trace() {
    let path = trace_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = std::fs::write(path, "");
}
