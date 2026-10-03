# labs/w6d1_p55_check.ps1 -- Week 6 Din 1, Step 5 (P-55).
# Two arms against the disposable database relay_w6d1 that the Step 4 harness run leaves behind:
#   silent : SINK_URL -> labs/w6d1_silent_server.py (accepts the TCP connection, never answers)
#   closed : SINK_URL -> a port nothing listens on
# Writes values only.
param([string]$RepoRoot = "")
$ErrorActionPreference = 'Continue'
if ([string]::IsNullOrEmpty($RepoRoot)) {
  $RepoRoot = (Get-Location).Path
}
Set-Location $RepoRoot
$db     = 'relay_w6d1'
$run    = 'w6d1_p55_' + (Get-Date -Format 'yyyyMMdd_HHmmss_ffffff')
$py     = (Resolve-Path .\.venv\Scripts\python.exe).Path
$server = Join-Path $RepoRoot 'labs\w6d1_silent_server.py'
$pkg    = if (Test-Path (Join-Path $RepoRoot 'relay')) { 'relay' } else { 'src' }

$reset  = 'DO $$ BEGIN IF current_database() <> ''relay_w6d1'' THEN RAISE EXCEPTION ''wrong db''; END IF; END $$; TRUNCATE outbox RESTART IDENTITY; INSERT INTO outbox (job_id, effect_key, payload) VALUES (55, ''job:55'', ''{}'');'
$keep = @{}
foreach ($k in 'DATABASE_URL', 'SINK_URL', 'RELAY_PROCESS_NAME', 'PYTHONUNBUFFERED') { $keep[$k] = [Environment]::GetEnvironmentVariable($k) }
$env:DATABASE_URL = (Get-Content .env | Select-String '^DATABASE_URL=').Line.Split('=', 2)[1] -replace '/relay$', "/$db"
$env:PYTHONUNBUFFERED = '1'
$o = [System.Collections.Generic.List[string]]::new()
$srv = Start-Process -FilePath $py -ArgumentList '-u', $server -PassThru -NoNewWindow -RedirectStandardOutput "logs\${run}_server.log" -RedirectStandardError "logs\${run}_server.err.log"
try {
  Start-Sleep -Seconds 2
  foreach ($arm in @(@('silent', 'http://127.0.0.1:8099/deliver', 13), @('closed', 'http://127.0.0.1:8098/deliver', 8))) {
    docker exec relay-db-1 psql -U postgres -d $db -v ON_ERROR_STOP=1 -c $reset | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "reset failed -- does relay_w6d1 exist? run the Step 4 harness first" }
    $env:SINK_URL = $arm[1]; $env:RELAY_PROCESS_NAME = "dispatcher_w6d1_$($arm[0])"
    $log = "logs\${run}_$($arm[0])_dispatcher.log"
    $d = Start-Process -FilePath $py -ArgumentList '-u', '-m', "$pkg.dispatcher" -PassThru -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError "logs\${run}_$($arm[0])_dispatcher.err.log"
    Start-Sleep -Seconds $arm[2]
    Stop-Process -Id $d.Id -Force
    Start-Sleep -Seconds 1
    $lines = @([IO.File]::ReadAllLines((Resolve-Path $log)) | Where-Object { $_.Contains('[dispatch_error]') })
    $attempts = (docker exec relay-db-1 psql -U postgres -d $db -t -A -c 'SELECT attempts FROM outbox WHERE id = 1;') -join ''
    $o.Add($arm[0] + ' window_s=' + $arm[2] + ' dispatch_error_lines=' + $lines.Count + ' with_ReadTimeout=' + @($lines | Where-Object { $_.Contains('ReadTimeout') }).Count + ' with_ConnectError=' + @($lines | Where-Object { $_.Contains('ConnectError') }).Count + ' outbox_attempts=' + $attempts)
    if ($lines.Count -gt 0) { $o.Add($arm[0] + ' first_line: ' + $lines[0]) }
  }
}
finally {
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*w6d1_silent_server*' -or ($_.CommandLine -like "*$RepoRoot*" -and $_.CommandLine -match "($pkg|src)\.dispatcher") } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  foreach ($k in $keep.Keys) { [Environment]::SetEnvironmentVariable($k, $keep[$k]) }
}
$o.Add('relay_python_after=' + @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$RepoRoot*" -or $_.CommandLine -like '*w6d1_silent_server*' }).Count)
$o | Out-File -Encoding utf8 "logs\${run}_census.txt"
Get-Content "logs\${run}_census.txt"
