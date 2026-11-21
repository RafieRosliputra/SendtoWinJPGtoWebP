"""JPG -> WebP (Send To) untuk Windows 11.

Guna:
  jpg2webp.exe <fail/folder> [...]   convert (Send To hantar path ke sini)
  jpg2webp.exe --install             pasang ke %LOCALAPPDATA% + shortcut Send To
  jpg2webp.exe --uninstall           buang shortcut + fail pasangan
  (double-click tanpa arg = --install)

Peraturan:
  - .jpg/.jpeg (huruf besar/kecil) -> .webp quality 60 dalam folder sama
  - orientation EXIF diaplikasi pada pixel (gambar tak senget), tag orientation dibuang
  - EXIF lain + ICC profile + tarikh modified dikekalkan
  - JPG asal dipindah ke <folder gambar>/_JPG/ (folder _JPG tak diproses semula)
  - folder diproses rekursif, setiap subfolder dapat _JPG sendiri
  - semua thread CPU digunakan (Pillow lepaskan GIL semasa decode/encode)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None  # gambar kamera besar (A7R II 42MP) jangan kena block

APP_NAME = "JPGtoWebP"
SENDTO_NAME = "JPG ke WebP (60%).lnk"
JPG_DIR = "_JPG"
EXTS = {".jpg", ".jpeg"}


# ---------------------------------------------------------------- scan
def collect(paths: list[str], recursive: bool) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(p)

    for raw in paths:
        p = Path(raw.strip('"'))
        if p.is_file():
            if p.suffix.lower() in EXTS and p.parent.name != JPG_DIR:
                add(p)
        elif p.is_dir():
            if recursive:
                for root, dirs, files in os.walk(p):
                    dirs[:] = [d for d in dirs if d != JPG_DIR]
                    for f in files:
                        if Path(f).suffix.lower() in EXTS:
                            add(Path(root) / f)
            else:
                for f in p.iterdir():
                    if f.is_file() and f.suffix.lower() in EXTS:
                        add(f)
    return out


def unique(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        c = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not c.exists():
            return c
        i += 1


# ---------------------------------------------------------------- convert
def convert(src: Path, quality: int, method: int) -> tuple[Path, str | None]:
    dst = src.with_suffix(".webp")
    tmp = dst.with_name(dst.name + ".part")
    try:
        st = src.stat()
        with Image.open(src) as im:
            im.load()
            icc = im.info.get("icc_profile")
            im = ImageOps.exif_transpose(im)  # putar pixel ikut EXIF, buang tag orientation
            exif = im.getexif()
            exif.pop(0x0112, None)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            kw = {"quality": quality, "method": method, "exif": exif.tobytes()}
            if icc:
                kw["icc_profile"] = icc
            im.save(tmp, "WEBP", **kw)
        os.replace(tmp, dst)
        os.utime(dst, (st.st_atime, st.st_mtime))
        jdir = src.parent / JPG_DIR
        jdir.mkdir(exist_ok=True)
        shutil.move(str(src), str(unique(jdir / src.name)))
        return src, None
    except Exception as e:  # noqa: BLE001
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return src, f"{type(e).__name__}: {e}"


def bar(done: int, total: int, t0: float, errs: int) -> str:
    pct = done / total * 100 if total else 100
    w = 30
    fill = int(w * done / total) if total else w
    el = time.time() - t0
    rate = done / el if el > 0 else 0
    eta = (total - done) / rate if rate > 0 else 0
    e = f" | gagal {errs}" if errs else ""
    return (f"\r[{'#' * fill}{'-' * (w - fill)}] {pct:5.1f}%  {done}/{total}"
            f"  {rate:5.1f} img/s  ETA {int(eta // 60):02d}:{int(eta % 60):02d}{e}   ")


def run(paths: list[str], quality: int, jobs: int, recursive: bool, method: int) -> int:
    print("Mengimbas fail...")
    files = collect(paths, recursive)
    total = len(files)
    if not total:
        print("Tiada fail JPG dijumpai.")
        return 0
    print(f"{total} JPG | quality {quality} | {jobs} thread\n")
    t0 = time.time()
    done, errors = 0, []
    sys.stdout.write(bar(0, total, t0, 0))
    sys.stdout.flush()
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = [ex.submit(convert, f, quality, method) for f in files]
        for fu in as_completed(futs):
            src, err = fu.result()
            done += 1
            if err:
                errors.append((src, err))
            sys.stdout.write(bar(done, total, t0, len(errors)))
            sys.stdout.flush()
    el = time.time() - t0
    print(f"\n\nSiap: {total - len(errors)}/{total} dalam {el:.1f}s")
    if errors:
        print(f"\n{len(errors)} gagal:")
        for s, e in errors:
            print(f"  {s}  ->  {e}")
    return 1 if errors else 0


# ---------------------------------------------------------------- install
def _ps(cmd: str) -> None:
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], check=True)


def install() -> None:
    exe = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
    dest_dir = Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "jpg2webp.exe"
    if exe != dest:
        shutil.copy2(exe, dest)
    sendto = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "SendTo" / SENDTO_NAME
    _ps(
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath='{exe}';$s.WorkingDirectory='{wd}';"
        "$s.IconLocation='{exe},0';$s.Description='Convert JPG ke WebP 60%';$s.Save()".format(
            lnk=str(sendto).replace("'", "''"), exe=str(dest).replace("'", "''"),
            wd=str(dest_dir).replace("'", "''"))
    )
    print(f"Dipasang: {dest}\nSend To : {sendto}\n\nRight-click gambar/folder > Send to > JPG ke WebP (60%)")


def uninstall() -> None:
    sendto = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "SendTo" / SENDTO_NAME
    sendto.unlink(missing_ok=True)
    d = Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    print(f"Shortcut dibuang. Padam folder ini secara manual jika mahu: {d}")


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(prog="jpg2webp", description="JPG -> WebP, JPG asal ke _JPG")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("-q", "--quality", type=int, default=60)
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 8)
    ap.add_argument("-m", "--method", type=int, default=4, help="0=laju .. 6=kecil (default 4)")
    ap.add_argument("--no-recursive", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-pause", action="store_true", help="jangan tunggu Enter di hujung")
    a = ap.parse_args()

    if a.uninstall:
        uninstall()
        rc = 0
    elif a.install or not a.paths:
        install()
        rc = 0
    else:
        rc = run(a.paths, a.quality, max(1, a.jobs), not a.no_recursive, a.method)
    if not a.no_pause and sys.stdin and sys.stdin.isatty():
        try:
            input("\nTekan Enter untuk tutup...")
        except EOFError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
