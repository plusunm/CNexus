//! Exit reason tracing — correlates programmatic vs user-initiated shutdown in boot-trace.log.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

static PENDING_REASON: Mutex<Option<String>> = Mutex::new(None);
static EXIT_REQUESTED_LOGGED: AtomicBool = AtomicBool::new(false);

/// Record an intentional exit before `AppHandle::exit` (or window close).
pub fn note_exit_intent(reason: &str, detail: Option<&str>) {
    let msg = match detail {
        Some(d) if !d.is_empty() => format!("{reason}:{d}"),
        _ => reason.to_string(),
    };
    if let Ok(mut guard) = PENDING_REASON.lock() {
        *guard = Some(msg.clone());
    }
    crate::boot_trace::trace(&format!("exit intent: {msg}"));
}

pub fn log_exit_requested(code: Option<i32>) {
    if EXIT_REQUESTED_LOGGED.swap(true, Ordering::SeqCst) {
        return;
    }
    let pending = PENDING_REASON
        .lock()
        .ok()
        .and_then(|g| g.clone());
    let origin = match (code, pending.as_deref()) {
        (None, Some(r)) => format!("user_or_framework code=None pending={r}"),
        (None, None) => {
            "user_or_framework code=None (window close / OS / external kill)".to_string()
        }
        (Some(c), Some(r)) => format!("programmatic code={c} intent={r}"),
        (Some(c), None) => format!("programmatic code={c} intent=unknown"),
    };
    crate::boot_trace::trace(&format!("run event: ExitRequested — {origin}"));
}

pub fn log_exit_complete() {
    let pending = PENDING_REASON.lock().ok().and_then(|mut g| g.take());
    match pending {
        Some(r) => crate::boot_trace::trace(&format!("run event: Exit — reason={r}")),
        None => crate::boot_trace::trace("run event: Exit"),
    }
}

pub fn on_run_event(event: &tauri::RunEvent) {
    match event {
        tauri::RunEvent::ExitRequested { code, .. } => log_exit_requested(*code),
        tauri::RunEvent::Exit => log_exit_complete(),
        tauri::RunEvent::WindowEvent { label, event, .. } => {
            if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                note_exit_intent("window_close_requested", Some(label));
            }
            if matches!(event, tauri::WindowEvent::Destroyed) {
                crate::boot_trace::trace(&format!("window destroyed: {label}"));
            }
        }
        _ => {}
    }
}
