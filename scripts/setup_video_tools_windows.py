#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
FFMPEG_DIR = TOOLS_DIR / "ffmpeg"
YTDLP_PATH = TOOLS_DIR / "yt-dlp.exe"


def log(msg: str) -> None:
    print(msg, flush=True)


def download(url: str, dest: Path) -> None:
    log(f"Scarico: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def setup_ytdlp() -> None:
    if YTDLP_PATH.exists():
        log(f"yt-dlp già presente: {YTDLP_PATH}")
        return

    download(
        "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
        YTDLP_PATH,
    )
    log(f"yt-dlp pronto: {YTDLP_PATH}")


def setup_ffmpeg() -> None:
    ffmpeg_exe = FFMPEG_DIR / "bin" / "ffmpeg.exe"
    ffprobe_exe = FFMPEG_DIR / "bin" / "ffprobe.exe"

    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        log(f"FFmpeg già presente: {FFMPEG_DIR}")
        return

    zip_path = TOOLS_DIR / "ffmpeg.zip"
    extract_dir = TOOLS_DIR / "_ffmpeg_extract"

    download(
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        zip_path,
    )

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    log("Estraggo FFmpeg...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    candidates = [p for p in extract_dir.iterdir() if p.is_dir() and p.name.startswith("ffmpeg-")]
    if not candidates:
        raise RuntimeError("Archivio FFmpeg non riconosciuto")

    extracted_root = candidates[0]

    if FFMPEG_DIR.exists():
        shutil.rmtree(FFMPEG_DIR)

    shutil.move(str(extracted_root), str(FFMPEG_DIR))

    zip_path.unlink(missing_ok=True)
    shutil.rmtree(extract_dir, ignore_errors=True)

    log(f"FFmpeg pronto: {FFMPEG_DIR}")


def main() -> int:
    if sys.platform != "win32":
        log("Questo setup è pensato per Windows.")

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    setup_ytdlp()
    setup_ffmpeg()

    log("")
    log("Installazione completata.")
    log(f"yt-dlp: {YTDLP_PATH}")
    log(f"ffmpeg: {FFMPEG_DIR / 'bin' / 'ffmpeg.exe'}")
    log(f"ffprobe: {FFMPEG_DIR / 'bin' / 'ffprobe.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
