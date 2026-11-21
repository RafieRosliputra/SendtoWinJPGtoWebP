"""Send To converter untuk Windows 11 (JohorStudio).

Dua mod:
  jpg2webp.exe <fail/folder> ...          JPG  -> WebP q60, JPG asal ke _JPG\\
  jpg2webp.exe --video <fail/folder> ...  MP4  -> HEVC 10-bit NVENC (CQ 26), MP4 asal ke _MP4\\
  jpg2webp.exe --install / --uninstall    pasang/buang 2 menu Send To
  (double-click tanpa arg = --install)

Lihat DESIGN.md untuk sebab setiap keputusan.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None  # gambar kamera besar (A7R II 42MP) jangan kena block

APP_NAME = "JPGtoWebP"
LNK_IMG = "JPG ke WebP (60%).lnk"
LNK_VID = "MP4 ke HEVC (kecilkan).lnk"
JPG_DIR, MP4_DIR = "_JPG", "_MP4"
SKIP_DIRS = {JPG_DIR, MP4_DIR}
IMG_EXTS = {".jpg", ".jpeg"}
VID_EXTS = {".mp4"}
AUDIO_COPY = {"aac", "mp3", "ac3", "eac3", "alac", "opus"}  # selamat disalin ke MP4
NOWIN = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


# ================================================================ umum
def collect(paths: list[str], exts: set[str], recursive: bool) -> list[Path]:
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
            if p.suffix.lower() in exts and p.parent.name not in SKIP_DIRS:
                add(p)
        elif p.is_dir():
            if recursive:
                for root, dirs, files in os.walk(p):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                    for f in sorted(files):
                        if Path(f).suffix.lower() in exts:
                            add(Path(root) / f)
            else:
                for f in sorted(p.iterdir()):
                    if f.is_file() and f.suffix.lower() in exts:
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


def move_original(src: Path, folder: str) -> Path:
    d = src.parent / folder
    d.mkdir(exist_ok=True)
    dst = unique(d / src.name)
    shutil.move(str(src), str(dst))
    return dst


def fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def bar(frac: float, t0: float, extra: str) -> str:
    frac = min(max(frac, 0.0), 1.0)
    w = 30
    fill = int(w * frac)
    el = time.time() - t0
    eta = el / frac - el if frac > 0.001 else 0
    return (f"\r[{'#' * fill}{'-' * (w - fill)}] {frac * 100:5.1f}%  {extra}"
            f"  ETA {int(eta // 60):02d}:{int(eta % 60):02d}   ")


def report(total: int, errors: list, t0: float, before: int, after: int) -> int:
    el = time.time() - t0
    print(f"\n\nSiap: {total - len(errors)}/{total} dalam {el:.1f}s")
    if before:
        pct = (1 - after / before) * 100
        print(f"Saiz: {fmt_bytes(before)} -> {fmt_bytes(after)}  (jimat {pct:.0f}%)")
    if errors:
        print(f"\n{len(errors)} gagal / dilangkau:")
        for s, e in errors:
            print(f"  {s}  ->  {e}")
    return 1 if any(not e.startswith("DILANGKAU") for _, e in errors) else 0


# ================================================================ JPG -> WebP
def convert_img(src: Path, quality: int, method: int) -> tuple[Path, str | None, int, int]:
    dst = src.with_suffix(".webp")
    tmp = dst.with_name(dst.name + ".part")
    try:
        st = src.stat()
        with Image.open(src) as im:
            im.load()
            icc = im.info.get("icc_profile")
            im = ImageOps.exif_transpose(im)  # putar pixel ikut EXIF
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
        move_original(src, JPG_DIR)
        return src, None, st.st_size, dst.stat().st_size
    except Exception as e:  # noqa: BLE001
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return src, f"{type(e).__name__}: {e}", 0, 0


def run_images(paths: list[str], quality: int, jobs: int, recursive: bool, method: int) -> int:
    print("Mengimbas gambar...")
    files = collect(paths, IMG_EXTS, recursive)
    total = len(files)
    if not total:
        print("Tiada fail JPG dijumpai.")
        return 0
    print(f"{total} JPG | WebP quality {quality} | {jobs} thread\n")
    t0 = time.time()
    done, errors, before, after = 0, [], 0, 0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = [ex.submit(convert_img, f, quality, method) for f in files]
        for fu in as_completed(futs):
            src, err, b, a = fu.result()
            done += 1
            before += b
            after += a
            if err:
                errors.append((src, err))
            el = time.time() - t0
            sys.stdout.write(bar(done / total, t0, f"{done}/{total}  {done / el if el else 0:5.1f} img/s"))
            sys.stdout.flush()
    return report(total, errors, t0, before, after)


# ================================================================ MP4 -> HEVC
def find_tool(name: str) -> str | None:
    base = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    for c in (base / f"{name}.exe", base / name):
        if c.is_file():
            return str(c)
    return shutil.which(name)


def probe(ffprobe: str, src: Path) -> tuple[float, str | None]:
    r = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(src)],
        capture_output=True, text=True, creationflags=NOWIN)
    if r.returncode:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "ffprobe gagal")
    j = json.loads(r.stdout)
    dur = float(j.get("format", {}).get("duration") or 0)
    acodec = next((s.get("codec_name") for s in j.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not any(s.get("codec_type") == "video" for s in j.get("streams", [])):
        raise RuntimeError("tiada stream video")
    return dur, acodec


def video_args(enc: str, cq: int, hwdec: bool) -> tuple[list[str], list[str]]:
    pre = ["-hwaccel", "cuda"] if hwdec else []
    if enc == "nvenc":
        v = ["-c:v", "hevc_nvenc", "-preset", "p5", "-tune", "hq", "-profile:v", "main10",
             "-pix_fmt", "p010le", "-rc", "vbr", "-cq", str(cq), "-b:v", "0",
             "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-bf", "3",
             "-b_ref_mode", "middle"]
    else:  # libx265 fallback (tiada GPU NVIDIA)
        v = ["-c:v", "libx265", "-preset", "fast", "-crf", str(cq - 2), "-profile:v", "main10",
             "-pix_fmt", "yuv420p10le", "-x265-params", "log-level=error"]
    return pre, v + ["-tag:v", "hvc1"]


class VidProgress:
    def __init__(self, total_sec: float, nfiles: int):
        self.total = max(total_sec, 0.001)
        self.nfiles = nfiles
        self.done_sec = 0.0
        self.cur: dict[int, float] = {}
        self.finished = 0
        self.lock = threading.Lock()
        self.t0 = time.time()

    def update(self, key: int, sec: float | None = None, finish_sec: float | None = None) -> None:
        with self.lock:
            if finish_sec is not None:
                self.cur.pop(key, None)
                self.done_sec += finish_sec
                self.finished += 1
            elif sec is not None:
                self.cur[key] = sec
            pos = self.done_sec + sum(self.cur.values())
            el = time.time() - self.t0
            speed = pos / el if el > 0 else 0
            sys.stdout.write(bar(pos / self.total, self.t0,
                                 f"video {self.finished}/{self.nfiles}  {speed:4.1f}x"))
            sys.stdout.flush()


def encode(ffmpeg: str, src: Path, tmp: Path, dur: float, acodec: str | None,
           enc: str, cq: int, hwdec: bool, key: int, prog: VidProgress) -> str | None:
    pre, vargs = video_args(enc, cq, hwdec)
    if acodec is None:
        aargs: list[str] = []
    elif acodec in AUDIO_COPY:
        aargs = ["-c:a", "copy"]
    else:  # cth: LPCM dari kamera Sony
        aargs = ["-c:a", "aac", "-b:a", "256k"]
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y", *pre, "-i", str(src),
           "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "0",
           *vargs, *aargs, "-movflags", "+faststart+use_metadata_tags",
           "-progress", "pipe:1", "-nostats", "-loglevel", "error", "-f", "mp4", str(tmp)]
    with tempfile.TemporaryFile() as errf:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf, text=True,
                             creationflags=NOWIN)
        assert p.stdout
        for line in p.stdout:
            if line.startswith("out_time_us="):
                try:
                    prog.update(key, sec=min(int(line.split("=")[1]) / 1e6, dur))
                except ValueError:
                    pass
        p.wait()
        if p.returncode:
            errf.seek(0)
            msg = errf.read().decode(errors="replace").strip().splitlines()
            return msg[-1] if msg else f"ffmpeg exit {p.returncode}"
    return None


def convert_vid(ffmpeg: str, ffprobe: str, src: Path, enc: str, cq: int,
                key: int, prog: VidProgress, durs: dict) -> tuple[Path, str | None, int, int]:
    tmp = src.with_name(src.stem + ".hevc.part.mp4")
    dur = durs.get(src, 0.0)
    try:
        st = src.stat()
        _, acodec = probe(ffprobe, src)
        err = None
        # cuba: NVENC+decode GPU -> NVENC+decode CPU -> libx265
        attempts = [("nvenc", True), ("nvenc", False), ("x265", False)] if enc == "nvenc" else [("x265", False)]
        for e, hw in attempts:
            prog.update(key, sec=0)
            err = encode(ffmpeg, src, tmp, dur, acodec, e, cq, hw, key, prog)
            if not err:
                break
        if err:
            raise RuntimeError(err)
        new = tmp.stat().st_size
        if new >= st.st_size:
            tmp.unlink(missing_ok=True)
            prog.update(key, finish_sec=dur)
            return src, f"DILANGKAU: HEVC tak lebih kecil ({fmt_bytes(new)} >= {fmt_bytes(st.st_size)})", 0, 0
        move_original(src, MP4_DIR)
        os.replace(tmp, src)  # nama sama, kandungan HEVC
        os.utime(src, (st.st_atime, st.st_mtime))
        prog.update(key, finish_sec=dur)
        return src, None, st.st_size, new
    except Exception as e:  # noqa: BLE001
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        prog.update(key, finish_sec=dur)
        return src, f"{type(e).__name__}: {e}", 0, 0


def run_videos(paths: list[str], cq: int, jobs: int, recursive: bool, enc: str) -> int:
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        print("ffmpeg.exe / ffprobe.exe tak dijumpai. Jalankan semula install.ps1.")
        return 2
    print("Mengimbas video...")
    files = collect(paths, VID_EXTS, recursive)
    if not files:
        print("Tiada fail MP4 dijumpai.")
        return 0
    durs: dict[Path, float] = {}
    for f in files:
        try:
            durs[f] = probe(ffprobe, f)[0]
        except Exception:  # noqa: BLE001
            durs[f] = 0.0
    total_sec = sum(durs.values())
    print(f"{len(files)} MP4 | {int(total_sec // 60)}m{int(total_sec % 60)}s | "
          f"HEVC 10-bit {'NVENC' if enc == 'nvenc' else 'x265'} CQ {cq} | {jobs} serentak\n")
    prog = VidProgress(total_sec, len(files))
    errors, before, after = [], 0, 0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = [ex.submit(convert_vid, ffmpeg, ffprobe, f, enc, cq, i, prog, durs)
                for i, f in enumerate(files)]
        for fu in as_completed(futs):
            src, err, b, a = fu.result()
            before += b
            after += a
            if err:
                errors.append((src, err))
    return report(len(files), errors, prog.t0, before, after)


# ================================================================ install
def _ps(cmd: str) -> None:
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], check=True)


def _q(s: object) -> str:
    return str(s).replace("'", "''")


def install() -> None:
    exe = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
    dest_dir = Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "jpg2webp.exe"
    if exe != dest:
        shutil.copy2(exe, dest)
        for t in ("ffmpeg.exe", "ffprobe.exe"):
            if (exe.parent / t).is_file() and exe.parent != dest_dir:
                shutil.copy2(exe.parent / t, dest_dir / t)
    sendto = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "SendTo"
    for lnk, args, desc in ((LNK_IMG, "", "Convert JPG ke WebP 60%"),
                            (LNK_VID, "--video", "Kecilkan MP4 ke HEVC 10-bit")):
        _ps("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{l}');"
            "$s.TargetPath='{e}';$s.Arguments='{a}';$s.WorkingDirectory='{w}';"
            "$s.IconLocation='{e},0';$s.Description='{d}';$s.Save()".format(
                l=_q(sendto / lnk), e=_q(dest), a=args, w=_q(dest_dir), d=desc))
    print(f"Dipasang: {dest}")
    print(f"Send To : {LNK_IMG[:-4]}  |  {LNK_VID[:-4]}")
    if not (dest_dir / "ffmpeg.exe").is_file():
        print("AMARAN: ffmpeg.exe tiada di folder pasang -> menu MP4 tak akan jalan.")


def uninstall() -> None:
    sendto = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "SendTo"
    for lnk in (LNK_IMG, LNK_VID):
        (sendto / lnk).unlink(missing_ok=True)
    print(f"Shortcut dibuang. Padam folder ini secara manual jika mahu: "
          f"{Path(os.environ['LOCALAPPDATA']) / APP_NAME}")


# ================================================================ main
def main() -> int:
    ap = argparse.ArgumentParser(prog="jpg2webp", description="JPG->WebP & MP4->HEVC, asal ke _JPG/_MP4")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--video", action="store_true", help="mod MP4 -> HEVC")
    ap.add_argument("-q", "--quality", type=int, default=None,
                    help="WebP quality (default 60) / video CQ (default 26, kecil=lebih cantik)")
    ap.add_argument("-j", "--jobs", type=int, default=None,
                    help="gambar: default semua thread; video: default 2 serentak")
    ap.add_argument("-m", "--method", type=int, default=4, help="WebP 0=laju .. 6=kecil")
    ap.add_argument("--encoder", choices=["nvenc", "x265"], default="nvenc")
    ap.add_argument("--no-recursive", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-pause", action="store_true")
    a = ap.parse_args()

    if a.uninstall:
        uninstall()
        rc = 0
    elif a.install or not a.paths:
        install()
        rc = 0
    elif a.video:
        rc = run_videos(a.paths, a.quality or 26, max(1, a.jobs or 2), not a.no_recursive, a.encoder)
    else:
        rc = run_images(a.paths, a.quality or 60, max(1, a.jobs or os.cpu_count() or 8),
                        not a.no_recursive, a.method)
    if not a.no_pause and sys.stdin and sys.stdin.isatty():
        try:
            input("\nTekan Enter untuk tutup...")
        except EOFError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
