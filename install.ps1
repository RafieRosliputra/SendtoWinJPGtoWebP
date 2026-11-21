# Muat turun jpg2webp.exe terbaru dari GitHub Release dan pasang ke Send To.
# Guna:  irm https://raw.githubusercontent.com/RafieRosliputra/SendtoWinJPGtoWebP/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$dir = Join-Path $env:LOCALAPPDATA 'JPGtoWebP'
New-Item -ItemType Directory -Force $dir | Out-Null
$exe = Join-Path $dir 'jpg2webp.exe'
Invoke-WebRequest 'https://github.com/RafieRosliputra/SendtoWinJPGtoWebP/releases/download/latest/jpg2webp.exe' -OutFile $exe
& $exe --install --no-pause
