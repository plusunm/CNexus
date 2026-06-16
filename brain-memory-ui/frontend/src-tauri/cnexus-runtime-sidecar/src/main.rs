//! CNexus Runtime sidecar — process 2 of 2 (API server on 127.0.0.1:8000).
#![windows_subsystem = "windows"]

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[cfg(windows)]
const DETACHED_PROCESS: u32 = 0x0000_0008;

fn log_line(msg: &str) {
    let log_path = app_data_dir().join("runtime-sidecar.log");
    if let Some(parent) = log_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
    {
        use std::io::Write;
        let _ = writeln!(f, "{msg}");
    }
    #[cfg(debug_assertions)]
    eprintln!("{msg}");
}

#[cfg(windows)]
mod win_job {
    use std::mem::{size_of, zeroed};
    use std::os::windows::io::AsRawHandle;
    use std::process::Child;
    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
        SetInformationJobObject,
    };

    pub struct KillJob(HANDLE);

    impl KillJob {
        pub fn new() -> Result<Self, String> {
            unsafe {
                let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
                if job.is_null() {
                    return Err("CreateJobObjectW failed".into());
                }
                let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = zeroed();
                info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
                let ok = SetInformationJobObject(
                    job,
                    JobObjectExtendedLimitInformation,
                    &info as *const _ as *const _,
                    size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
                );
                if ok == 0 {
                    CloseHandle(job);
                    return Err("SetInformationJobObject failed".into());
                }
                Ok(KillJob(job))
            }
        }

        pub fn assign(&self, child: &Child) -> Result<(), String> {
            unsafe {
                if AssignProcessToJobObject(self.0, child.as_raw_handle() as HANDLE) == 0 {
                    return Err("AssignProcessToJobObject failed".into());
                }
                Ok(())
            }
        }
    }

    impl Drop for KillJob {
        fn drop(&mut self) {
            unsafe {
                CloseHandle(self.0);
            }
        }
    }
}

fn main() {
    if let Err(err) = run() {
        log_line(&format!("[cnexus-runtime] ERROR: {err}"));
        std::process::exit(1);
    }
}

fn ensure_conflict_monitor_log() {
    let data_dir = app_data_dir();
    let _ = std::fs::create_dir_all(&data_dir);
    let log_path = data_dir.join("runtime-conflict-monitor.log");
    if log_path.is_file() {
        return;
    }
    let template = find_resource_bundle()
        .map(|b| b.join("app/data-templates/runtime-conflict-monitor.log"));
    if let Some(ref tpl) = template {
        if tpl.is_file() {
            if std::fs::copy(tpl, &log_path).is_ok() {
                log_line(&format!("initialized conflict monitor log from bundle template: {}", log_path.display()));
                return;
            }
        }
    }
    let seed = r#"{"event":"SIDECAR_INITIALIZED","level":"info","source":"sidecar","message":"Runtime conflict monitor log created at sidecar start"}
"#;
    if std::fs::write(&log_path, seed).is_ok() {
        log_line(&format!("initialized conflict monitor log: {}", log_path.display()));
    }
}

fn run() -> Result<(), String> {
    ensure_conflict_monitor_log();
    let (python, workdir, envs) = resolve_runtime()?;
    log_line(&format!(
        "starting API in {} via {}",
        workdir.display(),
        python.display()
    ));

    let stderr_log = app_data_dir().join("runtime-api.stderr.log");
    let stderr_file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&stderr_log)
        .map_err(|e| format!("stderr log open failed: {e}"))?;

    let mut cmd = Command::new(&python);
    cmd.current_dir(&workdir)
        .arg("-m")
        .arg("api.main")
        .stdout(Stdio::null())
        .stderr(Stdio::from(stderr_file));

    for (k, v) in &envs {
        cmd.env(k, v);
    }
    cmd.env_remove("PYTHONHOME");
    cmd.env_remove("PYTHONPATH");

    #[cfg(windows)]
    {
        cmd.creation_flags(CREATE_NO_WINDOW | DETACHED_PROCESS);
    }
    #[cfg(windows)]
    let job = win_job::KillJob::new()?;

    let mut child = cmd.spawn().map_err(|e| format!("spawn failed: {e}"))?;

    #[cfg(windows)]
    job.assign(&child)?;

    let status = child.wait().map_err(|e| format!("wait failed: {e}"))?;
    log_line(&format!(
        "API process exited code={}",
        status.code().unwrap_or(-1)
    ));
    std::process::exit(status.code().unwrap_or(1));
}

fn resolve_runtime() -> Result<(PathBuf, PathBuf, Vec<(String, String)>), String> {
    if let Some(bundle) = find_resource_bundle() {
        return bundle_runtime(bundle);
    }
    if let Some(dev) = dev_repo_runtime() {
        return Ok(dev);
    }
    Err(
        "Runtime bundle not found. Run scripts/bundle-runtime-for-desktop.ps1 before tauri build."
            .to_string(),
    )
}

fn find_resource_bundle() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let bin_dir = exe.parent()?;

    for base in [
        bin_dir.join("resources/runtime-bundle"),
        bin_dir.join("../resources/runtime-bundle"),
        bin_dir.join("runtime-bundle"),
        bin_dir.join("_up_/resources/runtime-bundle"),
    ] {
        if base.join("app/brain-memory-ui/api/main.py").is_file() {
            return Some(base.canonicalize().unwrap_or(base));
        }
    }
    None
}

fn sidecar_network_env() -> Vec<(String, String)> {
    let ollama_host = std::env::var("OLLAMA_HOST")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| "http://127.0.0.1:11434".to_string());
    let no_proxy = "localhost,127.0.0.1,::1";
    vec![
        ("OLLAMA_HOST".into(), ollama_host),
        ("NO_PROXY".into(), no_proxy.into()),
        ("no_proxy".into(), no_proxy.into()),
    ]
}

fn append_network_env(envs: &mut Vec<(String, String)>) {
    for (k, v) in sidecar_network_env() {
        if !envs.iter().any(|(ek, _)| ek == &k) {
            envs.push((k, v));
        }
    }
}

fn bundle_runtime(bundle: PathBuf) -> Result<(PathBuf, PathBuf, Vec<(String, String)>), String> {
    let app_root = bundle.join("app");
    let workdir = app_root.join("brain-memory-ui");
    let python = bundled_python(&bundle).ok_or_else(|| {
        "Bundled python.exe missing — re-run bundle-runtime-for-desktop.ps1".to_string()
    })?;

    let data_dir = app_data_dir();
    let _ = std::fs::create_dir_all(&data_dir);
    // Kuzu owns its database path — do not pre-create kuzu_db as an empty directory.
    for sub in ["blocks", "lancedb"] {
        let _ = std::fs::create_dir_all(data_dir.join(sub));
    }

    let mut pythonpath = vec![
        workdir.to_string_lossy().into_owned(),
        app_root.to_string_lossy().into_owned(),
    ];
    if let Some(site) = site_packages(&bundle) {
        pythonpath.push(site.to_string_lossy().into_owned());
    }

    let edition = read_edition_config(&app_root);
    let mut envs = vec![
        ("BRAIN_MEMORY_ROOT".into(), app_root.to_string_lossy().into_owned()),
        ("BM_MEMORY_DIR".into(), data_dir.to_string_lossy().into_owned()),
        ("CNEXUS_EDITION".into(), edition.clone()),
        // Boot/cognitive timeout uses deploy level — keep internal for bundled desktop (license via CNEXUS_EDITION).
        ("CNEXUS_DEPLOY_LEVEL".into(), "internal".into()),
        ("BM_API_PORT".into(), "8000".into()),
        ("CNEXUS_AUTO_RUNTIME_WARM".into(), "1".into()),
        ("CNEXUS_CONTROL_PLANE_ISOLATION".into(), "1".into()),
        ("CNEXUS_SKIP_PORT_GUARD".into(), "1".into()),
        ("CNEXUS_FAST_PATH_V3".into(), "0".into()),
        ("CNEXUS_NON_HANG_V5".into(), "0".into()),
        ("CNEXUS_NON_HANG_V4".into(), "0".into()),
        ("CNEXUS_NON_HANG_V3".into(), "0".into()),
        ("CNEXUS_LOCAL_STACK_BOOTSTRAP_MODELS".into(), "0".into()),
        ("PYTHONPATH".into(), pythonpath.join(";")),
        ("PYTHONNOUSERSITE".into(), "1".into()),
        ("PYTHONIOENCODING".into(), "utf-8".into()),
        ("PYTHONUTF8".into(), "1".into()),
    ];

    if let Some(license) = read_license_file() {
        envs.push(("CNEXUS_LICENSE".into(), license));
    }
    if let Ok(token) = std::env::var("CNEXUS_API_TOKEN") {
        if !token.is_empty() {
            envs.push(("CNEXUS_API_TOKEN".into(), token));
        }
    }

    append_network_env(&mut envs);
    for (k, v) in sidecar_network_env() {
        log_line(&format!("sidecar env {k}={v}"));
    }

    Ok((python, workdir, envs))
}

fn bundled_python(bundle: &Path) -> Option<PathBuf> {
    let pyw = bundle.join("python/pythonw.exe");
    if pyw.is_file() {
        return Some(pyw);
    }
    // Never fall back to python.exe — console subsystem flashes CMD windows on Windows.
    None
}

fn site_packages(bundle: &Path) -> Option<PathBuf> {
    let site = bundle.join("python/Lib/site-packages");
    if site.is_dir() {
        Some(site)
    } else {
        None
    }
}

fn dev_repo_runtime() -> Option<(PathBuf, PathBuf, Vec<(String, String)>)> {
    if !cfg!(debug_assertions) {
        return None;
    }
    let repo = discover_dev_repo()?;
    if !repo.join("brain-memory-ui/api/main.py").is_file() {
        return None;
    }
    let python = which_python()?;
    let workdir = repo.join("brain-memory-ui");
    let data = app_data_dir();
    let _ = std::fs::create_dir_all(&data);
    let mut envs = vec![
        ("BRAIN_MEMORY_ROOT".into(), repo.to_string_lossy().into_owned()),
        ("BM_MEMORY_DIR".into(), data.to_string_lossy().into_owned()),
        ("CNEXUS_EDITION".into(), "personal".into()),
        ("CNEXUS_DEPLOY_LEVEL".into(), "dev".into()),
        ("CNEXUS_AUTO_RUNTIME_WARM".into(), "1".into()),
        ("CNEXUS_CONTROL_PLANE_ISOLATION".into(), "1".into()),
        ("CNEXUS_SKIP_PORT_GUARD".into(), "1".into()),
        ("PYTHONPATH".into(), format!("{};{}", workdir.display(), repo.display())),
    ];
    append_network_env(&mut envs);
    log_line(&format!("dev repo runtime: {}", repo.display()));
    Some((python, workdir, envs))
}

fn discover_dev_repo() -> Option<PathBuf> {
    if let Ok(repo) = std::env::var("CNEXUS_DEV_REPO") {
        let path = PathBuf::from(repo);
        if path.join("brain-memory-ui/api/main.py").is_file() {
            return Some(path);
        }
    }
    let mut dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    for _ in 0..12 {
        if dir.join("brain-memory-ui/api/main.py").is_file()
            && dir.join("brain_memory/runtime.py").is_file()
        {
            return Some(dir);
        }
        if !dir.pop() {
            break;
        }
    }
    None
}

fn which_python() -> Option<PathBuf> {
    #[cfg(windows)]
    use std::os::windows::process::CommandExt;
    #[cfg(windows)]
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;

    for cmd in ["python", "py"] {
        let mut command = Command::new(cmd);
        command.args(["-c", "import sys; print(sys.executable)"]);
        #[cfg(windows)]
        {
            command.creation_flags(CREATE_NO_WINDOW);
        }
        if let Ok(output) = command.output() {
            if output.status.success() {
                let path = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
                if path.is_file() {
                    return Some(path);
                }
            }
        }
    }
    None
}

fn app_data_dir() -> PathBuf {
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        return PathBuf::from(local).join("CNexus").join("data");
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        return PathBuf::from(home).join(".cnexus").join("data");
    }
    PathBuf::from(".cnexus-data")
}

fn read_edition_config(app_root: &Path) -> String {
    let cfg_path = app_root.join("cnexus-config.json");
    if !cfg_path.is_file() {
        return "personal".into();
    }
    let raw = std::fs::read_to_string(cfg_path).unwrap_or_default();
    if raw.contains("\"enterprise\"") || raw.contains("'enterprise'") {
        "enterprise".into()
    } else {
        "personal".into()
    }
}

fn read_license_file() -> Option<String> {
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        let p = PathBuf::from(local).join("CNexus").join("license.cnx");
        if p.is_file() {
            let v = std::fs::read_to_string(p).ok()?.trim().to_string();
            if !v.is_empty() {
                return Some(v);
            }
        }
    }
    let p = PathBuf::from("license.cnx");
    if p.is_file() {
        let v = std::fs::read_to_string(p).ok()?.trim().to_string();
        if !v.is_empty() {
            return Some(v);
        }
    }
    None
}
