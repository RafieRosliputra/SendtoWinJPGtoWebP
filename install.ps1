# Pasang jpg2webp.exe + ffmpeg, dan 2 menu Send To.
# Guna (PowerShell biasa):  irm https://raw.githubusercontent.com/RafieRosliputra/SendtoWinJPGtoWebP/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest jauh lebih laju tanpa progress bar
$base = 'https://github.com/RafieRosliputra/SendtoWinJPGtoWebP/releases/download/latest'
$dir = Join-Path $env:LOCALAPPDATA 'JPGtoWebP'
New-Item -ItemType Directory -Force $dir | Out-Null
Write-Host 'Muat turun jpg2webp.exe...'
Invoke-WebRequest "$base/jpg2webp.exe" -OutFile (Join-Path $dir 'jpg2webp.exe')
Write-Host 'Muat turun ffmpeg (untuk MP4)...'
$zip = Join-Path $env:TEMP 'ffmpeg-win64.zip'
Invoke-WebRequest "$base/ffmpeg-win64.zip" -OutFile $zip
Expand-Archive $zip $dir -Force
Remove-Item $zip
& (Join-Path $dir 'jpg2webp.exe') --install --no-pause
