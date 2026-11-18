"""Audio Quality Control (QC) measuring loudness, true peak, and silence."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from goldreel.qc.models import QCCheckItem


class AudioQC:
    """Automated audio loudness and peak gate using FFmpeg loudnorm / ebur128 analysis."""

    def __init__(
        self,
        target_loudness_lufs: float = -14.0,
        max_true_peak_dbfs: float = -1.0,
        tolerance_lufs: float = 1.5,
    ):
        self.target_loudness = target_loudness_lufs
        self.max_true_peak = max_true_peak_dbfs
        self.tolerance = tolerance_lufs

    def probe_media(self, path: Path) -> dict[str, Any]:
        """Query audio/video stream details using ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,duration,channels,sample_rate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout)
        except Exception as e:
            return {"error": str(e), "streams": [], "format": {}}

    def analyze_loudness(self, path: Path) -> dict[str, float]:
        """Run FFmpeg loudnorm analysis to extract integrated loudness and true peak."""
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        # Search for the JSON block emitted by the loudnorm filter in stderr
        match = re.search(r"\{\s*\"input_i\"\s*:.*?\n\}", proc.stderr, re.DOTALL)
        if not match:
            return {"input_i": -99.0, "input_tp": -99.0, "input_lra": 0.0}

        try:
            parsed = json.loads(match.group(0))
            return {
                "input_i": float(parsed.get("input_i", -99.0)),
                "input_tp": float(parsed.get("input_tp", -99.0)),
                "input_lra": float(parsed.get("input_lra", 0.0)),
            }
        except Exception:
            return {"input_i": -99.0, "input_tp": -99.0, "input_lra": 0.0}

    def check(self, media_path: Path) -> list[QCCheckItem]:
        """Perform full audio quality check suite on media file."""
        checks: list[QCCheckItem] = []
        if not media_path.exists():
            checks.append(
                QCCheckItem(
                    name="audio_file_exists",
                    category="audio",
                    passed=False,
                    severity="critical",
                    message=f"Audio media file not found: {media_path}",
                )
            )
            return checks

        probe = self.probe_media(media_path)
        streams = probe.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not audio_stream:
            checks.append(
                QCCheckItem(
                    name="audio_stream_present",
                    category="audio",
                    passed=False,
                    severity="critical",
                    message="Media file does not contain an audio stream",
                )
            )
            return checks

        checks.append(
            QCCheckItem(
                name="audio_stream_present",
                category="audio",
                passed=True,
                severity="critical",
                message=f"Audio stream detected: {audio_stream.get('codec_name', 'unknown')}",
                measured_value=audio_stream.get("codec_name"),
            )
        )

        loudness = self.analyze_loudness(media_path)
        input_i = loudness["input_i"]
        input_tp = loudness["input_tp"]

        # 1. Silence check
        if input_i <= -50.0:
            checks.append(
                QCCheckItem(
                    name="audio_not_silent",
                    category="audio",
                    passed=False,
                    severity="critical",
                    message=f"Audio is silent or near-silent ({input_i:.1f} LUFS)",
                    measured_value=input_i,
                    target_value="> -50.0 LUFS",
                )
            )
        else:
            checks.append(
                QCCheckItem(
                    name="audio_not_silent",
                    category="audio",
                    passed=True,
                    severity="critical",
                    message=f"Audio signal is audible ({input_i:.1f} LUFS)",
                    measured_value=input_i,
                )
            )

        # 2. Integrated Loudness check (-14 LUFS +/- tolerance)
        min_lufs = self.target_loudness - self.tolerance
        max_lufs = self.target_loudness + self.tolerance
        loudness_passed = min_lufs <= input_i <= max_lufs
        checks.append(
            QCCheckItem(
                name="integrated_loudness",
                category="audio",
                passed=loudness_passed,
                severity="critical",
                message=f"Integrated loudness {input_i:.1f} LUFS (target: {self.target_loudness:.1f} ± {self.tolerance:.1f} LUFS)",
                measured_value=input_i,
                target_value=f"{min_lufs:.1f} to {max_lufs:.1f} LUFS",
            )
        )

        # 3. True Peak check (<= max_true_peak_dbfs)
        peak_passed = input_tp <= self.max_true_peak
        checks.append(
            QCCheckItem(
                name="true_peak_ceiling",
                category="audio",
                passed=peak_passed,
                severity="critical",
                message=f"Max true peak {input_tp:.1f} dBFS (ceiling: {self.max_true_peak:.1f} dBFS)",
                measured_value=input_tp,
                target_value=f"<= {self.max_true_peak:.1f} dBFS",
            )
        )

        return checks
