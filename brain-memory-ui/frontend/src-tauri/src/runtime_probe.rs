//! Fast TCP probes for CNexus Runtime API — no PowerShell subprocess.

use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Duration;

pub const RUNTIME_PORT: u16 = 8000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuntimeProbeState {
    PortClosed,
    Warming,
    Ready,
    InitFailed(String),
}

/// True when :8000 serves a healthy CNexus API (ok / warming / ready).
pub fn runtime_api_healthy() -> bool {
    for path in ["/health", "/v1/health"] {
        if let Some(body) = http_get_body(RUNTIME_PORT, path) {
            if health_body_ok(&body) {
                return true;
            }
        }
    }
    false
}

pub fn runtime_system_ready() -> bool {
    matches!(probe_runtime_state(), RuntimeProbeState::Ready)
}

pub fn probe_runtime_state() -> RuntimeProbeState {
    let Some(health_body) = http_get_body(RUNTIME_PORT, "/health") else {
        return RuntimeProbeState::PortClosed;
    };
    if let Some(err) = extract_init_error(&health_body) {
        return RuntimeProbeState::InitFailed(err);
    }
    let Some(ready_body) = http_get_body(RUNTIME_PORT, "/v1/system/ready") else {
        return RuntimeProbeState::PortClosed;
    };
    if response_body_ready(&ready_body) {
        return RuntimeProbeState::Ready;
    }
    if let Some(err) = extract_init_error(&ready_body) {
        return RuntimeProbeState::InitFailed(err);
    }
    RuntimeProbeState::Warming
}

fn health_body_ok(body: &str) -> bool {
    let lower = body.to_lowercase();
    if lower.contains("cnexus") {
        return true;
    }
    response_body_ready(&lower)
        || lower.contains("\"status\":\"ok\"")
        || lower.contains("\"status\": \"ok\"")
        || lower.contains("\"status\":\"warming\"")
        || lower.contains("\"status\": \"warming\"")
}

fn response_body_ready(body: &str) -> bool {
    if body.contains("\"init_error\":")
        && !body.contains("\"init_error\":null")
        && !body.contains("\"init_error\": null")
    {
        return false;
    }
    if body.contains("\"runtime_pointer\":false") || body.contains("\"runtime_pointer\": false") {
        return false;
    }
    if body.contains("\"checks\":") {
        let lower = body.to_lowercase();
        if lower.contains("\"ok\":false") && lower.contains("\"runtime\"") {
            return false;
        }
    }
    body.contains("\"status\":\"ready\"")
        || body.contains("\"status\": \"ready\"")
        || body.contains("'status': 'ready'")
}

fn extract_init_error(body: &str) -> Option<String> {
    let marker = "\"init_error\":";
    let idx = body.find(marker)?;
    let tail = body[idx + marker.len()..].trim_start();
    if tail.starts_with("null") {
        return None;
    }
    let rest = tail.strip_prefix('"')?;
    let end = rest.find('"')?;
    let value = rest[..end].trim();
    if value.is_empty() {
        None
    } else {
        Some(value.to_string())
    }
}

pub fn http_get_body(port: u16, path: &str) -> Option<String> {
    let addr = format!("127.0.0.1:{port}");
    let mut stream = TcpStream::connect(&addr).ok()?;
    let _ = stream.set_read_timeout(Some(Duration::from_millis(1500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
    let req = format!("GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n");
    stream.write_all(req.as_bytes()).ok()?;

    let mut response = String::new();
    let mut buf = [0u8; 4096];
    loop {
        match stream.read(&mut buf) {
            Ok(0) => break,
            Ok(n) => {
                response.push_str(&String::from_utf8_lossy(&buf[..n]));
                if response.len() > 65536 {
                    break;
                }
            }
            Err(_) => break,
        }
    }

    if !response.contains("200") {
        return None;
    }
    response
        .split("\r\n\r\n")
        .nth(1)
        .map(|body| body.to_string())
        .or(Some(response))
}
