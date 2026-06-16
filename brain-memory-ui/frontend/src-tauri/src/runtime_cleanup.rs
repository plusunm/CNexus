//! Force-stop Runtime sidecar + embedded Python (Windows process tree).



use std::sync::atomic::{AtomicBool, Ordering};



#[cfg(windows)]

use std::os::windows::process::CommandExt;



#[cfg(windows)]

const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[cfg(windows)]

const DETACHED_PROCESS: u32 = 0x0000_0008;



static QUIT_CLEANUP_STARTED: AtomicBool = AtomicBool::new(false);



/// Non-blocking kill for user quit — avoids slow PowerShell scans on the UI thread.

pub fn stop_runtime_processes_fast(known_pid: u32) {

    if QUIT_CLEANUP_STARTED.swap(true, Ordering::SeqCst) {

        return;

    }

    spawn_kill_process_tree(known_pid);

    #[cfg(windows)]

    {

        crate::win_process::hidden_taskkill_image("cnexus-runtime.exe");

    }

}



/// Blocking cleanup before restarting Runtime (license change, etc.).

pub fn stop_runtime_processes_for_restart(known_pid: u32) {

    QUIT_CLEANUP_STARTED.store(true, Ordering::SeqCst);

    if known_pid > 0 {

        run_taskkill(&["/F", "/T", "/PID", &known_pid.to_string()]);

    }

    #[cfg(windows)]

    {

        run_taskkill(&["/F", "/T", "/IM", "cnexus-runtime.exe"]);

    }

    std::thread::sleep(std::time::Duration::from_millis(200));

}



/// Best-effort cleanup when sidecar handle is missing (uninstall / crash / dev).

pub fn force_kill_orphan_runtime() {

    #[cfg(windows)]

    {

        crate::win_process::hidden_taskkill_image("cnexus-runtime.exe");

        crate::win_process::kill_port_listeners(8000);

    }

}



/// Stop preflight conflicts before respawning Runtime (no PowerShell / no visible CMD).

pub fn resolve_preflight_conflicts(pids: impl IntoIterator<Item = u32>) {

    #[cfg(windows)]

    {

        crate::win_process::kill_unique_pids(pids);

        std::thread::sleep(std::time::Duration::from_millis(250));

        crate::win_process::kill_port_listeners(8000);

    }

    #[cfg(not(windows))]

    {

        let _ = pids;

    }

}



#[cfg(windows)]

fn spawn_taskkill(args: &[&str]) {

    let _ = std::process::Command::new("taskkill")

        .args(args)

        .creation_flags(CREATE_NO_WINDOW | DETACHED_PROCESS)

        .spawn();

}



#[cfg(windows)]

fn run_taskkill(args: &[&str]) {

    let _ = std::process::Command::new("taskkill")

        .args(args)

        .creation_flags(CREATE_NO_WINDOW | DETACHED_PROCESS)

        .output();

}



#[cfg(not(windows))]

fn spawn_taskkill(_args: &[&str]) {}



#[cfg(not(windows))]

fn run_taskkill(_args: &[&str]) {}



#[cfg(windows)]

fn spawn_kill_process_tree(pid: u32) {

    if pid > 0 {

        spawn_taskkill(&["/F", "/T", "/PID", &pid.to_string()]);

    }

}



#[cfg(not(windows))]

fn spawn_kill_process_tree(_pid: u32) {}


