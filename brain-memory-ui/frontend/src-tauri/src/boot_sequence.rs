//! CNexus desktop boot: poll `/v1/system/ready` before UI render.

use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter, LogicalSize, Manager, Size};

use crate::boot_state::{self, BootState};
use crate::runtime_probe::{self, RuntimeProbeState};

const FLOAT_LABEL: &str = "float";
const DASHBOARD_LABEL: &str = "dashboard";
const BOOT_TIMEOUT: Duration = Duration::from_secs(120);
const RUNTIME_WATCH_EXTRA: Duration = Duration::from_secs(180);
const POLL_INTERVAL: Duration = Duration::from_millis(200);
const POLL_INTERVAL_SLOW: Duration = Duration::from_millis(400);
const SHOW_DELAY: Duration = Duration::from_millis(120);
const SHOW_READY_WAIT: Duration = Duration::from_secs(2);
const JS_SHOW_GRACE: Duration = Duration::from_secs(2);
const STARTUP_FLOAT_DELAY: Duration = Duration::from_secs(2);

pub fn prepare_float_window(app: &AppHandle) -> Result<(), String> {
    boot_state::reset_boot_state();
    let window = app
        .get_webview_window(FLOAT_LABEL)
        .ok_or_else(|| "float window missing".to_string())?;
    window.hide().map_err(|e| e.to_string())?;
    window
        .set_size(Size::Logical(LogicalSize::new(360.0, 228.0)))
        .map_err(|e| e.to_string())?;
    window
        .set_always_on_top(true)
        .map_err(|e| e.to_string())?;
    window
        .set_skip_taskbar(true)
        .map_err(|e| e.to_string())?;
    crate::webview_shell::harden_webview_shell(&window)?;
    Ok(())
}

pub fn prepare_dashboard_window(app: &AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window(DASHBOARD_LABEL) {
        window.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

pub fn start_runtime_ready_watch(app: AppHandle) {
    thread::spawn(move || {
        let start = Instant::now();
        let mut timed_out = false;
        let watch_limit = BOOT_TIMEOUT + RUNTIME_WATCH_EXTRA;

        loop {
            if start.elapsed() >= watch_limit {
                crate::boot_trace::trace("runtime watch ended without ready");
                return;
            }

            if handle_runtime_probe(&app, start, timed_out) {
                return;
            }

            if !timed_out && start.elapsed() >= BOOT_TIMEOUT {
                timed_out = true;
                crate::boot_trace::trace("runtime boot timeout — demo fallback path");
                boot_state::on_runtime_boot_timeout();
                let _ = app.emit("cnexus:runtime-boot-timeout", ());
                schedule_rust_float_fallback(app.clone(), true);
            }

            let interval = if runtime_probe::runtime_api_healthy() {
                POLL_INTERVAL
            } else {
                POLL_INTERVAL_SLOW
            };
            thread::sleep(interval);
        }
    });
}

fn handle_runtime_probe(app: &AppHandle, start: Instant, timed_out: bool) -> bool {
    match runtime_probe::probe_runtime_state() {
        RuntimeProbeState::Ready => {
            boot_state::on_runtime_system_ready();
            crate::boot_trace::trace("runtime system ready");
            let _ = app.emit("cnexus:runtime-ready", ());
            if !timed_out {
                schedule_rust_float_fallback(app.clone(), false);
            }
            true
        }
        RuntimeProbeState::InitFailed(msg) => {
            boot_state::on_runtime_init_failed(msg.clone());
            crate::boot_trace::trace(&format!("runtime init failed: {msg}"));
            let _ = app.emit("cnexus:runtime-init-failed", msg);
            boot_state::on_runtime_boot_timeout();
            let _ = app.emit("cnexus:runtime-boot-timeout", ());
            schedule_rust_float_fallback(app.clone(), true);
            true
        }
        RuntimeProbeState::PortClosed => {
            if boot_state::runtime_bundle_missing()
                && start.elapsed() >= Duration::from_secs(20)
            {
                crate::boot_trace::trace(
                    "runtime bundle missing and port still closed after 20s",
                );
                boot_state::on_runtime_boot_timeout();
                let _ = app.emit("cnexus:runtime-boot-timeout", ());
                schedule_rust_float_fallback(app.clone(), true);
                true
            } else {
                false
            }
        }
        RuntimeProbeState::Warming => false,
    }
}

/// If the WebView boot gate does not show the float in time, show from Rust.
pub fn schedule_rust_float_fallback(app: AppHandle, demo: bool) {
    thread::spawn(move || {
        thread::sleep(JS_SHOW_GRACE);
        if boot_state::get_boot_state() >= BootState::FloatWindowShown {
            return;
        }
        crate::boot_trace::trace(&format!("rust float fallback (demo={demo})"));
        if demo {
            boot_state::grant_ui_render_demo_fallback();
        } else if boot_state::grant_ui_render().is_err() {
            boot_state::grant_ui_render_demo_fallback();
        }
        let handle = app.clone();
        tauri::async_runtime::spawn(async move {
            if let Err(err) = show_float_window(handle.clone()).await {
                crate::boot_trace::trace(&format!("rust float fallback failed: {err}"));
                reveal_float_window(&handle);
            }
        });
    });
}

/// Show float from tray / secondary launch — bypass JS boot gate and runtime ready wait.
pub fn force_show_float_from_tray(app: &AppHandle) {
    reveal_float_window(app);
}

pub fn nudge_float_on_secondary_launch(app: &AppHandle) {
    reveal_float_window(app);
}

/// User-initiated show (tray menu, tray click, shortcut) — wait briefly if Runtime is spawning.
pub fn reveal_float_window(app: &AppHandle) {
    crate::boot_trace::trace("reveal_float_window");
    if boot_state::get_boot_state() < BootState::UiRenderAllowed {
        if boot_state::get_boot_state() >= BootState::RuntimeSpawning && !runtime_system_ready() {
            let start = Instant::now();
            while start.elapsed() < Duration::from_secs(90) {
                if runtime_system_ready() {
                    boot_state::on_runtime_system_ready();
                    let _ = boot_state::grant_ui_render();
                    break;
                }
                thread::sleep(Duration::from_millis(200));
            }
        }
        ensure_ui_render_allowed();
    }
    let Some(window) = app.get_webview_window(FLOAT_LABEL) else {
        crate::boot_trace::trace("reveal_float_window: float window missing");
        return;
    };
    // Size restored by frontend sync_float_window after cnexus:float-revealed.
    if let Err(err) = window.show() {
        crate::boot_trace::trace(&format!("reveal_float_window show failed: {err}"));
        return;
    }
    let _ = crate::webview_shell::harden_webview_shell(&window);
    if let Err(err) = window.set_focus() {
        crate::boot_trace::trace(&format!("reveal_float_window focus failed: {err}"));
    }
    boot_state::on_float_window_shown();
    let _ = app.emit("cnexus:float-revealed", ());
    crate::smoke_report::on_float_shown(app);
}

fn ensure_ui_render_allowed() {
    if boot_state::get_boot_state() >= BootState::UiRenderAllowed {
        return;
    }
    if runtime_system_ready() {
        let _ = boot_state::grant_ui_render();
    } else if boot_state::get_boot_state() >= BootState::RuntimeSpawning {
        // Wait for sidecar — do not fall back to demo while Runtime is still booting.
        return;
    } else {
        boot_state::grant_ui_render_demo_fallback();
    }
}

fn force_show_float(app: &AppHandle) {
    reveal_float_window(app);
}

/// Primary instance: show something quickly so the user is not staring at a blank desktop.
pub fn schedule_startup_float(app: AppHandle) {
    thread::spawn(move || {
        thread::sleep(STARTUP_FLOAT_DELAY);
        if boot_state::get_boot_state() >= BootState::FloatWindowShown {
            return;
        }
        crate::boot_trace::trace("startup float safety (2s)");
        force_show_float(&app);
    });
}

/// Last-resort demo float if JS + runtime-ready fallback both miss.
pub fn schedule_absolute_float_safety_net(app: AppHandle) {
    thread::spawn(move || {
        thread::sleep(BOOT_TIMEOUT + JS_SHOW_GRACE + Duration::from_secs(5));
        if boot_state::get_boot_state() >= BootState::FloatWindowShown {
            return;
        }
        crate::boot_trace::trace("absolute float safety net");
        schedule_rust_float_fallback(app, true);
    });
}

#[tauri::command]
pub fn reveal_float_window_command(app: AppHandle) -> Result<(), String> {
    reveal_float_window(&app);
    Ok(())
}

#[tauri::command]
pub fn grant_ui_render_command() -> Result<u8, String> {
    boot_state::grant_ui_render().map(|s| s as u8)
}

#[tauri::command]
pub fn boot_fallback_demo_command() -> Result<u8, String> {
    Ok(boot_state::grant_ui_render_demo_fallback() as u8)
}

#[tauri::command]
pub fn get_boot_state_command() -> u8 {
    boot_state::get_boot_state() as u8
}

#[tauri::command]
pub fn runtime_boot_timed_out_command() -> bool {
    boot_state::runtime_boot_timed_out()
}

#[tauri::command]
pub fn get_runtime_boot_failure_command() -> Option<String> {
    if boot_state::runtime_bundle_missing() {
        return Some("bundle_missing".into());
    }
    boot_state::runtime_init_failed_message()
}

/// Boot state lock: only STATE ≥ UiRenderAllowed may show float; re-verify system/ready.
pub async fn show_float_window(app: AppHandle) -> Result<(), String> {
    if !boot_state::boot_state_at_least(BootState::UiRenderAllowed) {
        return Err(format!(
            "boot state lock: UI render not allowed (state={:?})",
            boot_state::get_boot_state()
        ));
    }
    if !boot_state::is_demo_render_path()
        && !wait_for_system_ready(SHOW_READY_WAIT)
    {
        return Err("boot state lock: GET /v1/system/ready failed before show".into());
    }
    thread::sleep(SHOW_DELAY);
    let window = app
        .get_webview_window(FLOAT_LABEL)
        .ok_or_else(|| "float window missing".to_string())?;
    window.show().map_err(|e| e.to_string())?;
    crate::webview_shell::harden_webview_shell(&window)?;
    window.set_focus().map_err(|e| e.to_string())?;
    boot_state::on_float_window_shown();
    crate::smoke_report::on_float_shown(&app);
    Ok(())
}

fn wait_for_system_ready(max: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < max {
        if runtime_system_ready() {
            return true;
        }
        thread::sleep(Duration::from_millis(100));
    }
    false
}

pub fn runtime_system_ready() -> bool {
    runtime_probe::runtime_system_ready()
}

#[cfg(test)]
mod tests {
    use super::SHOW_DELAY;
    use std::time::Duration;

    #[test]
    fn show_delay_meets_gate_minimum() {
        assert!(SHOW_DELAY >= Duration::from_millis(100));
    }
}
