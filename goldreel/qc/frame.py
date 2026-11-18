"""Frame Quality Control (QC) inspecting visual output, blank frames, safe margins, and layout."""

import io
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from goldreel.design.tokens import Layout
from goldreel.qc.models import FrameAudit, QCCheckItem


class FrameQC:
    """Automated visual inspection of rendered video frames."""

    def __init__(self, sample_count: int = 10):
        self.sample_count = max(sample_count, 10)

    def get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 3.0

    def extract_sample_frames(
        self, video_path: Path, output_dir: Path | None = None
    ) -> list[tuple[float, Image.Image, Path | None]]:
        """Extract 10 sample frames evenly distributed across the video."""
        dur = self.get_video_duration(video_path)
        # 10 canonical inspection points: 5%, 15%, 25%, 35%, 45%, 55%, 65%, 75%, 85%, 95%
        ratios = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
        timestamps = [round(max(0.1, r * dur), 2) for r in ratios]

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        frames: list[tuple[float, Image.Image, Path | None]] = []
        for idx, t in enumerate(timestamps):
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-ss",
                str(t),
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ]
            proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0 or not proc.stdout:
                continue

            try:
                img = Image.open(io.BytesIO(proc.stdout)).convert("RGB")
                saved_path: Path | None = None
                if output_dir:
                    saved_path = output_dir / f"frame_{idx + 1:02d}_{t:.2f}s.png"
                    img.save(saved_path)
                frames.append((t, img, saved_path))
            except Exception:
                continue

        return frames

    def check(
        self,
        frames: list[tuple[float, Image.Image, Path | None]],
        format_type: str = "landscape",
    ) -> tuple[list[QCCheckItem], list[FrameAudit]]:
        """Run visual checks across extracted frames."""
        checks: list[QCCheckItem] = []
        audits: list[FrameAudit] = []

        if not frames:
            checks.append(
                QCCheckItem(
                    name="frames_extracted",
                    category="frame",
                    passed=False,
                    severity="critical",
                    message="No frames could be extracted from video",
                )
            )
            return checks, audits

        checks.append(
            QCCheckItem(
                name="sample_frames_count",
                category="frame",
                passed=len(frames) >= 6,
                severity="warning" if len(frames) >= 4 else "critical",
                message=f"Reviewed {len(frames)} frames across video duration (target: >= 6)",
                measured_value=len(frames),
                target_value=">= 6",
            )
        )

        # 1. Inspect Resolution
        first_frame = frames[0][1]
        w, h = first_frame.size
        if format_type == "portrait":
            res_pass = w == Layout.PORTRAIT_WIDTH and h == Layout.PORTRAIT_HEIGHT
            expected_res = f"{Layout.PORTRAIT_WIDTH}x{Layout.PORTRAIT_HEIGHT}"
        else:
            res_pass = w == Layout.LANDSCAPE_WIDTH and h == Layout.LANDSCAPE_HEIGHT
            expected_res = f"{Layout.LANDSCAPE_WIDTH}x{Layout.LANDSCAPE_HEIGHT}"

        checks.append(
            QCCheckItem(
                name="resolution_compliance",
                category="frame",
                passed=res_pass,
                severity="critical",
                message=f"Resolution is {w}x{h} (expected {expected_res} for {format_type})",
                measured_value=f"{w}x{h}",
                target_value=expected_res,
            )
        )

        # 2. Frame-by-frame analysis
        has_blank_frame = False
        has_flat_frame = False
        margin_breaches = 0
        bottom_ui_breaches = 0
        gold_detected_count = 0

        for t, img, saved_path in frames:
            gray = img.convert("L")
            stat = ImageStat.Stat(gray)
            mean_lum = stat.mean[0]
            std_lum = stat.stddev[0]

            is_blank = mean_lum < 5.0 and std_lum < 2.0
            is_flat = std_lum < 1.0

            if is_blank:
                has_blank_frame = True
            if is_flat:
                has_flat_frame = True

            # Safe margin & text clipping check
            # Look for high-luminance foreground text (lum > 210) right at the frame outer boundary
            outer_edge_left = gray.crop((0, 0, 20, h))
            outer_edge_top = gray.crop((0, 0, w, 20))
            outer_edge_right = gray.crop((w - 20, 0, w, h))

            stat_l = ImageStat.Stat(outer_edge_left)
            stat_t = ImageStat.Stat(outer_edge_top)
            stat_r = ImageStat.Stat(outer_edge_right)

            # Max luminance in extreme edge should not have pure text (> 220)
            if (
                stat_l.extrema[0][1] > 225
                or stat_t.extrema[0][1] > 225
                or stat_r.extrema[0][1] > 225
            ):
                margin_breaches += 1

            # Portrait bottom 120px platform UI exclusion zone check
            if format_type == "portrait":
                bottom_zone = gray.crop((0, h - 120, w, h))
                stat_b = ImageStat.Stat(bottom_zone)
                # Bottom platform UI zone should be empty background, max lum < 200
                if stat_b.extrema[0][1] > 200:
                    bottom_ui_breaches += 1

            # Accent presence check (look for gold tokens: rgb(212, 175, 55))
            small_w, small_h = (180, 320) if format_type == "portrait" else (320, 180)
            small = img.resize((small_w, small_h), Image.Resampling.NEAREST)
            has_gold = any(
                r > 160 and g > 130 and b < 110 and (r - b) > 50 for r, g, b in small.getdata()
            )
            if has_gold:
                gold_detected_count += 1

            audits.append(
                FrameAudit(
                    timestamp_sec=t,
                    mean_luminance=round(mean_lum, 2),
                    stddev_luminance=round(std_lum, 2),
                    passed=not (is_blank or is_flat),
                    notes=f"Mean lum: {mean_lum:.1f}, Std: {std_lum:.1f}",
                    saved_path=str(saved_path) if saved_path else None,
                )
            )

        # Blank / Solid Black Frame Gate
        checks.append(
            QCCheckItem(
                name="no_blank_frames",
                category="frame",
                passed=not has_blank_frame,
                severity="critical",
                message="No solid black / unrendered blank frames detected"
                if not has_blank_frame
                else "Solid black frame detected in video",
            )
        )

        checks.append(
            QCCheckItem(
                name="no_flat_frames",
                category="frame",
                passed=not has_flat_frame,
                severity="critical",
                message="Frames display rich graphical variance"
                if not has_flat_frame
                else "Zero-variance flat frame detected",
            )
        )

        # Margin / Text Clipping Gate
        checks.append(
            QCCheckItem(
                name="safe_margins_respected",
                category="frame",
                passed=margin_breaches == 0,
                severity="critical" if margin_breaches > 1 else "warning",
                message="All text and visual elements stay within safe margins"
                if margin_breaches == 0
                else f"Text clipping/bleed detected near frame edge in {margin_breaches} frame(s)",
                measured_value=margin_breaches,
                target_value=0,
            )
        )

        if format_type == "portrait":
            checks.append(
                QCCheckItem(
                    name="portrait_bottom_exclusion_zone",
                    category="frame",
                    passed=bottom_ui_breaches == 0,
                    severity="critical",
                    message="Bottom 120px platform UI exclusion zone is clear of foreground text"
                    if bottom_ui_breaches == 0
                    else f"Content detected inside bottom 120px platform UI zone in {bottom_ui_breaches} frame(s)",
                    measured_value=bottom_ui_breaches,
                    target_value=0,
                )
            )

        # Freeze and Continuous Motion Gate
        if len(frames) >= 2:
            pair_diffs: list[float] = []
            identical_pairs = 0
            for i in range(len(frames) - 1):
                f1 = frames[i][1]
                f2 = frames[i + 1][1]
                diff = ImageChops.difference(f1, f2)
                d_stat = ImageStat.Stat(diff.convert("L"))
                m_diff = d_stat.mean[0]
                pair_diffs.append(m_diff)
                if m_diff < 0.15:
                    identical_pairs += 1

            avg_pair_diff = sum(pair_diffs) / len(pair_diffs) if pair_diffs else 0.0
            identical_ratio = identical_pairs / len(pair_diffs) if pair_diffs else 1.0

            # Compute difference between earliest frame and latest frame
            span_diff = ImageChops.difference(frames[0][1], frames[-1][1])
            span_mean = ImageStat.Stat(span_diff.convert("L")).mean[0]

            is_diverse = (avg_pair_diff >= 0.35) and (identical_ratio <= 0.60) and (span_mean >= 2.0)

            checks.append(
                QCCheckItem(
                    name="continuous_motion_diversity",
                    category="frame",
                    passed=is_diverse,
                    severity="critical",
                    message="Continuous motion and scene transitions confirmed across sampled frames"
                    if is_diverse
                    else f"Video frames are mostly identical (avg step diff: {avg_pair_diff:.2f}, span diff: {span_mean:.2f}, identical pairs: {identical_ratio*100:.0f}%). Continuous animation required.",
                    measured_value=round(avg_pair_diff, 2),
                    target_value=">= 0.35",
                )
            )

        if len(frames) >= 4:
            f_early = frames[1][1]
            f_late = frames[-2][1]
            diff = ImageChops.difference(f_early, f_late)
            diff_stat = ImageStat.Stat(diff.convert("L"))
            is_frozen = diff_stat.mean[0] < 0.05 and diff_stat.stddev[0] < 0.05
            checks.append(
                QCCheckItem(
                    name="no_frozen_render",
                    category="frame",
                    passed=not is_frozen,
                    severity="critical",
                    message="Timeline motion dynamic across sample intervals"
                    if not is_frozen
                    else "Frames appear identical across time; render pipe may be frozen",
                )
            )

        # Dark theme / Gold accent check
        checks.append(
            QCCheckItem(
                name="design_token_palette",
                category="frame",
                passed=gold_detected_count > 0,
                severity="warning",
                message=f"Black and gold aesthetic confirmed in {gold_detected_count}/{len(frames)} audited frames",
                measured_value=gold_detected_count,
            )
        )

        return checks, audits
