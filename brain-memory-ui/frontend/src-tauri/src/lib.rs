use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, LogicalSize, Manager, Size, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

mod boot_state;
mod boot_sequence;
mod boot_trace;
mod exit_trace;
mod boot_ui;
mod ollama_probe;
mod pe_utils;
mod runtime_cleanup;
mod runtime_preflight;
mod runtime_probe;
mod runtime_sidecar;
mod security_bootstrap;
mod smoke_report;
mod webview_shell;
mod window_layout;
mod win_process;

const FLOAT_LABEL: &str = "float";
const DASHBOARD_LABEL: &str = "dashboard";

fn emit_boot_session(app: &tauri::AppHandle) {
    let id = format!(
        "boot_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis())
            .unwrap_or(0)
    );
    let path = cnexus_data_dir().join("data").join("boot-session.txt");
    let _ = std::fs::write(&path, &id);
    let _ = app.emit("cnexus:boot-session", id);
}

/// Keep in sync with frontend `lib/floatWindowSpec.ts` FLOAT_LAYOUT.
fn float_size(stage: &str) -> (f64, f64) {
    match stage {
        "dock" => (56.0, 56.0),
        "bar" => (360.0, 228.0),
        "expanded" => (440.0, 640.0),
        other => {
            boot_trace::trace(&format!("float_size: unknown stage '{other}', defaulting to bar"));
            (360.0, 228.0)
        }
    }
}

#[tauri::command]
async fn sync_float_window(
    app: tauri::AppHandle,
    stage: String,
    pinned: bool,
) -> Result<(), String> {
    let window = app
        .get_webview_window(FLOAT_LABEL)
        .ok_or_else(|| "float window missing".to_string())?;
    let (w, h) = float_size(&stage);
    window
        .set_size(Size::Logical(LogicalSize::new(w, h)))
        .map_err(|e| e.to_string())?;
    window
        .set_always_on_top(pinned)
        .map_err(|e| e.to_string())?;
    window
        .set_skip_taskbar(true)
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn toggle_float_visibility(app: tauri::AppHandle) -> Result<bool, String> {
    let window = app
        .get_webview_window(FLOAT_LABEL)
        .ok_or_else(|| "float window missing".to_string())?;
    let visible = window.is_visible().map_err(|e| e.to_string())?;
    if visible {
        window.hide().map_err(|e| e.to_string())?;
        Ok(false)
    } else {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        Ok(true)
    }
}

#[tauri::command]
async fn hide_float_window(app: tauri::AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window(FLOAT_LABEL)
        .ok_or_else(|| "float window missing".to_string())?;
    window.hide().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn open_dashboard(app: tauri::AppHandle, route: Option<String>) -> Result<(), String> {
    let path = route.unwrap_or_else(|| "/shell?layout=overview".to_string());
    if !path.starts_with('/') || path.contains("..") {
        return Err("invalid dashboard route".to_string());
    }

    let window = if let Some(existing) = app.get_webview_window(DASHBOARD_LABEL) {
        existing
    } else {
        WebviewWindowBuilder::new(
            &app,
            DASHBOARD_LABEL,
            WebviewUrl::App(path.clone().into()),
        )
            .title("CNexus — Mind")
            .inner_size(1280.0, 840.0)
            .min_inner_size(960.0, 640.0)
            .prevent_overflow_with_margin(LogicalSize::new(16.0, 16.0))
            .center()
            .build()
            .map_err(|e| e.to_string())?
    };
    webview_shell::harden_webview_shell(&window)?;
    window_layout::prepare_dashboard_show(&window)?;
    if let Some(float_win) = app.get_webview_window(FLOAT_LABEL) {
        let _ = float_win.set_always_on_top(false);
    }
    let _ = window.emit("cnexus:navigate-shell", path);
    let _ = app.emit("cnexus:dashboard-opened", ());
    window.show().map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn emit_open_settings(app: tauri::AppHandle) -> Result<(), String> {
    app.emit("open-settings", ()).map_err(|e| e.to_string())
}

#[tauri::command]
async fn save_enterprise_license(app: tauri::AppHandle, license: String) -> Result<(), String> {
    let dir = cnexus_data_dir();
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    std::fs::write(dir.join("license.cnx"), license.trim()).map_err(|e| e.to_string())?;

    runtime_sidecar::stop_runtime_sidecar(&app);
    runtime_sidecar::force_restart_runtime_sidecar(&app);
    Ok(())
}

#[tauri::command]
fn check_runtime_environment() -> runtime_preflight::PreflightReport {
    runtime_preflight::scan_conflicts()
}

#[tauri::command]
fn restart_runtime_sidecar(app: tauri::AppHandle) -> Result<(), String> {
    runtime_sidecar::stop_runtime_sidecar(&app);
    runtime_sidecar::force_restart_runtime_sidecar(&app);
    Ok(())
}

fn cnexus_data_dir() -> std::path::PathBuf {
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        return std::path::PathBuf::from(local).join("CNexus");
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        return std::path::PathBuf::from(home).join(".cnexus");
    }
    std::path::PathBuf::from(".cnexus")
}

#[tauri::command]
async fn show_float_window(app: tauri::AppHandle) -> Result<(), String> {
    boot_sequence::show_float_window(app).await
}

#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    exit_trace::note_exit_intent("quit_app_command", None);
    runtime_sidecar::stop_runtime_sidecar_fast(&app);
    app.exit(0);
}

fn emit_float_toggle(app: &tauri::AppHandle) {
    let _ = app.emit("float-toggle", ());
}

fn build_tray(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let show_i = MenuItem::with_id(app, "show", "显示悬浮条", true, None::<&str>)?;
    let hide_i = MenuItem::with_id(app, "hide", "隐藏悬浮条", true, None::<&str>)?;
    let dashboard_i = MenuItem::with_id(app, "dashboard", "打开大屏窗口", true, None::<&str>)?;
    let autostart_i = MenuItem::with_id(app, "autostart", "切换开机自启", true, None::<&str>)?;
    let settings_i = MenuItem::with_id(app, "settings", "连接服务", true, None::<&str>)?;
    let quit_i = MenuItem::with_id(app, "quit", "退出 CNexus", true, None::<&str>)?;
    let menu = Menu::with_items(
        app,
        &[
            &show_i,
            &hide_i,
            &PredefinedMenuItem::separator(app)?,
            &dashboard_i,
            &autostart_i,
            &settings_i,
            &PredefinedMenuItem::separator(app)?,
            &quit_i,
        ],
    )?;

    let mut builder = TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("CNexus")
        .show_menu_on_left_click(false);
    if let Some(icon) = app.default_window_icon() {
        builder = builder.icon(icon.clone());
    }
    builder = builder
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                boot_sequence::force_show_float_from_tray(tray.app_handle());
            }
        })
        .on_menu_event(|app, event| match event.id.as_ref() {
        "show" => {
            boot_sequence::force_show_float_from_tray(app);
        }
        "hide" => {
            if let Some(w) = app.get_webview_window(FLOAT_LABEL) {
                let _ = w.hide();
            }
        }
        "dashboard" => {
            let handle = app.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(err) = open_dashboard(handle, None).await {
                    boot_trace::trace(&format!("tray open_dashboard failed: {err}"));
                }
            });
        }
        "autostart" => {
            use tauri_plugin_autostart::ManagerExt;
            let autostart = app.autolaunch();
            if autostart.is_enabled().unwrap_or(false) {
                let _ = autostart.disable();
            } else {
                let _ = autostart.enable();
            }
        }
        "settings" => {
            let _ = app.emit("open-settings", ());
        }
        "quit" => {
            exit_trace::note_exit_intent("tray_menu_quit", None);
            runtime_sidecar::stop_runtime_sidecar_fast(app);
            app.exit(0);
        }
        _ => {}
    });
    builder.build(app)?;

    Ok(())
}

fn register_shortcuts(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let shortcut = Shortcut::new(Some(Modifiers::ALT | Modifiers::SHIFT), Code::KeyM);
    let handle = app.clone();
    app.global_shortcut().on_shortcut(shortcut, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            emit_float_toggle(&handle);
        }
    })?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    boot_trace::reset_trace();
    boot_trace::trace(&format!("run() pid={}", std::process::id()));
    std::panic::set_hook(Box::new(|info| {
        boot_trace::trace(&format!("PANIC: {info}"));
    }));
    boot_trace::trace("builder: creating");
    let result = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            boot_trace::trace("single-instance: secondary launch forwarded");
            boot_sequence::nudge_float_on_secondary_launch(app);
        }))
        .plugin({
            boot_trace::trace("builder: shell plugin");
            tauri_plugin_shell::init()
        })
        .plugin({
            boot_trace::trace("builder: shortcut plugin");
            tauri_plugin_global_shortcut::Builder::new().build()
        })
        .plugin({
            boot_trace::trace("builder: autostart plugin");
            tauri_plugin_autostart::init(
                tauri_plugin_autostart::MacosLauncher::LaunchAgent,
                Some(vec![]),
            )
        })
        .invoke_handler(tauri::generate_handler![
            sync_float_window,
            toggle_float_visibility,
            hide_float_window,
            open_dashboard,
            emit_open_settings,
            save_enterprise_license,
            restart_runtime_sidecar,
            check_runtime_environment,
            show_float_window,
            security_bootstrap::security_bootstrap_scan_app_dir,
            security_bootstrap::security_bootstrap_preflight,
            security_bootstrap::security_bootstrap_license_status,
            security_bootstrap::security_bootstrap_heartbeat,
            boot_sequence::reveal_float_window_command,
            boot_sequence::grant_ui_render_command,
            boot_sequence::boot_fallback_demo_command,
            boot_sequence::get_boot_state_command,
            boot_sequence::runtime_boot_timed_out_command,
            boot_sequence::get_runtime_boot_failure_command,
            boot_ui::report_ui_heartbeat_command,
            ollama_probe::probe_ollama_local,
            quit_app
        ])
        .setup(|app| {
            boot_ui::mark_app_start();
            boot_trace::trace("setup: begin");
            let bootstrap = security_bootstrap::run_security_bootstrap_preflight(false);
            boot_trace::trace(&format!(
                "security bootstrap: ok={} code={} edition={}",
                bootstrap.ok, bootstrap.internal_code, bootstrap.edition
            ));
            if !bootstrap.ok {
                let _ = app.emit("cnexus:security-bootstrap-failed", &bootstrap);
            } else {
                let _ = app.emit("cnexus:security-bootstrap-ok", &bootstrap);
            }
            // Start Runtime before UI/tray so API comes up in parallel with boot shell.
            if bootstrap.ok || bootstrap.edition == "personal" {
                runtime_sidecar::start_runtime_sidecar(app.handle());
            } else {
                boot_trace::trace("security bootstrap blocked runtime sidecar spawn");
            }
            boot_trace::trace("setup: sidecar spawn requested");
            boot_sequence::start_runtime_ready_watch(app.handle().clone());
            smoke_report::reset_report_file();
            let data = cnexus_data_dir().join("data");
            for sub in ["blocks", "lancedb", "kuzu_db"] {
                let _ = std::fs::create_dir_all(data.join(sub));
            }
            boot_sequence::prepare_float_window(app.handle()).map_err(|e| {
                boot_trace::trace(&format!("setup: prepare_float_window FAILED: {e}"));
                e
            })?;
            boot_trace::trace("setup: float window prepared");
            if let Err(err) = build_tray(app.handle()) {
                boot_trace::trace(&format!("setup: build_tray WARN: {err}"));
            } else {
                boot_trace::trace("setup: tray ok");
            }
            if let Err(err) = register_shortcuts(app.handle()) {
                boot_trace::trace(&format!("setup: shortcuts WARN: {err}"));
            } else {
                boot_trace::trace("setup: shortcuts ok");
            }
            boot_sequence::schedule_absolute_float_safety_net(app.handle().clone());
            boot_trace::trace("setup: complete");
            emit_boot_session(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!());
    boot_trace::trace("builder: build returned");
    result
        .map_err(|e| {
            boot_trace::trace(&format!("build FAILED: {e}"));
            e
        })
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if matches!(event, tauri::RunEvent::Ready) {
                boot_trace::trace("run event: Ready");
                emit_boot_session(app_handle);
            }
            exit_trace::on_run_event(&event);
            runtime_sidecar::on_run_event(app_handle, &event);
        });
}
