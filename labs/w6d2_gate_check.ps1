# labs/w6d2_gate_check.ps1 -- Week 6 Din 2, Step 1 (P-44).
# Starts the API (relay.main:app) once per value of ENABLE_TEST_ROUTES and records what each route answers.
# Read-only against the evidence DB: /healthz runs SELECT 1, /slow-hold is called with seconds=0.
# Usage: pwsh -File labs\w6d2_gate_check.ps1 -Phase control   (today's main.py, before the edit)
#        pwsh -File labs\w6d2_gate_check.ps1 -Phase fixed     (after the Step 1 edit)
# Every line it writes is a value or a label. It writes no conclusions (P-52).
param(
  [Parameter(Mandatory = $true)][ValidatePattern('^[a-z]+$')][string]$Phase,
  [string]$RepoRoot = '',
  [string]$OutDir = '',
  [int]$Port = 8000
)
if ($RepoRoot -eq '') {
  $RepoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot '..')).Path } else { (Get-Location).Path }
}
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
Set-Location $RepoRoot
if ($OutDir -eq '') { $OutDir = Join-Path $RepoRoot 'logs' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$run = "w6d2_gate_${Phase}_" + (Get-Date -Format 'yyyyMMdd_HHmmss_ffffff')
$py  = (Resolve-Path (Join-Path $RepoRoot '.venv\Scripts\python.exe')).Path
$B   = "http://127.0.0.1:$Port"
$out = Join-Path $OutDir "${run}_census.txt"

function Hit([string]$method, [string]$path) {
  try {
    $resp = Invoke-WebRequest -Method $method -Uri ($B + $path) -TimeoutSec 10 -UseBasicParsing
    return [string][int]$resp.StatusCode
  }
  catch [System.Net.WebException] {
    if ($_.Exception.Response) {
      return [string][int]$_.Exception.Response.StatusCode
    }
    return 'ERR:' + $_.Exception.GetType().Name
  }
  catch {
    return 'ERR:' + $_.Exception.GetType().Name
  }
}
function Sweep {
  foreach ($c in @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$RepoRoot*" -and $_.CommandLine -match 'relay\.main:app' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

if (@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -ne 0) { throw "port $Port already has a listener -- stop it first" }
$o = [System.Collections.Generic.List[string]]::new()
$o.Add("run_id=$run")
$o.Add("main_hash=" + (git hash-object relay/main.py))
$o.Add("src_diff_files_vs_HEAD=" + ((git diff --name-only HEAD -- relay/) -join ','))
$o.Add("dotenv_mentions_flag=" + @(Select-String -Path (Join-Path $RepoRoot '.env') -SimpleMatch 'ENABLE_TEST_ROUTES' -ErrorAction SilentlyContinue).Count)
$saved = @{}
foreach ($k in 'ENABLE_TEST_ROUTES', 'RELAY_PROCESS_NAME', 'PYTHONUNBUFFERED') { $saved[$k] = [Environment]::GetEnvironmentVariable($k) }
$env:PYTHONUNBUFFERED = '1'
$arms = @(@('unset', $null), @('empty', ''), @('zero', '0'), @('true', 'true'), @('garbage', 'banana'), @('one', '1'))
try {
  foreach ($a in $arms) {
    $name = $a[0]
    if ($null -eq $a[1]) { Remove-Item Env:ENABLE_TEST_ROUTES -ErrorAction SilentlyContinue } else { $env:ENABLE_TEST_ROUTES = $a[1] }
    $env:RELAY_PROCESS_NAME = "api_w6d2_$name"
    $log = Join-Path $OutDir "${run}_${name}_api.log"
    $p = Start-Process -FilePath $py -ArgumentList '-u', '-m', 'uvicorn', 'relay.main:app', '--host', '127.0.0.1', '--port', "$Port" `
         -WorkingDirectory $RepoRoot -PassThru -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    $null = $p.Handle
    $up = $false
    for ($i = 0; $i -lt 40 -and -not $up -and -not $p.HasExited; $i++) {
      if ((Hit 'GET' '/health') -eq '200') { $up = $true } else { Start-Sleep -Milliseconds 300 }
    }
    if ($up) {
      $paths = @((Invoke-RestMethod -Uri "$B/openapi.json" -TimeoutSec 5 -UseBasicParsing).paths.PSObject.Properties.Name)
      $line = "arm=$name listening=True health=" + (Hit 'GET' '/health') + ' healthz=' + (Hit 'GET' '/healthz') +
              ' slow_hold_get=' + (Hit 'GET' '/slow-hold?seconds=0') + ' slow_hold_post=' + (Hit 'POST' '/slow-hold?seconds=0') +
              ' db_ping=' + (Hit 'GET' '/db-ping') +
              ' openapi_slow_hold=' + @($paths | Where-Object { $_ -eq '/slow-hold' }).Count +
              ' openapi_db_ping=' + @($paths | Where-Object { $_ -eq '/db-ping' }).Count
    }
    else {
      Start-Sleep -Milliseconds 500
      $line = "arm=$name listening=False exited=" + $p.HasExited + ' exit_code=' + $(if ($p.HasExited) { $p.ExitCode } else { '-' })
    }
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Sweep
    Start-Sleep -Milliseconds 500
    $all = @(Get-Content $log, "$log.err" -ErrorAction SilentlyContinue)
    $flag = @($all | Where-Object { $_ -match '^test_routes=' })
    $line += ' flag_lines=' + $flag.Count + ' err_mentions_flag=' + @(Get-Content "$log.err" -ErrorAction SilentlyContinue | Where-Object { $_.Contains('ENABLE_TEST_ROUTES') }).Count
    $o.Add($line)
    if ($flag.Count -gt 0) { $o.Add("arm=$name flag_line: " + $flag[0]) }
  }
}
finally {
  Sweep
  foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
}
$o.Add('relay_python_after=' + @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$RepoRoot*" }).Count)
$o | Out-File -Encoding utf8 $out
Get-Content $out
