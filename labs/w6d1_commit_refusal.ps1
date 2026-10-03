# labs/w6d1_commit_refusal.ps1 -- Week 6 Din 1.
# Runs sink + worker + reaper (+ dispatcher for a window) against a disposable database relay_w6d1 in which
# the database REFUSES chosen COMMITs.
#   Phase 1 (t = 0..40 s): refusal triggers active.
#   Phase 2 (t = 40..52 s): refusal triggers dropped, audit triggers kept, so every writer also gets
#                           committed transitions (the positive controls).
# Usage:  pwsh -File labs\w6d1_commit_refusal.ps1 -Phase control    (today's code, before the fix)
#         pwsh -File labs\w6d1_commit_refusal.ps1 -Phase fixed      (after the Step 3 edit)
param(
  [Parameter(Mandatory = $true)][ValidatePattern('^[a-z]+$')][string]$Phase,
  [string]$RepoRoot = ""
)
$ErrorActionPreference = 'Continue'
if ([string]::IsNullOrEmpty($RepoRoot)) {
  $RepoRoot = (Get-Location).Path
}
Set-Location $RepoRoot
$db  = 'relay_w6d1'
$run = "w6d1_${Phase}_" + (Get-Date -Format 'yyyyMMdd_HHmmss_ffffff')
$L   = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Force -Path $L | Out-Null
$py  = (Resolve-Path (Join-Path $RepoRoot '.venv\Scripts\python.exe')).Path
$sql  = Join-Path $RepoRoot 'labs\w6d1_commit_refusal.sql'
$tl  = Join-Path $L "${run}_timeline.txt"

# Detect package name (relay vs src)
$pkg = if (Test-Path (Join-Path $RepoRoot 'relay')) { 'relay' } else { 'src' }

function Stamp([string]$label) { "$label=" + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff') | Out-File -Append -Encoding utf8 $tl }
function Psql([string]$q) { ((docker exec relay-db-1 psql -U postgres -d $db -t -A -F '|' -c $q) -join ' ').Trim() }
function CountIn([string]$file, [string]$needle, [string]$regex = '') {
  if (-not (Test-Path $file)) { return -1 }
  $n = 0
  foreach ($line in [IO.File]::ReadLines($file)) {
    if ($line.Contains($needle) -and ($regex -eq '' -or [regex]::IsMatch($line, $regex))) { $n++ }
  }
  return $n
}
function Snapshot([string]$path) {
  $o = [System.Collections.Generic.List[string]]::new()
  $o.Add("db=" + (Psql "SELECT current_database();"))
  $o.Add("jobs(id:status:attempts:generation)=" + (Psql "SELECT string_agg(id || ':' || status || ':' || attempts || ':' || claim_generation, ' ' ORDER BY id) FROM jobs;"))
  $o.Add("outbox(id:dispatched:attempts)=" + (Psql "SELECT string_agg(id || ':' || (dispatched_at IS NOT NULL) || ':' || attempts, ' ' ORDER BY id) FROM outbox;"))
  $o.Add("sink_rows=" + (Psql "SELECT count(*) FROM sink_deliveries;"))
  $o.Add("audit=" + (Psql "SELECT string_agg(k.kind || '_committed=' || coalesce(c.n, 0), ' ' ORDER BY k.kind) FROM (VALUES ('claim'),('heartbeat'),('mark'),('reclaim'),('dispatch')) AS k(kind) LEFT JOIN (SELECT kind, count(*) AS n FROM w6d1_audit GROUP BY kind) c ON c.kind = k.kind;"))
  $o.Add("hb_seq(last_value:is_called)=" + (Psql "SELECT last_value || ':' || is_called FROM w6d1_hb_seq;"))
  $o.Add("refusal_triggers_left=" + (Psql "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'w6d1\_refuse\_%';"))
  $o | Out-File -Encoding utf8 $path
}
function Start-Relay([string]$name, [string[]]$argList) {
  $env:RELAY_PROCESS_NAME = "${name}_w6d1"
  $p = Start-Process -FilePath $py -ArgumentList $argList -WorkingDirectory $RepoRoot -PassThru -NoNewWindow `
       -RedirectStandardOutput (Join-Path $L "${run}_${name}.log") `
       -RedirectStandardError  (Join-Path $L "${run}_${name}.err.log")
  Stamp "start_$name"
  return $p
}

$before = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$RepoRoot*" }).Count
if ($before -ne 0) {
  Write-Host "Warning: $before python processes running. Terminating them before harness..."
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$RepoRoot*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 2
}

$saved = @{}
foreach ($k in 'DATABASE_URL', 'PYTHONUNBUFFERED', 'RELAY_PROCESS_NAME', 'SINK_URL') { $saved[$k] = [Environment]::GetEnvironmentVariable($k) }
$procs = @()
try {
  Stamp 'run_start'
  "run_id=$run" | Out-File -Append -Encoding utf8 $tl
  "src_hashes(worker,reaper,dispatcher)=" + ((git hash-object "$pkg/worker.py" "$pkg/reaper.py" "$pkg/dispatcher.py") -join ',') | Out-File -Append -Encoding utf8 $tl
  "src_diff_files_vs_HEAD=" + (@(git diff --name-only HEAD -- "$pkg/").Count) | Out-File -Append -Encoding utf8 $tl

  docker exec relay-db-1 psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS $db WITH (FORCE);" | Out-Null
  docker exec relay-db-1 psql -U postgres -d postgres -c "CREATE DATABASE $db;" | Out-Null
  $base = (Get-Content (Join-Path $RepoRoot '.env') | Select-String '^DATABASE_URL=').Line.Split('=', 2)[1]
  $env:DATABASE_URL = $base -replace '/relay$', "/$db"
  if (-not $env:DATABASE_URL.EndsWith("/$db")) { throw "DATABASE_URL rewrite failed" }
  $env:PYTHONUNBUFFERED = '1'
  $mig = (& $py -m alembic upgrade head 2>&1 | ForEach-Object { "$_" }) -join "`n"
  $mig | Out-File -Encoding utf8 (Join-Path $L "${run}_migrate.txt")
  Get-Content $sql -Raw | docker exec -i relay-db-1 psql -U postgres -d $db -v ON_ERROR_STOP=1 *> (Join-Path $L "${run}_setup.txt")
  if ($LASTEXITCODE -ne 0) { throw "setup SQL failed -- see ${run}_setup.txt" }

  $procs += Start-Relay 'sink' @('-u', '-m', 'uvicorn', "$pkg.sink:app", '--host', '127.0.0.1', '--port', '8001')
  $up = $false
  for ($i = 0; $i -lt 40 -and -not $up; $i++) {
    try {
      $tcp = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8001)
      $tcp.Close()
      $up = $true
    } catch { Start-Sleep -Milliseconds 500 }
  }
  if (-not $up) { throw "sink did not answer on port 8001" }
  Stamp 'sink_healthy'

  Stamp 't0'
  $procs += Start-Relay 'worker' @('-u', '-m', "$pkg.worker")
  $procs += Start-Relay 'reaper' @('-u', '-m', "$pkg.reaper")
  Start-Sleep -Seconds 28
  $env:SINK_URL = 'http://127.0.0.1:8001/deliver'
  $procs += Start-Relay 'dispatcher' @('-u', '-m', "$pkg.dispatcher")
  Start-Sleep -Seconds 12

  Snapshot (Join-Path $L "${run}_phase1.txt")
  Psql "DROP TRIGGER w6d1_refuse_claim ON jobs; DROP TRIGGER w6d1_refuse_heartbeat ON jobs; DROP TRIGGER w6d1_refuse_mark ON jobs; DROP TRIGGER w6d1_refuse_reclaim ON jobs; DROP TRIGGER w6d1_refuse_dispatch ON outbox;" | Out-Null
  Stamp 'phase2_start'
  Start-Sleep -Seconds 12
}
finally {
  foreach ($p in $procs) { if ($p) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
  Start-Sleep -Seconds 2
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$RepoRoot*" -and $_.CommandLine -match "($pkg|src)\.(worker|reaper|dispatcher|sink)" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 1
  Stamp 'stopped'
  "relay_python_after=" + @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$RepoRoot*" }).Count | Out-File -Append -Encoding utf8 $tl
  foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
}

Snapshot (Join-Path $L "${run}_final.txt")
$w = Join-Path $L "${run}_worker.log"; $r = Join-Path $L "${run}_reaper.log"
$d = Join-Path $L "${run}_dispatcher.log"; $s = Join-Path $L "${run}_sink.log"
$c = [System.Collections.Generic.List[string]]::new()
foreach ($f in $w, $r, $d, $s) {
  $line = if (Test-Path $f) { (Select-String -Path $f -Pattern '^(\[db\] )?resolved_db=' | Select-Object -First 1).Line } else { 'missing' }
  $c.Add("premise $(Split-Path $f -Leaf): $line")
}
$c.Add("claim_lines=" + (CountIn $w 'Claimed job_id='))
$c.Add("heartbeat_lines=" + (CountIn $w 'Heartbeat sent for job_id='))
$c.Add("mark_lines=" + (CountIn $w 'Marked job_id='))
$c.Add("reclaim_lines=" + (CountIn $r '[reclaim]' 'matched=1'))
$c.Add("dispatch_lines=" + (CountIn $d '[dispatch]'))
$c.Add("mark_error_lines=" + (CountIn $w '[mark_error]'))
$c.Add("heartbeat_error_lines=" + (CountIn $w 'Heartbeat failed:'))
$c.Add("worker_poll_error=" + (CountIn $w 'Claim poll failed:'))
$c.Add("reaper_poll_error=" + (CountIn $r 'Reaper poll failed:'))
$c.Add("dispatcher_poll_error=" + (CountIn $d 'Poll failed:'))
$c.Add("worker_echo_COMMIT=" + (CountIn $w 'COMMIT' 'sqlalchemy\.engine\.Engine COMMIT$'))
$c.Add("sink_applied=" + (CountIn $s 'result=applied'))
$c.Add("sink_duplicate=" + (CountIn $s 'result=duplicate'))
$c.Add("final_" + ((Get-Content (Join-Path $L "${run}_final.txt") | Select-String '^audit=').Line))
$c | Out-File -Encoding utf8 (Join-Path $L "${run}_census.txt")
Get-Content $tl, (Join-Path $L "${run}_phase1.txt"), (Join-Path $L "${run}_final.txt"), (Join-Path $L "${run}_census.txt")
