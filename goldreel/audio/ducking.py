"""Audio ducking and loudness normalization mixer.

Ducks background music under narration voice and normalizes loudness to -14 LUFS
using FFmpeg filters per docs/DESIGN.md & docs/GEMINI.md.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioMixer:
    """Mixes voice and music tracks with sidechain ducking and EBU R128 loudness normalization."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def prepare_music_track(
        self,
        music_path: Path | str,
        duration_sec: float,
        output_path: Path | str,
        target_loudness_lufs: float = -14.0,
        max_true_peak_dbfs: float = -1.0,
        fade_out_sec: float = 2.0,
    ) -> Path:
        """Prepare normalized music-only audio track with end fade-out per docs/DESIGN.md."""
        m_file = Path(music_path).resolve()
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fade_start = max(0.0, duration_sec - fade_out_sec)
        filter_str = (
            f"atrim=0:{duration_sec},"
            f"afade=t=out:st={fade_start:.2f}:d={fade_out_sec:.2f},"
            f"loudnorm=I={target_loudness_lufs}:TP={max_true_peak_dbfs}:LRA=7"
        )
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(m_file),
            "-af",
            filter_str,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(out_file),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return out_file

    def mix_and_duck(
        self,
        voice_path: Path | str,
        music_path: Path | str | None,
        output_path: Path | str,
        target_loudness_lufs: float = -14.0,
        max_true_peak_dbfs: float = -1.0,
    ) -> Path:
        """Mix voice and music with automated ducking and loudness normalization."""
        v_file = Path(voice_path).resolve()
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        m_file = Path(music_path).resolve() if music_path else None
        has_music = m_file and m_file.exists()

        if has_music:
            logger.info(
                "Mixing voice (%s) with music (%s) using ducking...", v_file.name, m_file.name
            )
            # Sidechain ducking filter:
            # 1. Background music level reduced to base volume 0.35.
            # 2. Sidechaincompress ducks music when voice is active.
            # 3. amix combines them with duration=first (voice length drives mix).
            # 4. loudnorm brings the combined mix to target LUFS (-14 LUFS).
            filter_complex = (
                "[1:a]volume=0.35[bg];"
                "[bg][0:a]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=300[ducked];"
                "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2,"
                f"loudnorm=I={target_loudness_lufs}:TP={max_true_peak_dbfs}:LRA=7[out]"
            )
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(v_file),
                "-stream_loop",
                "-1",  # Loop music if voice is longer
                "-i",
                str(m_file),
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(out_file),
            ]
        else:
            logger.info("No music track provided. Normalizing voice track alone...")
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(v_file),
                "-af",
                f"loudnorm=I={target_loudness_lufs}:TP={max_true_peak_dbfs}:LRA=7",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(out_file),
            ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg audio mixing failed with code {proc.returncode}: {proc.stderr}"
            )

        return out_file
