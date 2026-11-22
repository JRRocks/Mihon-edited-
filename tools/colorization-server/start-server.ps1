# Starts the colorization server for Mihon (edited). Arguments go to colorization_server.py, e.g. --engine mc2.
# The first run downloads uv (GitHub), Python and its packages, then the AI models (Hugging Face) into
# %USERPROFILE%\.cache\mihon-colorization: deleting that folder uninstalls everything.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$cache = Join-Path $env:USERPROFILE '.cache\mihon-colorization'
$uvVersion = '0.13.4'
$uvDir = Join-Path $cache "uv-$uvVersion"
$uv = Join-Path $uvDir 'uv.exe'
if (-not (Test-Path $uv)) {
    Write-Host "Downloading uv $uvVersion..."
    New-Item -ItemType Directory -Force $uvDir | Out-Null
    $zip = Join-Path $cache 'uv.zip'
    Invoke-WebRequest -Uri "https://github.com/astral-sh/uv/releases/download/$uvVersion/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip
    if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne 'CCEC7508A07D9933D7CB1261880633EFCF1F30D6E6EDDAB21823F1DAE6F23225') {
        Remove-Item $zip
        throw 'The uv download is corrupted, try again.'
    }
    Expand-Archive $zip $uvDir -Force
    Remove-Item $zip
}

$env:UV_CACHE_DIR = Join-Path $cache 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $cache 'python'
$env:UV_PYTHON_INSTALL_BIN = '0'
# uv reports its progress on stderr, which Windows PowerShell turns into errors when 'Stop' is set
$ErrorActionPreference = 'Continue'
& $uv run --script (Join-Path $PSScriptRoot 'colorization_server.py') --cache $cache @args
exit $LASTEXITCODE
