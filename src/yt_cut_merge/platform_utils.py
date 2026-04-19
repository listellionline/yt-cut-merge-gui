import os
import platform
import shutil
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_linux() -> bool:
    return platform.system().lower() == "linux"


def is_macos() -> bool:
    return platform.system().lower() == "darwin"


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def find_in_path(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def find_ffmpeg() -> Optional[str]:
    root = get_project_root()

    if is_windows():
        local = root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
        if local.exists():
            return str(local)

    return find_in_path("ffmpeg")


def find_ffprobe() -> Optional[str]:
    root = get_project_root()

    if is_windows():
        local = root / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
        if local.exists():
            return str(local)

    return find_in_path("ffprobe")


def find_ytdlp() -> Optional[str]:
    root = get_project_root()

    if is_windows():
        local = root / "tools" / "yt-dlp.exe"
        if local.exists():
            return str(local)

    user_local = Path.home() / ".local" / "bin" / "yt-dlp"
    if user_local.exists():
        return str(user_local)

    return find_in_path("yt-dlp")


def default_workdir() -> Path:
    if is_windows():
        workdir = Path.home() / "Videos" / "yt-cut-merge"
    else:
        workdir = Path.home() / ".local" / "share" / "yt-cut-merge" / "video"

    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def patch_runtime_path() -> None:
    root = get_project_root()

    if is_windows():
        ffmpeg_bin = root / "tools" / "ffmpeg" / "bin"
        tools_dir = root / "tools"

        parts = [
            str(ffmpeg_bin),
            str(tools_dir),
            os.environ.get("PATH", ""),
        ]
        os.environ["PATH"] = os.pathsep.join(p for p in parts if p)


def debug_tools_info() -> dict[str, Optional[str]]:
    return {
        "platform": platform.system(),
        "project_root": str(get_project_root()),
        "ffmpeg": find_ffmpeg(),
        "ffprobe": find_ffprobe(),
        "yt-dlp": find_ytdlp(),
        "workdir": str(default_workdir()),
    }
