// Release builds must not allocate a console window on Windows (avoids black CMD on startup).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    cnexus_product_lib::run()
}
