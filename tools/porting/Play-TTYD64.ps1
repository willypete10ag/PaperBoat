# A Windows PowerShell 5.1+ launcher. All generated data stays under SessionRoot.
[CmdletBinding()]
param(
    [string]$Rom,
    [string]$Archive,
    [ValidateSet('healing', 'status')][string]$Profile = 'healing',
    [string]$SessionRoot = (Join-Path $env:LOCALAPPDATA 'PaperBoat-TTYD64-playtest'),
    [switch]$PreflightOnly
)
$ErrorActionPreference = 'Stop'
$package = $PSScriptRoot
$exe = Join-Path $package 'Paperboat.exe'

# Start-Process uses one Windows command-line string, including in PowerShell 5.1.
function Quote-Argument([string]$Value) {
    return '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}
function Run-Paperboat([string[]]$Arguments, [string]$LogBase) {
    $line = ($Arguments | ForEach-Object { Quote-Argument $_ }) -join ' '
    $process = Start-Process -FilePath $exe -ArgumentList $line -WorkingDirectory $package `
        -RedirectStandardOutput ($LogBase + '.stdout.log') -RedirectStandardError ($LogBase + '.stderr.log') `
        -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "PaperBoat exited with code $($process.ExitCode). See $LogBase.stderr.log and $LogBase.stdout.log"
    }
}

try {
    foreach ($name in @('Paperboat.exe', 'paperboat.o2r', 'config.yml', 'playtest-keyboard.json', 'assets')) {
        if (-not (Test-Path -LiteralPath (Join-Path $package $name))) {
            throw "Missing $name. Extract the complete Paperboat-windows ZIP before running the launcher."
        }
    }
    New-Item -ItemType Directory -Force -Path $SessionRoot | Out-Null
    $SessionRoot = (Resolve-Path -LiteralPath $SessionRoot).Path
    $id = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $logs = Join-Path $SessionRoot ('logs-' + $id)
    New-Item -ItemType Directory -Path $logs | Out-Null
    if (-not $Archive) {
        if (-not $Rom) {
            Add-Type -AssemblyName System.Windows.Forms
            $picker = New-Object System.Windows.Forms.OpenFileDialog
            $picker.Title = 'Select your own supported Paper Mario (USA) ROM'
            $picker.Filter = 'Nintendo 64 ROM (*.z64;*.n64;*.v64)|*.z64;*.n64;*.v64|All files (*.*)|*.*'
            if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'No ROM selected.' }
            $Rom = $picker.FileName
        }
        $Rom = (Resolve-Path -LiteralPath $Rom).Path
        $romHash = (Get-FileHash -LiteralPath $Rom -Algorithm SHA256).Hash
        $exeHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
        $cache = Join-Path $SessionRoot ('archives\' + $romHash + '-' + $exeHash.Substring(0, 12))
        $Archive = Join-Path $cache 'pm64.o2r'
        $receipt = Join-Path $cache 'archive.json'
        if (Test-Path -LiteralPath $receipt) {
            $previous = Get-Content -Raw -LiteralPath $receipt | ConvertFrom-Json
            if ($previous.rom_sha256 -ne $romHash -or $previous.executable_sha256 -ne $exeHash -or
                -not (Test-Path -LiteralPath $Archive) -or
                $previous.archive_sha256 -ne (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash) {
                throw "ROM cache verification failed. Move aside this generated cache folder and retry: $cache"
            }
        } else {
            if (Test-Path -LiteralPath $cache) { throw "Incomplete ROM cache. Move it aside and retry: $cache" }
            New-Item -ItemType Directory -Path $cache | Out-Null
            Write-Host 'Building a local archive from your ROM (first run for this build)...'
            Run-Paperboat -Arguments @('--extract-rom', $Rom, $package, $cache) -LogBase (Join-Path $logs 'extract')
            if (-not (Test-Path -LiteralPath $Archive)) { throw "Extraction did not create $Archive" }
            @{
                rom_sha256 = $romHash; executable_sha256 = $exeHash
                archive_sha256 = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
            } | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath $receipt
        }
    }
    $Archive = (Resolve-Path -LiteralPath $Archive).Path
    $session = Join-Path $SessionRoot ('sessions\' + $id)
    $mode = '--ttyd64-playtest'
    if ($PreflightOnly) { $mode = '--ttyd64-playtest-preflight' }
    @{
        started_utc = [DateTime]::UtcNow.ToString('o'); profile = $Profile; session = $session
        preflight_only = [bool]$PreflightOnly
        executable_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
        launcher_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
        archive_sha256 = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
    } | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $logs 'launch.json')
    Write-Host "Fresh isolated $Profile session: $session"
    Write-Host 'WASD move; X confirm/jump; C cancel/hammer; Space pause; Left items; Right partners; Z battle order.'
    Write-Host 'Starts in Goomba Village. The right exit leads toward Goomba Road battles. Close the game to finish.'
    Run-Paperboat -Arguments @($mode, $session, $package, $Archive, $Profile) -LogBase (Join-Path $logs 'game')
    [DateTime]::UtcNow.ToString('o') | Set-Content -LiteralPath (Join-Path $logs 'finished-utc.txt')
    Write-Host "Finished. Session saves/config: $session. Launcher logs: $logs"
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
