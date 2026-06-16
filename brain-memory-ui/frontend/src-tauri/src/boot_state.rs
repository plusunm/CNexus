//! CNexus desktop boot state machine (BootStateLock).

use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
use std::sync::Mutex;

static DEMO_RENDER: AtomicBool = AtomicBool::new(false);
static RUNTIME_BOOT_TIMED_OUT: AtomicBool = AtomicBool::new(false);
static RUNTIME_BUNDLE_MISSING: AtomicBool = AtomicBool::new(false);
static RUNTIME_INIT_FAILED: AtomicBool = AtomicBool::new(false);
static RUNTIME_INIT_ERROR: Mutex<Option<String>> = Mutex::new(None);

#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum BootState {
    Init = 0,
    RuntimeSpawning = 1,
    RuntimeReady = 2,
    UiRenderAllowed = 3,
    FloatWindowShown = 4,
}

static BOOT_STATE: AtomicU8 = AtomicU8::new(BootState::Init as u8);

pub fn get_boot_state() -> BootState {
    match BOOT_STATE.load(Ordering::SeqCst) {
        1 => BootState::RuntimeSpawning,
        2 => BootState::RuntimeReady,
        3 => BootState::UiRenderAllowed,
        4 => BootState::FloatWindowShown,
        _ => BootState::Init,
    }
}

fn set_boot_state(state: BootState) {
    BOOT_STATE.store(state as u8, Ordering::SeqCst);
    crate::boot_trace::trace(&format!("boot state -> {state:?}"));
    #[cfg(debug_assertions)]
    eprintln!("[cnexus] boot state → {state:?}");
    crate::smoke_report::on_boot_state_change(state);
}

pub fn reset_boot_state() {
    DEMO_RENDER.store(false, Ordering::SeqCst);
    RUNTIME_BOOT_TIMED_OUT.store(false, Ordering::SeqCst);
    RUNTIME_BUNDLE_MISSING.store(false, Ordering::SeqCst);
    RUNTIME_INIT_FAILED.store(false, Ordering::SeqCst);
    if let Ok(mut guard) = RUNTIME_INIT_ERROR.lock() {
        *guard = None;
    }
    set_boot_state(BootState::Init);
}

pub fn on_runtime_bundle_missing() {
    RUNTIME_BUNDLE_MISSING.store(true, Ordering::SeqCst);
}

pub fn runtime_bundle_missing() -> bool {
    RUNTIME_BUNDLE_MISSING.load(Ordering::SeqCst)
}

pub fn on_runtime_init_failed(message: String) {
    RUNTIME_INIT_FAILED.store(true, Ordering::SeqCst);
    if let Ok(mut guard) = RUNTIME_INIT_ERROR.lock() {
        *guard = Some(message);
    }
}

pub fn runtime_init_failed_message() -> Option<String> {
    if !RUNTIME_INIT_FAILED.load(Ordering::SeqCst) {
        return None;
    }
    RUNTIME_INIT_ERROR.lock().ok().and_then(|g| g.clone())
}

pub fn on_runtime_boot_timeout() {
    RUNTIME_BOOT_TIMED_OUT.store(true, Ordering::SeqCst);
}

pub fn runtime_boot_timed_out() -> bool {
    RUNTIME_BOOT_TIMED_OUT.load(Ordering::SeqCst)
}

pub fn is_demo_render_path() -> bool {
    DEMO_RENDER.load(Ordering::SeqCst)
}

pub fn on_runtime_spawn_started() {
    if get_boot_state() == BootState::Init {
        set_boot_state(BootState::RuntimeSpawning);
    }
}

/// Reuse an already-running Runtime API (skip sidecar spawn).
pub fn on_runtime_api_attached() {
    if get_boot_state() == BootState::Init {
        set_boot_state(BootState::RuntimeSpawning);
    }
}

pub fn on_runtime_system_ready() {
    if get_boot_state() < BootState::RuntimeReady {
        set_boot_state(BootState::RuntimeReady);
    }
}

pub fn grant_ui_render() -> Result<BootState, String> {
    let current = get_boot_state();
    if current < BootState::RuntimeReady {
        return Err(format!(
            "boot state lock: need RuntimeReady (now {current:?})"
        ));
    }
    if current < BootState::UiRenderAllowed {
        set_boot_state(BootState::UiRenderAllowed);
    }
    Ok(get_boot_state())
}

pub fn grant_ui_render_demo_fallback() -> BootState {
    DEMO_RENDER.store(true, Ordering::SeqCst);
    set_boot_state(BootState::UiRenderAllowed);
    get_boot_state()
}

pub fn on_float_window_shown() {
    set_boot_state(BootState::FloatWindowShown);
}

pub fn boot_state_at_least(min: BootState) -> bool {
    get_boot_state() >= min
}
