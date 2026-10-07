# labs/w6d3_key_scan.ps1 -- Week 6 Din 3: is the provider API key anywhere it must not be?
# Reads the key's VALUE from .env by NAME, keeps it in memory, and counts where it appears. Never prints it.
# Every domain has a positive control that uses the SAME search code, so a domain the scan cannot actually see shows
# up as control_hits=0 instead of a quiet "0 leaks":
#   logs    : every logs\w6d3_* file                    control: "resolved_db=<Database>" (src/database.py prints it)
#   tracked : every git-tracked file + the staged diff  control: "DATABASE_URL=" (.env.example)
#   history : PSReadLine ConsoleHost_history.txt        control: "git "
#   db      : pg_dump --data-only of <Database>         control: "w6d3-canary" (put it in one job payload)
# Usage: pwsh -File labs\w6d3_key_scan.ps1 -KeyName <YOUR_KEY_VAR> -Out logs\w6d3_<step>_keyscan.txt [-Database relay_w6d3]
# Values and labels only; no conclusions (P-52).
param(
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Z][A-Z0-9_]*$')][string]$KeyName,
  [Parameter(Mandatory = $true)][string]$Out,
  [ValidatePattern('^relay_w6d3[a-z0-9_]*$')][string]$Database = 'relay_w6d3',
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
  [string]$EnvFile = ''
)
$ErrorActionPreference = 'Stop'
Set-Location $RepoRoot
if ($EnvFile -eq '') { $EnvFile = Join-Path $RepoRoot '.env' }
$line = @(Get-Content $EnvFile | Where-Object { $_ -match "^\s*$KeyName\s*=" }) | Select-Object -First 1
if (-not $line) { throw "$KeyName not found in $EnvFile" }
$key = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
if ($key.Length -lt 20) { throw "$KeyName value is shorter than 20 chars -- refusing (a short needle matches by accident)" }

function Count-In([string[]]$paths, [string]$needle) {
  $n = 0
  foreach ($p in $paths) {
    if (Test-Path -LiteralPath $p -PathType Leaf) {
      if ([IO.File]::ReadAllText((Resolve-Path -LiteralPath $p).Path).Contains($needle)) { $n++ }
    }
  }
  return $n
}

$o = [System.Collections.Generic.List[string]]::new()
$o.Add("key_name=$KeyName key_len_ge_20=True database=$Database at=" + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'))

$logFiles = @(Get-ChildItem (Join-Path $RepoRoot 'logs') -Filter 'w6d3_*' -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
$o.Add("logs_files=$($logFiles.Count) logs_hits=" + (Count-In $logFiles $key) + " logs_control_hits=" + (Count-In $logFiles "resolved_db=$Database"))

$tracked = @(git ls-files | ForEach-Object { Join-Path $RepoRoot $_ })
$staged = (git diff --cached) -join "`n"
$o.Add("tracked_files=$($tracked.Count) tracked_hits=" + (Count-In $tracked $key) + " tracked_control_hits=" + (Count-In $tracked 'DATABASE_URL=') +
       " staged_diff_hits=" + [int]$staged.Contains($key))

$hist = Join-Path $env:APPDATA 'Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt'
$o.Add("history_file_exists=" + (Test-Path -LiteralPath $hist) + " history_hits=" + (Count-In @($hist) $key) + " history_control_hits=" + (Count-In @($hist) 'git '))

$dump = (docker exec relay-db-1 pg_dump -U postgres --data-only --no-owner $Database) -join "`n"
$o.Add("db_dump_bytes=$($dump.Length) db_hits=" + [int]$dump.Contains($key) + " db_control_hits=" + [int]$dump.Contains('w6d3-canary'))
$key = $null
$o | Out-File -Encoding utf8 $Out
Get-Content $Out
