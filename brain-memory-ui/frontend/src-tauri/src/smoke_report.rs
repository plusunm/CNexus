use std::fs;

use std::path::PathBuf;

use std::thread;

use std::time::Duration;



use tauri::{AppHandle, Manager};



use crate::boot_state::{self, BootState};

use crate::boot_ui;

use crate::runtime_sidecar;



fn smoke_enabled() -> bool {

    std::env::var("CNEXUS_UI_SMOKE")

        .ok()

        .as_deref()

        == Some("1")

}



fn report_path() -> PathBuf {

    cnexus_data_dir().join("data").join("ui-smoke-report.json")

}



fn cnexus_data_dir() -> PathBuf {

    if let Ok(local) = std::env::var("LOCALAPPDATA") {

        return PathBuf::from(local).join("CNexus");

    }

    if let Ok(home) = std::env::var("USERPROFILE") {

        return PathBuf::from(home).join(".cnexus");

    }

    PathBuf::from(".cnexus")

}



fn boot_state_name(state: BootState) -> &'static str {

    match state {

        BootState::Init => "Init",

        BootState::RuntimeSpawning => "RuntimeSpawning",

        BootState::RuntimeReady => "RuntimeReady",

        BootState::UiRenderAllowed => "UiRenderAllowed",

        BootState::FloatWindowShown => "FloatWindowShown",

    }

}



pub fn on_ui_heartbeat() {

    if !smoke_enabled() {

        return;

    }

    let _ = write_report(None, false);

}



pub fn on_boot_state_change(state: BootState) {

    if !smoke_enabled() {

        return;

    }

    let _ = write_report(None, false);

    let _ = state;

}



pub fn on_float_shown(app: &AppHandle) {

    if !smoke_enabled() {

        return;

    }

    let visible = app

        .get_webview_window("float")

        .and_then(|w| w.is_visible().ok())

        .unwrap_or(false);

    let _ = write_report(Some(app), visible);

    schedule_smoke_exit(app.clone());

}



fn write_report(_app: Option<&AppHandle>, float_visible: bool) -> Result<(), String> {

    if !smoke_enabled() {

        return Ok(());

    }

    let state = boot_state::get_boot_state();

    let (boot_shell_mounted, ttfv_ms, ui_phase, ui_rust_state) =

        boot_ui::ui_snapshot_for_report();

    let ui_ack = boot_ui::ui_ack_matches_rust_float();

    let dir = cnexus_data_dir().join("data");

    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;

    let ttfv_json = match ttfv_ms {

        Some(ms) => ms.to_string(),

        None => "null".to_string(),

    };

    let body = format!(

        r#"{{"boot_state":{},"boot_state_name":"{}","float_visible":{},"runtime_ready":{},"boot_shell_mounted":{},"ttfv_ms":{},"ui_phase":"{}","ui_rust_state":{},"ui_ack_float":{},"updated_at":"{}","pid":{}}}"#,

        state as u8,

        boot_state_name(state),

        float_visible,

        state >= BootState::RuntimeReady,

        boot_shell_mounted,

        ttfv_json,

        ui_phase.replace('"', "\\\""),

        ui_rust_state,

        ui_ack,

        chrono_lite_iso(),

        std::process::id()

    );

    fs::write(report_path(), body).map_err(|e| e.to_string())

}



fn smoke_auto_exit_enabled() -> bool {

    smoke_enabled()

        && std::env::var("CNEXUS_UI_SMOKE_AUTO_EXIT")

            .ok()

            .as_deref()

            != Some("0")

}



fn schedule_smoke_exit(app: AppHandle) {

    if !smoke_auto_exit_enabled() {

        return;

    }

    thread::spawn(move || {

        thread::sleep(Duration::from_millis(1200));

        crate::exit_trace::note_exit_intent("smoke_auto_exit", None);
        runtime_sidecar::stop_runtime_sidecar_fast(&app);

        app.exit(0);

    });

}



fn chrono_lite_iso() -> String {

    use std::time::{SystemTime, UNIX_EPOCH};

    let secs = SystemTime::now()

        .duration_since(UNIX_EPOCH)

        .map(|d| d.as_secs())

        .unwrap_or(0);

    format!("{secs}")

}



pub fn reset_report_file() {

    if !smoke_enabled() {

        return;

    }

    let _ = fs::remove_file(report_path());

}


