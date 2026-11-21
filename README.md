# SendtoWinJPGtoWebP

CLI Windows 11 untuk right-click → **Send to**:
- **JPG ke WebP (60%)**: gambar
- **MP4 ke HEVC (kecilkan)**: video, untuk simpanan jangka panjang

## Pasang
PowerShell **biasa** (bukan Administrator), paste satu baris ni sahaja:
```powershell
irm https://raw.githubusercontent.com/RafieRosliputra/SendtoWinJPGtoWebP/main/install.ps1 | iex
```
- Lokasi pasang: `%LOCALAPPDATA%\JPGtoWebP\` (`jpg2webp.exe`, `ffmpeg.exe`, `ffprobe.exe`)
- Shortcut di `%APPDATA%\Microsoft\Windows\SendTo\`
- Buang: `jpg2webp.exe --uninstall`

## JPG → WebP
- `.jpg/.jpeg` → `.webp` **quality 60**, dalam folder yang sama
- Orientation EXIF diaplikasi; EXIF, ICC dan tarikh modified dikekalkan
- JPG asal masuk `_JPG\` dalam folder gambar tu (rekursif)
- Guna semua thread CPU (i9-12900 = 24)

## MP4 → HEVC
- **HEVC 10-bit, NVENC (RTX 3060)**, kualiti tetap **CQ 26** (kualiti turun lebih kurang 10%)
- Resolusi, fps dan rotation kekal. Audio AAC disalin terus; LPCM (Sony) ditukar ke AAC 256k
- Nama fail sama (`.mp4`). MP4 asal masuk `_MP4\`
- Kalau hasil HEVC **tak lebih kecil**, fail asal dikekalkan (DILANGKAU)
- 2 video diproses serentak. Progress % dikira ikut jumlah durasi
- Tiada GPU NVIDIA? Auto fallback ke CPU `libx265` (lebih lambat)

## CLI
```
jpg2webp.exe <fail/folder> ...                [-q 60] [-j 24] [-m 4]
jpg2webp.exe --video <fail/folder> ...        [-q 26] [-j 2] [--encoder nvenc|x265]
             [--no-recursive] [--no-pause]
jpg2webp.exe --install | --uninstall
```
| Flag | Gambar | Video |
|---|---|---|
| `-q` | quality WebP (60) | CQ (26; lebih kecil = lebih cantik, fail lebih besar) |
| `-j` | thread (semua) | video serentak (2) |

## Nota
- Untuk ribuan fail, Send To **folder**. Windows ada had panjang command line.
- Fail rosak dilangkau dan disenaraikan di hujung. Fail asal tak diusik kalau gagal.
- Windows Photos perlukan "HEVC Video Extensions" untuk main HEVC. VLC dan telefon terus boleh.

Rujuk [DESIGN.md](DESIGN.md) untuk cara pemikiran.
