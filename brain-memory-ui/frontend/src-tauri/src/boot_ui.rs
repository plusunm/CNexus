//! UI heartbeat protocol — dual bookkeeping (Invariant B) + smoke TTFV.

use std::sync::{Mutex, OnceLock};
use std::time::Instant;

use serde::Deserialize;

use crate::boot_state::BootState;
use crate::smoke_report;

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UiHeartbeatPayload {
    pub phase: String,
    pub rust_boot_state: u8,
    pub mounted: bool,
    pub ts: u64,
    pub detail: Option<String>,
}

#[derive(Clone)]
struct UiHeartbeatSnapshot {
    boot_shell_mounted: bool,
    ttfv_ms: Option<u64>,
    ui_phase: String,
    ui_rust_state: u8,
    last_ts: u64,
}

static APP_START: OnceLock<Instant> = OnceLock::new();
static UI_SNAPSHOT: Mutex<Option<UiHeartbeatSnapshot>> = Mutex::new(None);

pub fn mark_app_start() {
    let _ = APP_START.set(Instant::now());
}

#[tauri::command]
pub fn report_ui_heartbeat_command(payload: UiHeartbeatPayload) -> Result<(), String> {
    crate::boot_trace::trace(&format!(
        "ui heartbeat phase={} rust_state={} mounted={}",
        payload.phase, payload.rust_boot_state, payload.mounted
    ));

    let mut guard = UI_SNAPSHOT
        .lock()
        .map_err(|e| format!("ui snapshot lock: {e}"))?;

    let entry = guard.get_or_insert_with(|| UiHeartbeatSnapshot {
        boot_shell_mounted: false,
        ttfv_ms: None,
        ui_phase: payload.phase.clone(),
        ui_rust_state: payload.rust_boot_state,
        last_ts: payload.ts,
    });

    if payload.mounted && !entry.boot_shell_mounted {
        entry.boot_shell_mounted = true;
        let ms = APP_START
            .get()
            .map(|t| t.elapsed().as_millis() as u64)
            .unwrap_or(0);
        entry.ttfv_ms = Some(ms);
        crate::boot_trace::trace(&format!("BootShell TTFV {ms}ms"));
    }

    entry.ui_phase = payload.phase.clone();
    entry.ui_rust_state = payload.rust_boot_state;
    entry.last_ts = payload.ts;

    smoke_report::on_ui_heartbeat();
    Ok(())
}

pub fn ui_snapshot_for_report() -> (bool, Option<u64>, String, u8) {
    UI_SNAPSHOT
        .lock()
        .ok()
        .and_then(|g| g.clone())
        .map(|s| (s.boot_shell_mounted, s.ttfv_ms, s.ui_phase, s.ui_rust_state))
        .unwrap_or((false, None, String::new(), 0))
}

pub fn ui_ack_matches_rust_float() -> bool {
    let (mounted, _, _, ui_state) = ui_snapshot_for_report();
    mounted && ui_state >= BootState::FloatWindowShown as u8
}
