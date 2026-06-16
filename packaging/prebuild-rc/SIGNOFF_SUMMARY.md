# CNexus RC Signoff Summary

> Generated: 2026-06-13 02:40:21 路 `npm run prebuild:rc-report`
> Machine JSON: `packaging/prebuild-rc/MANUAL_SIGNOFF.json`

## Release

| Field | Value |
|-------|-------|
| Version | `0.1.0-alpha` |
| Readiness | **RC Candidate (not approved)** |

## Automated 鈥?Smoke (Runtime truth probe)

| Metric | Value |
|--------|-------|
| Smoke | PASS |
| Smoke at | 2026-06-13T02:12:16.5796922+08:00 |
| Runtime ready | 20934 ms |
| WS first frame | 112 ms |
| Shutdown clean | 1583 ms |
| Report | [LATEST_SMOKE.txt](./LATEST_SMOKE.txt) |

## Automated 鈥?Gate

| Metric | Value |
|--------|-------|
| Last run | 2026-06-13 02:38:23 |
| Summary | GATE SUMMARY: PASS=25 WARN=2 FAIL=2 |
| Build allowed (automated) | FAIL |
| Report | [LATEST_GATE.txt](./LATEST_GATE.txt) 路 [LATEST_AUDIT.txt](./LATEST_AUDIT.txt) |

## Machine context

| Field | Value |
|-------|-------|
| Hostname | `新项目` |
| OS | Microsoft Windows NT 10.0.26200.0 |
| DPI scale | 100% |
| Admin user | FAIL |

## Manual gates (required)

- **FAIL** `installer_install_ok` (Installer install)
- **FAIL** `appdata_paths_ok` (AppData paths writable)
- **FAIL** `runtime_auto_start_ok` (Runtime auto-start)
- **FAIL** `float_ui_ok_no_mahjong` (Float UI (no mahjong tile))
- **FAIL** `no_cmd_black_window_ok` (No CMD black window)
- **FAIL** `tray_quit_no_orphan` (Tray quit (no orphan))
- **FAIL** `uninstall_no_orphan` (Uninstall (no orphan))
- **FAIL** `port_8000_released_after_quit` (Port 8000 released after quit)

## Optional gates

- **FAIL** `dpi_125_150_ok` (DPI 125% / 150%)
- **FAIL** `low_privilege_data_write_ok` (Low-privilege data write)
- **FAIL** `registry_clean_after_uninstall_ok` (Registry clean after uninstall)
- **FAIL** `alt_shift_m_toggle_ok` (Alt+Shift+M toggle)
- **FAIL** `dual_monitor_float_ok` (Dual monitor float)

## Signoff

| Field | Value |
|-------|-------|
| Signed | FAIL |
| Artifacts | `packaging/prebuild-rc/signoff-artifacts/0.1.0-alpha/20260613-0218/` |

## Warnings

- `runtime_ready_slow (20934 ms)`
- `automated_gate_not_green (link/cl PATH?)`
- `manual_signoff_not_signed`
- `dpi_125_150_ok_not_verified`
- `low_privilege_data_write_ok_not_verified`
- `registry_clean_after_uninstall_ok_not_verified`
- `alt_shift_m_toggle_ok_not_verified`
- `dual_monitor_float_ok_not_verified`

## Evidence chain

```text
Source -> Static Gate -> Smoke Runtime -> MANUAL_SIGNOFF -> gate:strict -> tauri:build
```

## Next steps

1. Open **VS x64 Native Tools** 鈫?`npm run prebuild:gate` (link/cl on PATH)
- Complete [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md) 鈫?set `signoff.signed=true`
- Phase 2 (future): UI headless smoke for Tauri lifecycle

