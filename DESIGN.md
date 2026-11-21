# DESIGN — cara pemikiran (rujukan masa depan)

## 1. Keperluan asal (Rafi, 2026-11-22)
1. App Windows 11, **CLI sahaja**
2. Pilih gambar dan/atau folder → right-click → **Send To**
3. JPG → WebP **60%**, **kekalkan orientation**
4. WebP ganti gambar dalam folder; JPG pindah ke `_JPG` (per folder)
5. Guna **semua core** i9-12900
6. Tunjuk **%** siap
7. Push ke GitHub `RafieRosliputra/SendtoWinJPGtoWebP`
8. Terus install + masuk Send To di PC

## 2. Pilihan teknologi
| Pilihan | Kenapa ya / tidak |
|---|---|
| **Python + Pillow → PyInstaller .exe** ✅ | Pillow guna libwebp (encoder rasmi Google), `ImageOps.exif_transpose` urus orientation, mudah diselenggara |
| cwebp.exe (Google) | Laju, tapi **tak putar ikut EXIF** → gambar portrait jadi senget |
| ImageMagick | Ada `-auto-orient`, tapi dependency besar (~100MB), perlu install |
| Rust/Go | Encoder WebP lossy perlu libwebp C (cgo/libwebp-sys) — build lebih rumit, faedah kecil |

Build `.exe` dibuat di **GitHub Actions (windows-latest)** — tak perlu Python di PC.

## 3. Keputusan reka bentuk
- **Thread, bukan process**: Pillow lepaskan GIL masa decode JPEG, transpose & encode WebP → `ThreadPoolExecutor` dapat guna semua 24 thread tanpa kos spawn process (lambat di Windows, lebih-lebih lagi dengan PyInstaller onefile).
- **Orientation**: pixel diputar (`exif_transpose`) dan tag `0x0112` dibuang → semua viewer/web papar betul, tak bergantung pada sokongan EXIF browser.
- **Metadata**: EXIF lain + ICC dikekalkan; `mtime` JPG disalin ke WebP supaya susunan ikut tarikh dalam Explorer/Lightroom tak rosak.
- **Selamat data**:
  - tulis ke `nama.webp.part` → `os.replace` (atomic) → baru pindah JPG
  - jika gagal, `.part` dibuang dan JPG **tak diusik**
  - nama bertembung dalam `_JPG` → tambah `_1`, `_2`…
- **Rekursif**: folder diimbas penuh; folder `_JPG` dilangkau supaya run kedua tak convert balik fail lama.
- **Send To**: shortcut `.lnk` dalam `shell:sendto` → Explorer hantar semua path terpilih sebagai argumen ke satu proses.
- **Install sendiri**: double-click exe tanpa argumen = `--install` (salin ke `%LOCALAPPDATA%\JPGtoWebP` + buat shortcut). Tiada admin diperlukan.
- **Console kekal terbuka** di hujung (`Tekan Enter`) supaya keputusan & senarai gagal boleh dibaca.
- `Image.MAX_IMAGE_PIXELS = None` — gambar 42MP+ (Sony A7R II) tak dianggap "decompression bomb".

## 4. Had diketahui
- Had command line Windows ~32k aksara → untuk ribuan fail, Send To **folder**, bukan fail.
- RAM: ~24 gambar 42MP serentak ≈ 3–4 GB. Guna `-j 12` jika RAM sempit.
- Hanya JPG; HEIC/PNG/RAW tak disentuh.

## 5. Idea akan datang
- Pilihan quality dalam menu Send To (cth: 60 / 80 / 90 shortcut berasingan dengan `-q`)
- Resize (cth: sisi panjang 2048px) untuk web
- Log fail ke `_JPG\convert.log`
