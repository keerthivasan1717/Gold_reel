"""Central Quality Gate orchestrator for GoldReel automated pipeline."""

import json
from typing import Any

from goldreel.config.loader import PipelineConfig, load_pipeline_config
from goldreel.qc.audio import AudioQC
from goldreel.qc.frame import FrameQC
from goldreel.qc.metadata import MetadataQC
from goldreel.qc.models import FrameAudit, QCCheckItem, QCReport
from goldreel.qc.similarity import SimilarityQC
from goldreel.state.store import JobState, compute_content_hash
from goldreel.topics.history import TopicHistory


class QualityGate:
    """Orchestrates audio, visual, metadata, fact, and similarity quality gates."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        history: TopicHistory | None = None,
    ):
        self.config = config or load_pipeline_config()
        self.history = history or TopicHistory()
        self.audio_qc = AudioQC(
            target_loudness_lufs=self.config.quality_control.target_loudness_lufs,
            max_true_peak_dbfs=self.config.quality_control.max_true_peak_dbfs,
        )
        self.frame_qc = FrameQC(sample_count=6)
        self.metadata_qc = MetadataQC()
        self.similarity_qc = SimilarityQC(
            history=self.history,
            threshold_percent=self.config.quality_control.similarity_threshold_percent,
        )

    def evaluate_job(self, job: JobState, dry_run: bool = False) -> QCReport:
        """Run all automated quality control gates on a completed or in-progress job."""
        job.mark_stage_start("qc")
        checks: list[QCCheckItem] = []
        audits: list[FrameAudit] = []

        # 1. Check Fact Gate Status
        fact_gate_report_path = job.job_dir / "fact_gate_report.json"
        if not fact_gate_report_path.exists():
            checks.append(
                QCCheckItem(
                    name="fact_gate_passed",
                    category="facts",
                    passed=False,
                    severity="critical",
                    message="Fact gate report missing from job state",
                )
            )
        else:
            try:
                with open(fact_gate_report_path, encoding="utf-8") as f:
                    fg_data = json.load(f)
                fg_passed = bool(fg_data.get("passed", False))
                checks.append(
                    QCCheckItem(
                        name="fact_gate_passed",
                        category="facts",
                        passed=fg_passed,
                        severity="critical",
                        message="Script 100% grounded in verified facts"
                        if fg_passed
                        else f"Fact gate failed: {fg_data.get('summary', 'Unknown mismatch')}",
                        measured_value=fg_passed,
                    )
                )
            except Exception as e:
                checks.append(
                    QCCheckItem(
                        name="fact_gate_passed",
                        category="facts",
                        passed=False,
                        severity="critical",
                        message=f"Failed to parse fact gate report: {e}",
                    )
                )

        # 2. Check Video and Audio Assets
        video_path = job.job_dir / "video.mp4"
        format_type = "landscape"
        script_data: dict[str, Any] = {}
        script_path = job.job_dir / "script.json"
        if script_path.exists():
            try:
                with open(script_path, encoding="utf-8") as f:
                    script_data = json.load(f)
                    format_type = script_data.get("format_type", "landscape")
            except Exception:
                pass

        # Audio QC
        loudness_val: float | None = None
        true_peak_val: float | None = None
        audio_target_path = video_path if video_path.exists() else (job.job_dir / "audio_mixed.mp3")
        if audio_target_path.exists():
            audio_checks = self.audio_qc.check(audio_target_path)
            checks.extend(audio_checks)
            for ac in audio_checks:
                if ac.name == "integrated_loudness" and isinstance(ac.measured_value, (int, float)):
                    loudness_val = float(ac.measured_value)
                elif ac.name == "true_peak_ceiling" and isinstance(ac.measured_value, (int, float)):
                    true_peak_val = float(ac.measured_value)
        else:
            checks.append(
                QCCheckItem(
                    name="audio_present",
                    category="audio",
                    passed=False,
                    severity="critical",
                    message="No audio or muxed video found for QC analysis",
                )
            )

        # Frame QC & Visual Inspection
        video_dur = 0.0
        if video_path.exists():
            video_dur = self.frame_qc.get_video_duration(video_path)
            audit_dir = job.job_dir / "audit_frames"
            sample_frames = self.frame_qc.extract_sample_frames(video_path, output_dir=audit_dir)
            frame_checks, audits = self.frame_qc.check(sample_frames, format_type=format_type)
            checks.extend(frame_checks)
        else:
            checks.append(
                QCCheckItem(
                    name="video_rendered",
                    category="frame",
                    passed=False,
                    severity="critical",
                    message=f"Rendered video MP4 not found at {video_path}",
                )
            )

        # 3. Check Metadata & Duration
        title = script_data.get("title", "")
        if title:
            checks.extend(self.metadata_qc.check_title(title))

        credits_path = job.job_dir / "credits.txt"
        credits_text = ""
        if credits_path.exists():
            credits_text = credits_path.read_text(encoding="utf-8")

        desc_to_check = credits_text or script_data.get("stated_insight", "")
        # Add synthetic disclosure if not already present
        if desc_to_check:
            checks.extend(self.metadata_qc.check_description(desc_to_check))

        if video_dur > 0:
            checks.extend(
                self.metadata_qc.check_duration(
                    duration_sec=video_dur,
                    format_type=format_type,
                    is_dry_run=dry_run,
                )
            )

        # 4. Check Similarity
        facts_path = job.job_dir / "facts.json"
        entities: list[str] = []
        facts_hash = None
        if facts_path.exists():
            try:
                with open(facts_path, encoding="utf-8") as f:
                    facts_dict = json.load(f)
                    entities = [r.get("entity", "") for r in facts_dict.get("records", [])]
                    facts_hash = compute_content_hash(facts_dict)
            except Exception:
                pass

        sim_checks, max_sim = self.similarity_qc.check(
            title=title or "Untitled Topic",
            entities=entities,
            facts_hash=facts_hash,
            exclude_job_id=job.job_id,
        )
        checks.extend(sim_checks)

        # Compile overall QC report
        failed_critical = [c for c in checks if not c.passed and c.severity == "critical"]
        passed_overall = len(failed_critical) == 0

        summary = (
            f"QC PASSED: All {len(checks)} automated gates satisfied."
            if passed_overall
            else f"QC FAILED: {len(failed_critical)} critical check(s) failed ({', '.join(c.name for c in failed_critical)})."
        )

        report = QCReport(
            job_id=job.job_id,
            passed=passed_overall,
            checks=checks,
            summary=summary,
            duration_sec=video_dur if video_dur > 0 else None,
            loudness_lufs=loudness_val,
            true_peak_dbfs=true_peak_val,
            similarity_score=max_sim,
            frames_audited=audits,
        )

        # Save artifact and update job manifest
        job.save_artifact("qc_report.json", report.model_dump(mode="json"))
        if passed_overall:
            job.mark_stage_completed(
                "qc",
                metadata={
                    "passed": True,
                    "checks_count": len(checks),
                    "duration_sec": video_dur,
                    "loudness_lufs": loudness_val,
                    "true_peak_dbfs": true_peak_val,
                    "similarity_pct": max_sim,
                },
            )
        else:
            job.mark_stage_failed(
                "qc",
                error=summary,
            )

        return report
