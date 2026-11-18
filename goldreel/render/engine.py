"""Frame rendering engine with raw frame piping to FFmpeg.

Strictly follows docs/GEMINI.md Section 2:
"Never hold all frames in memory, pipe frames to FFmpeg.
Peak RAM under 3 GB."
"""

import logging
import subprocess
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from goldreel.facts.models import FactTable
from goldreel.render.templates.base import BaseTemplate
from goldreel.script.models import GeneratedScript

logger = logging.getLogger(__name__)


@dataclass
class RenderStats:
    total_frames: int
    duration_sec: float
    fps: int
    elapsed_time_sec: float
    fps_render_speed: float
    peak_ram_mb: float
    output_path: Path


class RenderEngine:
    """Renders video by drawing frames and streaming directly to FFmpeg stdin."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def render(
        self,
        template: BaseTemplate,
        fact_table: FactTable,
        script: GeneratedScript,
        output_path: Path | str,
        fps: int = 30,
        audio_path: Path | str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> RenderStats:
        """Render entire video from template and stream frames to FFmpeg."""
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        timeline = template.plan(fact_table, script)
        timeline.fps = fps
        total_frames = timeline.total_frames
        w, h = timeline.width, timeline.height

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{w}x{h}",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(fps),
            "-i",
            "-",  # Read video frames from stdin
        ]

        if audio_path and Path(audio_path).exists():
            cmd.extend(
                [
                    "-i",
                    str(Path(audio_path).resolve()),
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                ]
            )

        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                str(out_file),
            ]
        )

        logger.info("Starting FFmpeg pipeline: %s", " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            for frame_idx in range(total_frames):
                t = timeline.time_at_frame(frame_idx)
                # Render single frame
                frame_img = template.draw(t)
                # Pipe raw RGB bytes directly to FFmpeg stdin
                proc.stdin.write(frame_img.tobytes())
                del frame_img  # Explicitly release image buffer

                if progress_callback and frame_idx % 30 == 0:
                    progress_callback(frame_idx, total_frames)

            proc.stdin.close()
            proc.wait()

            if proc.returncode != 0:
                stderr_output = proc.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"FFmpeg render failed with exit code {proc.returncode}: {stderr_output}"
                )

        finally:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            if proc.stdin and not proc.stdin.closed:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

        elapsed = time.perf_counter() - start_time
        speed = total_frames / elapsed if elapsed > 0 else 0.0
        peak_mb = peak / (1024 * 1024)

        logger.info(
            "Render complete: %d frames in %.2f s (%.1f fps). Peak RAM: %.2f MB",
            total_frames,
            elapsed,
            speed,
            peak_mb,
        )

        return RenderStats(
            total_frames=total_frames,
            duration_sec=timeline.duration_sec,
            fps=fps,
            elapsed_time_sec=elapsed,
            fps_render_speed=speed,
            peak_ram_mb=peak_mb,
            output_path=out_file,
        )
