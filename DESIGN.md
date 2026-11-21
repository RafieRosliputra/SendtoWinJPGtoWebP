# DESIGN: cara pemikiran (rujukan masa depan)

## 1. Keperluan (Rafi, 2026-11-22)
### Gambar
1. App Windows 11, **CLI sahaja**, guna melalui **Send To** (fail dan/atau folder)
2. JPG → WebP **60%**, **kekalkan orientation**
3. WebP ganti dalam folder; JPG pindah ke `_JPG` (per folder)
4. Guna **semua core** i9-12900, tunjuk **%**
5. Push ke GitHub `RafieRosliputra/SendtoWinJPGtoWebP`, terus install di PC

### Video (ditambah kemudian, hari sama)
6. MP4 untuk **simpanan jangka panjang**, proses **laju**
7. Boleh terima **kualiti turun ~10%** (asalnya minta "25MB → 5MB"; diputuskan ikut kualiti, bukan saiz)
8. Encoder: **RTX 3060 NVENC**; codec: **HEVC 10-bit**
9. MP4 asal ke **`_MP4`**; **menu Send To berasingan**

## 2. Pilihan teknologi
| Pilihan | Keputusan |
|---|---|
| **Python + Pillow → PyInstaller .exe** ✅ | libwebp rasmi, `exif_transpose` urus orientation, mudah diubah |
| cwebp.exe | ✗ tak putar ikut EXIF → portrait jadi senget |
| ImageMagick | ✗ dependency besar |
| **ffmpeg (BtbN GPL build)** ✅ video | ada `hevc_nvenc` + `libx265` untuk fallback; di-host semula dalam release `ffmpeg-win64.zip` |

Build di **GitHub Actions windows-latest**, jadi PC tak perlu Python.

## 3. Kenapa HEVC 10-bit NVENC CQ 26
| Codec | Saiz (relatif) | Laju di PC Rafi | Serasi | Keputusan |
|---|---|---|---|---|
| H.264 NVENC | 100% | sangat laju | semua | ✗ fail besar untuk arkib |
| **HEVC NVENC** | ~55–60% | sangat laju | telefon, Mac, VLC, TV | ✅ |
| AV1 | ~45–50% | **CPU sahaja** (RTX 30 tiada encoder AV1) → lambat | baru | ✗ |

- **Kualiti tetap (CQ)**, bukan saiz tetap. Arkib perlukan kualiti konsisten; saiz ikut kandungan video. Sasaran "1/5" akan merosakkan video yang dah dimampat.
- **CQ 26 ≈ turun ~10%** (lebih kurang VMAF 90+). Boleh ubah dengan `-q`.
- **10-bit (main10)**: kurang banding/jalur pada gradient, simpan maklumat footage Sony 10-bit; kosnya hampir sifar dengan NVENC.
- `preset p5 + tune hq + spatial/temporal AQ + lookahead 32 + b_ref middle`: imbangan kualiti/laju yang baik untuk Ampere.
- `-tag:v hvc1`: supaya QuickTime/iPhone/Mac boleh main.
- **Audio**: AAC/MP3/AC3/Opus disalin terus (tiada kehilangan). LPCM (biasa pada XAVC S) → AAC 256k sebab MP4 + LPCM bermasalah dan terlalu besar.
- Hanya `0:v:0` + audio di-map. Track data Sony (timecode/rtmd) dibuang; metadata global (`creation_time`) dikekalkan.
- **Rotation**: ffmpeg auto-rotate semasa re-encode, jadi video telefon portrait kekal portrait.

## 4. Keputusan reka bentuk
- **Gambar = thread**: Pillow lepaskan GIL masa decode/transpose/encode, jadi 24 thread tanpa kos spawn process.
- **Video = 2 serentak**: NVENC sebenarnya cip berasingan; 2 job memastikan GPU sentiasa sibuk sementara CPU decode. Lebih dari tu tak tambah laju.
- **Fallback berlapis video**: NVENC + decode CUDA → NVENC + decode CPU (cth: H.264 4:2:2 10-bit Sony yang NVDEC tak sokong) → libx265 CPU.
- **Progress video** ikut `-progress pipe:1` (out_time_us), digabung ikut jumlah durasi semua video, jadi % adalah tepat walaupun saiz video tak sama.
- **Selamat data** (kedua-dua mod):
  - tulis ke fail `.part` dulu → pindah asal → `os.replace` (atomic)
  - gagal = fail asal tak diusik, `.part` dibuang
  - nama bertembung dalam `_JPG/_MP4` → tambah `_1`, `_2`…
  - video: kalau HEVC ≥ saiz asal → buang hasil, kekalkan asal (DILANGKAU)
- `mtime` asal disalin ke fail baru, supaya susunan ikut tarikh dalam Explorer/Lightroom kekal.
- **Rekursif**; folder `_JPG` dan `_MP4` dilangkau supaya run kedua tak proses semula fail lama.
- **Send To** = 2 shortcut `.lnk` ke exe yang sama (`--video` untuk menu MP4). Tiada admin diperlukan.
- `install.ps1` set `$ProgressPreference='SilentlyContinue'` sebab progress bar `Invoke-WebRequest` (PowerShell 5.1) boleh jadikan muat turun 10–50x lebih lambat. Pernah nampak macam "tiada pergerakan".

## 5. Had diketahui
- Had command line Windows ~32k aksara → untuk ribuan fail, Send To **folder**.
- RAM gambar: ~24 × 42MP serentak ≈ 3–4 GB (`-j 12` jika sempit).
- Video: hanya `.mp4`. `.mov`/`.mts` belum. Subtitle/chapter tak disalin.
- Windows Photos perlukan HEVC Video Extensions.

## 6. Idea akan datang
- `.mov` / `.mts` (Sony AVCHD)
- Pilihan CQ dalam menu Send To (cth: "arkib CQ 24" vs "kecil CQ 30")
- Resize gambar (sisi panjang 2048px) untuk web
- Log ke `_JPG\convert.log` / `_MP4\convert.log`
