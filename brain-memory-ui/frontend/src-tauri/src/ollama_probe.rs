use serde::Serialize;

const FALLBACK_HOSTS: [&str; 2] = ["http://127.0.0.1:11434", "http://localhost:11434"];
const PROBE_TIMEOUT_MS: u64 = 2_500;
const DEFAULT_OLLAMA_HOST: &str = "http://127.0.0.1:11434";

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OllamaProbeResult {
    pub reachable: bool,
    pub host: Option<String>,
    pub model_count: usize,
    pub error: Option<String>,
    /// Value of OLLAMA_HOST in the Tauri process (may differ from sidecar if not synced).
    pub ollama_host_env: Option<String>,
    /// Per-host probe notes for diagnostics.
    pub attempts: Vec<String>,
}

fn classify_reqwest_err(err: &reqwest::Error) -> String {
    if err.is_timeout() {
        return format!("Timeout after {PROBE_TIMEOUT_MS}ms");
    }
    if err.is_connect() {
        return format!("Connection refused or unreachable: {err}");
    }
    format!("{err}")
}

fn probe_hosts() -> Vec<String> {
    let mut hosts = Vec::new();
    if let Ok(env_host) = std::env::var("OLLAMA_HOST") {
        let trimmed = env_host.trim();
        if !trimmed.is_empty() {
            hosts.push(trimmed.trim_end_matches('/').to_string());
        }
    }
    for host in FALLBACK_HOSTS {
        if !hosts.iter().any(|h| h == host) {
            hosts.push(host.to_string());
        }
    }
    if hosts.is_empty() {
        hosts.push(DEFAULT_OLLAMA_HOST.to_string());
    }
    hosts
}

#[tauri::command]
pub async fn probe_ollama_local() -> OllamaProbeResult {
    let ollama_host_env = std::env::var("OLLAMA_HOST").ok();
    crate::boot_trace::trace(&format!(
        "probe_ollama_local: OLLAMA_HOST={}",
        ollama_host_env.as_deref().unwrap_or("(unset)")
    ));

    let client = match reqwest::Client::builder()
        .timeout(std::time::Duration::from_millis(PROBE_TIMEOUT_MS))
        .no_proxy()
        .build()
    {
        Ok(c) => c,
        Err(err) => {
            return OllamaProbeResult {
                reachable: false,
                host: None,
                model_count: 0,
                error: Some(format!("reqwest client build failed: {err}")),
                ollama_host_env,
                attempts: vec![],
            };
        }
    };

    let hosts = probe_hosts();
    let mut attempts = Vec::new();

    for host in &hosts {
        let url = format!("{host}/api/tags");
        match client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let model_count = resp
                    .json::<serde_json::Value>()
                    .await
                    .ok()
                    .and_then(|v| v.get("models").and_then(|m| m.as_array()).map(|a| a.len()))
                    .unwrap_or(0);
                let note = format!("{host}: OK models={model_count}");
                crate::boot_trace::trace(&format!("ollama probe {note}"));
                attempts.push(note);
                return OllamaProbeResult {
                    reachable: true,
                    host: Some(host.clone()),
                    model_count,
                    error: None,
                    ollama_host_env,
                    attempts,
                };
            }
            Ok(resp) => {
                let note = format!("{host}: HTTP {}", resp.status());
                crate::boot_trace::trace(&format!("ollama probe {note}"));
                attempts.push(note);
            }
            Err(err) => {
                let note = format!("{host}: {}", classify_reqwest_err(&err));
                crate::boot_trace::trace(&format!("ollama probe {note}"));
                attempts.push(note);
            }
        }
    }

    OllamaProbeResult {
        reachable: false,
        host: None,
        model_count: 0,
        error: Some(format!(
            "Ollama not reachable. attempts=[{}]",
            attempts.join("; ")
        )),
        ollama_host_env,
        attempts,
    }
}
