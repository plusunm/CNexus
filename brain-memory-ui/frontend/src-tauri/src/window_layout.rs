//! Fit desktop windows inside monitor work area (excludes Windows taskbar).

use tauri::{LogicalPosition, LogicalSize, PhysicalRect, Position, Size, WebviewWindow};

const WORK_MARGIN: f64 = 16.0;

fn monitor_for_window(window: &WebviewWindow) -> Option<tauri::Monitor> {
    window
        .current_monitor()
        .ok()
        .flatten()
        .or_else(|| window.primary_monitor().ok().flatten())
}

fn work_area_logical(monitor: &tauri::Monitor, scale: f64) -> (f64, f64, f64, f64) {
    let PhysicalRect { position, size } = *monitor.work_area();
    (
        position.x as f64 / scale,
        position.y as f64 / scale,
        size.width as f64 / scale,
        size.height as f64 / scale,
    )
}

/// Resize + center a window within the monitor work area (not under the taskbar).
pub fn fit_window_to_work_area(window: &WebviewWindow) -> Result<(), String> {
    let monitor = monitor_for_window(window).ok_or_else(|| "no monitor".to_string())?;
    let scale = window.scale_factor().map_err(|e| e.to_string())?;
    let (work_x, work_y, work_w, work_h) = work_area_logical(&monitor, scale);

    let inner = window.inner_size().map_err(|e| e.to_string())?;
    let mut w = inner.width as f64 / scale;
    let mut h = inner.height as f64 / scale;

    let max_w = (work_w - WORK_MARGIN * 2.0).max(320.0);
    let max_h = (work_h - WORK_MARGIN * 2.0).max(240.0);
    w = w.min(max_w);
    h = h.min(max_h);

    window
        .set_size(Size::Logical(LogicalSize::new(w, h)))
        .map_err(|e| e.to_string())?;

    let x = work_x + (work_w - w) / 2.0;
    let y = work_y + (work_h - h) / 2.0;
    window
        .set_position(Position::Logical(LogicalPosition::new(x, y)))
        .map_err(|e| e.to_string())?;

    Ok(())
}

pub fn prepare_dashboard_show(window: &WebviewWindow) -> Result<(), String> {
    let _ = window.set_always_on_top(false);
    let _ = window.set_skip_taskbar(false);
    let _ = window.unminimize();
    fit_window_to_work_area(window)
}
