from __future__ import annotations

import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .platform_utils import find_ffmpeg, find_ffprobe, find_ytdlp


LogFn = Callable[[str], None]
ProgressFn = Callable[[str, Optional[float]], None]

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


@dataclass
class JobConfig:
    url: Optional[str]
    clipfile: Optional[Path]
    ranges_csv: Optional[str]
    source_file: Optional[Path]
    output_file: Path
    workdir: Path
    fade: float = 0.0
    reencode: bool = True
    dry_run: bool = False
    auto_clean: bool = False
    browser: Optional[str] = None


def run_cmd(
    cmd: List[str],
    log: LogFn,
    dry_run: bool = False,
    capture: bool = False,
) -> Optional[subprocess.CompletedProcess]:
    if dry_run:
        log("[dry-run] " + " ".join(shlex.quote(c) for c in cmd))
        return None

    log("$ " + " ".join(shlex.quote(c) for c in cmd))
    return subprocess.run(cmd, text=True, check=True, capture_output=capture)


def parse_hms(value: str) -> int:
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def validate_range(value: str) -> bool:
    try:
        start, end = value.split("-", 1)
        return parse_hms(end) > parse_hms(start)
    except Exception:
        return False


def load_ranges(clipfile: Optional[Path], ranges_csv: Optional[str]) -> List[str]:
    ranges: List[str] = []

    def normalize_range(line: str) -> str:
        start, end = [x.strip() for x in line.split("-", 1)]
        normalized = f"{start}-{end}"
        if not validate_range(normalized):
            raise ValueError(f"Range non valido: {line}")
        return normalized

    if clipfile:
        if not clipfile.is_file():
            raise FileNotFoundError(f"Clip file non trovato: {clipfile}")

        for raw in clipfile.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ranges.append(normalize_range(line))
    else:
        if not ranges_csv:
            raise ValueError("Nessun range specificato")

        for raw in ranges_csv.split(","):
            line = raw.strip()
            ranges.append(normalize_range(line))

    if not ranges:
        raise ValueError("Nessuna clip valida")

    return ranges


def list_video_files(workdir: Path) -> List[Path]:
    return sorted(
        [p for p in workdir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS],
        key=lambda p: p.name.lower(),
    )


def unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    i = 1
    while True:
        candidate = parent / f"{stem}_{i:03d}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def expected_source_from_url(url: str, workdir: Path, dry_run: bool, log: LogFn) -> Optional[Path]:
    ytdlp = find_ytdlp()
    if not ytdlp:
        return None

    cmd = [
        ytdlp,
        "--no-warnings",
        "--skip-download",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-o",
        "%(title)s [%(id)s].%(ext)s",
        "--print",
        "filename",
        url,
    ]

    if dry_run:
        log("[dry-run] " + " ".join(shlex.quote(c) for c in cmd))
        return workdir / "video [id].mp4"

    try:
        res = run_cmd(cmd, log=log, capture=True)
        assert res is not None
        name = res.stdout.strip().splitlines()[0]
        return workdir / name
    except Exception:
        return None


def ffprobe_duration(path: Path, dry_run: bool, fallback: float, log: LogFn) -> float:
    ffprobe = find_ffprobe()
    if not ffprobe:
        raise RuntimeError("ffprobe non trovato")

    if dry_run:
        return fallback

    res = run_cmd(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        log=log,
        capture=True,
    )
    assert res is not None
    return float(res.stdout.strip())


def build_xfade_filter(durations: List[float], fade: float) -> str:
    safe_fade = fade
    for d in durations:
        safe_fade = min(safe_fade, max(0.1, d / 3.0))

    v_prev = "[0:v]"
    a_prev = "[0:a]"
    offset = max(0.0, durations[0] - safe_fade)
    parts: List[str] = []

    for i in range(1, len(durations)):
        v_in = f"[{i}:v]"
        a_in = f"[{i}:a]"
        v_out = f"[v{i}]"
        a_out = f"[a{i}]"

        parts.append(f"{v_prev}{v_in}xfade=transition=fade:duration={safe_fade}:offset={offset}{v_out}")
        parts.append(f"{a_prev}{a_in}acrossfade=d={safe_fade}{a_out}")

        v_prev = v_out
        a_prev = a_out

        if i < len(durations) - 1:
            offset += durations[i] - safe_fade

    return ";".join(parts)


def ensure_tools(source_file: Optional[Path]) -> None:
    if not find_ffmpeg():
        raise RuntimeError("ffmpeg non trovato")
    if not find_ffprobe():
        raise RuntimeError("ffprobe non trovato")
    if source_file is None and not find_ytdlp():
        raise RuntimeError("yt-dlp non trovato")


def resolve_source(
    cfg: JobConfig,
    log: LogFn,
    progress: Optional[ProgressFn] = None,
) -> tuple[Path, bool]:
    def report(status: str, percent: Optional[float]) -> None:
        if progress:
            progress(status, percent)

    if cfg.source_file:
        if not cfg.source_file.is_file():
            raise FileNotFoundError(f"File sorgente non trovato: {cfg.source_file}")
        return cfg.source_file, False

    if not cfg.url:
        raise ValueError("Serve un URL o un file sorgente")

    expected = expected_source_from_url(cfg.url, cfg.workdir, cfg.dry_run, log)
    if expected and expected.exists():
        log(f"Trovato file già presente: {expected}")
        report("Uso file già presente nella cartella di lavoro", 5.0)
        return expected, False

    ytdlp = find_ytdlp()
    if not ytdlp:
        raise RuntimeError("yt-dlp non trovato")

    target = expected if expected else (cfg.workdir / "source.%(ext)s")

    report("Download sorgente da URL...", 2.0)
    log("Download sorgente da URL in corso...")

    cmd = [
        ytdlp,
        "--newline",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-o",
        str(target),
        cfg.url,
    ]

    try:
        run_cmd(cmd, log=log, dry_run=cfg.dry_run)
    except subprocess.CalledProcessError:
        if not cfg.browser:
            raise RuntimeError("Download fallito; prova a usare un browser per i cookie")

        report(f"Retry download con cookie browser: {cfg.browser}", 3.0)

        cmd = [
            ytdlp,
            "--newline",
            "--cookies-from-browser",
            cfg.browser,
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(target),
            cfg.url,
        ]
        run_cmd(cmd, log=log, dry_run=cfg.dry_run)

    if cfg.dry_run:
        return (expected if expected else cfg.workdir / "source.mp4"), True

    if "%(ext)s" in str(target):
        matches = [p for p in cfg.workdir.iterdir() if p.is_file() and p.name.startswith("source.")]
        if not matches:
            raise RuntimeError("File scaricato non trovato")
        return sorted(matches)[0], True

    if not target.exists():
        raise RuntimeError("File scaricato non trovato")

    return target, True


def process_job(
    cfg: JobConfig,
    log: LogFn,
    progress: Optional[ProgressFn] = None,
) -> Path:
    def report(status: str, percent: Optional[float]) -> None:
        if progress:
            progress(status, percent)

    ensure_tools(cfg.source_file)
    ranges = load_ranges(cfg.clipfile, cfg.ranges_csv)

    ffmpeg = find_ffmpeg()
    assert ffmpeg is not None

    cfg.workdir.mkdir(parents=True, exist_ok=True)
    cfg.output_file = unique_output_path(cfg.output_file)

    report("Preparazione...", 0.0)

    source, downloaded_now = resolve_source(cfg, log, progress=progress)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        clips: List[Path] = []
        durations: List[float] = []

        total = len(ranges)

        for i, rng in enumerate(ranges, start=1):
            start, end = [x.strip() for x in rng.split("-", 1)]
            clip = tmpdir / f"clip_{i:03d}.mp4"

            base_progress = 10.0 + ((i - 1) / total) * 60.0
            report(f"Taglio clip {i}/{total}: {start} - {end}", base_progress)

            run_cmd(
                [
                    ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-stats",
                    "-ss",
                    start,
                    "-to",
                    end,
                    "-i",
                    str(source),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    str(clip),
                ],
                log=log,
                dry_run=cfg.dry_run,
            )

            fallback = float(parse_hms(end) - parse_hms(start))
            durations.append(ffprobe_duration(clip, cfg.dry_run, fallback, log))
            clips.append(clip)

            done_progress = 10.0 + (i / total) * 60.0
            report(f"Clip {i}/{total} completata", done_progress)

        if len(clips) == 1:
            report("Scrittura output finale...", 95.0)
            if cfg.dry_run:
                log(f"[dry-run] output finale: {cfg.output_file}")
            else:
                cfg.output_file.write_bytes(clips[0].read_bytes())
            report("Completato", 100.0)
            return cfg.output_file

        listfile = tmpdir / "lista.txt"
        if not cfg.dry_run:
            listfile.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")

        if cfg.fade > 0:
            report("Merge finale con fade...", 80.0)
            filter_complex = build_xfade_filter(durations, cfg.fade)
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-stats"]
            for c in clips:
                cmd.extend(["-i", str(c)])
            cmd.extend(
                [
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    f"[v{len(clips)-1}]",
                    "-map",
                    f"[a{len(clips)-1}]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    str(cfg.output_file),
                ]
            )
            run_cmd(cmd, log=log, dry_run=cfg.dry_run)
        else:
            if cfg.reencode:
                report("Merge finale con ricodifica...", 80.0)
                run_cmd(
                    [
                        ffmpeg,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-stats",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(listfile),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-crf",
                        "18",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        str(cfg.output_file),
                    ],
                    log=log,
                    dry_run=cfg.dry_run,
                )
            else:
                report("Merge finale senza ricodifica...", 80.0)
                run_cmd(
                    [
                        ffmpeg,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-stats",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(listfile),
                        "-c",
                        "copy",
                        str(cfg.output_file),
                    ],
                    log=log,
                    dry_run=cfg.dry_run,
                )

    if cfg.auto_clean and downloaded_now and source.exists() and not cfg.dry_run:
        source.unlink(missing_ok=True)

    report("Completato", 100.0)
    return cfg.output_file
