use std::path::PathBuf;
use std::sync::Mutex;

use tauri::{AppHandle, Emitter, Manager, RunEvent};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

use crate::boot_state;
use crate::runtime_cleanup::{
    force_kill_orphan_runtime, resolve_preflight_conflicts, stop_runtime_processes_fast,
    stop_runtime_processes_for_restart,
};
use crate::runtime_preflight;

/// Managed runtime sidecar PID — avoids Tauri shell (can flash cmd.exe on Windows).
pub struct RuntimeProcess(Mutex<Option<u32>>);

pub fn start_runtime_sidecar(app: &AppHandle) {
    let bundle_ok = runtime_bundle_available(app);
    if !bundle_ok {
        boot_state::on_runtime_bundle_missing();
        let _ = app.emit("cnexus:runtime-bundle-missing", ());
        crate::boot_trace::trace("runtime bundle missing — emit cnexus:runtime-bundle-missing");
        if !cfg!(debug_assertions) {
            return;
        }
        crate::boot_trace::trace("debug build: attempting sidecar spawn (dev repo fallback)");
    }

    if crate::runtime_probe::runtime_api_healthy() {
        boot_state::on_runtime_api_attached();
        crate::boot_trace::trace("runtime API already healthy on :8000 — skip sidecar spawn");
        return;
    }

    let preflight = runtime_preflight::scan_conflicts();
    if preflight.has_conflicts() {
        crate::boot_trace::trace(&format!(
            "preflight: {} conflict(s) detected",
            preflight.conflicts.len()
        ));
        if !runtime_preflight::prompt_user_proceed(&preflight) {
            crate::boot_trace::trace("preflight: user cancelled — runtime sidecar not started");
            return;
        }
        resolve_preflight_conflicts(preflight.conflict_pids());
    }

    if runtime_sidecar_already_running(app) {
        crate::boot_trace::trace("runtime sidecar already managed — skip duplicate spawn");
        return;
    }

    spawn_runtime_sidecar(app);
}

fn runtime_sidecar_already_running(app: &AppHandle) -> bool {
    if let Some(state) = app.try_state::<RuntimeProcess>() {
        if let Ok(guard) = state.0.lock() {
            if let Some(pid) = *guard {
                if pid > 0 && sidecar_pid_alive(pid) {
                    return true;
                }
            }
        }
    }
    false
}

fn sidecar_pid_alive(pid: u32) -> bool {
    if pid == 0 {
        return false;
    }
    #[cfg(windows)]
    {
        crate::win_process::process_image_for_pid(pid).is_some()
    }
    #[cfg(not(windows))]
    {
        let _ = pid;
        true
    }
}

/// Diagnostics only — kills stale listeners/processes then spawns sidecar.
pub fn force_restart_runtime_sidecar(app: &AppHandle) {
    if !runtime_bundle_available(app) {
        crate::boot_trace::trace("runtime bundle missing — force restart skipped");
        return;
    }
    force_kill_orphan_runtime();
    clear_managed_sidecar(app);
    spawn_runtime_sidecar(app);
}

fn clear_managed_sidecar(app: &AppHandle) {
    if let Some(state) = app.try_state::<RuntimeProcess>() {
        if let Ok(mut guard) = state.0.lock() {
            guard.take();
        }
    }
}

fn resolve_sidecar_binary(_app: &AppHandle) -> Option<PathBuf> {
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            for name in [
                "cnexus-runtime-x86_64-pc-windows-msvc.exe",
                "cnexus-runtime.exe",
            ] {
                let candidate = dir.join(name);
                if candidate.is_file() {
                    return Some(candidate);
                }
            }
        }
    }

    if cfg!(debug_assertions) {
        if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
            let dev = PathBuf::from(manifest).join("cnexus-runtime-x86_64-pc-windows-msvc.exe");
            if dev.is_file() {
                return Some(dev);
            }
        }
    }
    None
}

fn spawn_runtime_sidecar(app: &AppHandle) {
    let Some(binary) = resolve_sidecar_binary(app) else {
        let err = "cnexus-runtime sidecar binary not found next to CNexus.exe";
        crate::boot_trace::trace(err);
        let _ = app.emit("cnexus:runtime-spawn-failed", err);
        return;
    };

    let mut cmd = std::process::Command::new(&binary);
    #[cfg(windows)]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    match cmd.spawn() {
        Ok(child) => {
            let pid = child.id();
            boot_state::on_runtime_spawn_started();
            crate::boot_trace::trace(&format!(
                "runtime sidecar started pid={pid} path={}",
                binary.display()
            ));
            app.manage(RuntimeProcess(Mutex::new(Some(pid))));
            std::mem::forget(child);
        }
        Err(err) => {
            crate::boot_trace::trace(&format!("runtime spawn failed: {err}"));
            let _ = app.emit("cnexus:runtime-spawn-failed", err.to_string());
        }
    }
}

fn take_runtime_pid(app: &AppHandle) -> u32 {
    if let Some(state) = app.try_state::<RuntimeProcess>() {
        if let Ok(mut guard) = state.0.lock() {
            return guard.take().unwrap_or(0);
        }
    }
    0
}

/// Instant quit path — spawn taskkill without waiting for PowerShell.
pub fn stop_runtime_sidecar_fast(app: &AppHandle) {
    let pid = take_runtime_pid(app);
    stop_runtime_processes_fast(pid);
}

/// Restart path — wait briefly for sidecar tree to exit before respawning.
pub fn stop_runtime_sidecar(app: &AppHandle) {
    let pid = take_runtime_pid(app);
    stop_runtime_processes_for_restart(pid);
    if pid == 0 {
        force_kill_orphan_runtime();
    }
}

pub fn on_run_event(app: &AppHandle, event: &RunEvent) {
    match event {
        RunEvent::Exit | RunEvent::ExitRequested { .. } => stop_runtime_sidecar_fast(app),
        _ => {}
    }
}

fn runtime_bundle_available(app: &AppHandle) -> bool {
    if runtime_bundle_present(app) {
        return true;
    }
    if cfg!(debug_assertions) {
        if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
            let dev_bundle = std::path::PathBuf::from(manifest)
                .join("runtime-bundle/app/brain-memory-ui/api/main.py");
            if dev_bundle.is_file() {
                return true;
            }
        }
    }
    false
}

fn runtime_bundle_present(app: &AppHandle) -> bool {
    app.path()
        .resource_dir()
        .ok()
        .map(|resource_dir| {
            resource_dir
                .join("runtime-bundle/app/brain-memory-ui/api/main.py")
                .is_file()
        })
        .unwrap_or(false)
}
