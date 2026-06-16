; CNexus — stop UI + Runtime + embedded Python before uninstall/update.

!macro CNEXUS_PREFLIGHT_WARN
  DetailPrint "CNexus: checking environment for port/process conflicts..."
  nsExec::ExecToStack 'powershell -NoProfile -NonInteractive -Command "$$lines=@(); $$seen=@{}; function Add($$k,$$p,$$n,$$d){ if(-not $$p -or $$seen[$$p]){return}; $$seen[$$p]=1; $$lines += ($$k+''|PID ''+$$p+'' (''+$$n+'') ''+$$d) }; Get-NetTCPConnection -LocalPort 8000 -State Listen -EA SilentlyContinue | %% { $$p=$$_.OwningProcess; $$pr=Get-Process -Id $$p -EA SilentlyContinue; $$cmd=(Get-CimInstance Win32_Process -Filter (''ProcessId=''+$$p) -EA SilentlyContinue).CommandLine; Add ''port_8000'' $$p $$(if($$pr){$$pr.ProcessName}else{''?''}) $$(if($$cmd){$$cmd}else{''listening''}) }; Get-CimInstance Win32_Process -EA SilentlyContinue | ? { ($$_.Name -in ''python.exe'',''pythonw.exe'') -and ($$_.CommandLine -match ''api\.main'') -and ($$_.CommandLine -notmatch ''runtime-bundle'') } | %% { Add ''dev_api'' $$_.ProcessId $$_.Name $$_.CommandLine }; if($$lines.Count -eq 0){ exit 0 }; $$lines -join [char]10"'
  Pop $0
  Pop $1
  StrCmp $1 "" preflight_ok 0
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "检测到环境冲突（端口 8000 或开发版 Runtime）：$\n$\n$1$\n$\n安装/升级将停止上述进程后继续。是否继续？" IDOK preflight_ok IDCANCEL preflight_abort
  preflight_abort:
    Abort "安装已取消：请先关闭冲突进程后重试。"
  preflight_ok:
!macroend

!macro CNEXUS_KILL_RUNTIME
  DetailPrint "Stopping CNexus Runtime..."
  nsis_tauri_utils::KillProcess "CNexus.exe"
  nsis_tauri_utils::KillProcess "cnexus-product.exe"
  nsis_tauri_utils::KillProcess "cnexus-runtime.exe"
  nsExec::ExecToLog 'powershell -NoProfile -NonInteractive -Command "$$names=@(''python.exe'',''pythonw.exe''); Get-CimInstance Win32_Process | Where-Object { ($$names -contains $$_.Name) -and ($$_.CommandLine -match ''api\.main'' -or $$_.CommandLine -match ''runtime-bundle'') } | ForEach-Object { Stop-Process -Id $$_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { taskkill /F /T /PID $$($$_.OwningProcess) 2>$$null }"'
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ReadEnvStr $0 LOCALAPPDATA
  CreateDirectory "$0\CNexus"
  CreateDirectory "$0\CNexus\data"
  CreateDirectory "$0\CNexus\data\blocks"
  CreateDirectory "$0\CNexus\data\lancedb"
  ; Do NOT pre-create kuzu_db — Kuzu owns that path.

  ; Runtime conflict monitor log (JSONL) — seed from bundle template on first install.
  IfFileExists "$0\CNexus\data\runtime-conflict-monitor.log" conflict_log_exists 0
    IfFileExists "$INSTDIR\resources\runtime-bundle\app\data-templates\runtime-conflict-monitor.log" 0 conflict_log_seed_inline
      CopyFiles "$INSTDIR\resources\runtime-bundle\app\data-templates\runtime-conflict-monitor.log" "$0\CNexus\data\runtime-conflict-monitor.log"
      Goto conflict_log_exists
    conflict_log_seed_inline:
      FileOpen $1 "$0\CNexus\data\runtime-conflict-monitor.log" w
      FileWrite $1 '{"event":"INSTALL_INITIALIZED","level":"info","source":"nsis","message":"Runtime conflict monitor log created at install"}$\r$\n'
      FileClose $1
  conflict_log_exists:
  IfFileExists "$INSTDIR\resources\runtime-bundle\app\data-templates\runtime-conflict-monitor.README.txt" 0 +2
    CopyFiles "$INSTDIR\resources\runtime-bundle\app\data-templates\runtime-conflict-monitor.README.txt" "$0\CNexus\data\runtime-conflict-monitor.README.txt"

  ; Desktop shortcut: CNexus avatar icon (not generic installer icon)
  StrCpy $R9 "$INSTDIR\cnexus-product.exe"
  IfFileExists "$INSTDIR\icons\icon.ico" 0 +2
    StrCpy $R9 "$INSTDIR\icons\icon.ico"
  Delete "$DESKTOP\CNexus.lnk"
  CreateShortcut "$DESKTOP\CNexus.lnk" "$INSTDIR\cnexus-product.exe" "" "$R9" 0
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro CNEXUS_KILL_RUNTIME
!macroend

!macro NSIS_HOOK_PREINSTALL
  ; Warn before stopping conflicting dev Runtime / :8000 listeners.
  !insertmacro CNEXUS_PREFLIGHT_WARN
  ; Re-install / upgrade: ensure old Runtime tree is gone.
  !insertmacro CNEXUS_KILL_RUNTIME
!macroend
