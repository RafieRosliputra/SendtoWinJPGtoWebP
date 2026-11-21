# SendtoWinJPGtoWebP

CLI Windows 11: right-click gambar/folder → **Send to → JPG ke WebP (60%)**.

## Apa ia buat
- `.jpg` / `.jpeg` → `.webp` quality **60**, dalam folder yang sama
- Orientation EXIF diaplikasi (gambar portrait kekal portrait)
- EXIF (kamera, tarikh), ICC profile & tarikh modified dikekalkan
- JPG asal dipindah ke `_JPG\` dalam folder gambar itu
- Folder: rekursif, setiap subfolder dapat `_JPG\` sendiri
- Guna semua thread CPU (i9-12900 = 24 thread)
- Progress bar `%`, img/s, ETA dalam console

## Pasang
**Cara 1 (PowerShell, satu baris):**
```powershell
irm https://raw.githubusercontent.com/RafieRosliputra/SendtoWinJPGtoWebP/main/install.ps1 | iex
```
**Cara 2:** muat turun `jpg2webp.exe` dari [Releases](../../releases/tag/latest) → double-click (auto pasang Send To).

Lokasi pasang: `%LOCALAPPDATA%\JPGtoWebP\jpg2webp.exe`
Shortcut: `%APPDATA%\Microsoft\Windows\SendTo\JPG ke WebP (60%).lnk`

## CLI
```
jpg2webp.exe <fail/folder> [...] [-q 60] [-j 24] [-m 4] [--no-recursive] [--no-pause]
jpg2webp.exe --install | --uninstall
```
| Flag | Default | Fungsi |
|---|---|---|
| `-q` | 60 | quality WebP |
| `-j` | semua thread | bilangan thread |
| `-m` | 4 | 0 = laju … 6 = fail kecil |
| `--no-recursive` | off | jangan masuk subfolder |
| `--no-pause` | off | jangan tunggu Enter di hujung |

## Nota
- Pilih **folder** bila gambar banyak (ribuan fail) — Windows ada had panjang command line (~32k aksara) bila hantar banyak fail satu-satu.
- Fail rosak dilangkau & disenarai di hujung; JPG asal tak diusik jika gagal.

Rujuk [DESIGN.md](DESIGN.md) untuk cara pemikiran.
