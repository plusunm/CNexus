#[cfg(windows)]
fn main() {
    let mut res = winres::WindowsResource::new();
    res.set_icon("../icons/icon.ico");
    if let Err(err) = res.compile() {
        eprintln!("winres: {err}");
        std::process::exit(1);
    }
    // winres 0.1 has no set_windows_subsystem — force GUI subsystem (no empty CMD window).
    println!("cargo:rustc-link-arg=/SUBSYSTEM:WINDOWS");
    println!("cargo:rustc-link-arg=/ENTRY:mainCRTStartup");
}

#[cfg(not(windows))]
fn main() {}
