//! WebView shell hardening — block Windows native share/context menus in float UI.

use tauri::WebviewWindow;

pub fn harden_webview_shell(window: &WebviewWindow) -> Result<(), String> {
    let _ = window.set_ignore_cursor_events(false);
    disable_default_context_menus(window)?;
    let _ = window.eval(
        "window.addEventListener('contextmenu',function(e){if(!e.target?.closest?.('[data-allow-native-menu]'))e.preventDefault();},true);",
    );
    Ok(())
}

#[cfg(windows)]
fn disable_default_context_menus(window: &WebviewWindow) -> Result<(), String> {
    window
        .with_webview(|platform| {
            let controller = platform.controller();
            unsafe {
                if let Ok(core) = controller.CoreWebView2() {
                    if let Ok(settings) = core.Settings() {
                        let _ = settings.SetAreDefaultContextMenusEnabled(false);
                    }
                }
            }
        })
        .map_err(|e| e.to_string())
}

#[cfg(not(windows))]
fn disable_default_context_menus(_window: &WebviewWindow) -> Result<(), String> {
    Ok(())
}
