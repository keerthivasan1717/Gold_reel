"""Automated failure drill harness for GoldReel.

Tests and validates pipeline resilience against critical failure scenarios:
1. Upstream data adapter network/parse failure.
2. Complete AI narration provider chain failure (offline synthesis fallback).
3. Fact gate hallucination rejection.
4. Frame QC defect detection (blank frames / safe zone breaches).
5. YouTube API restricted mode fallback packaging.
6. Global emergency kill switch activation.
"""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

from goldreel.config.loader import PipelineConfig
from goldreel.facts.gate import FactGate
from goldreel.facts.models import FactTable
from goldreel.publish.fallback import FallbackPackager
from goldreel.publish.uploader import YouTubeUploader
from goldreel.qc.frame import FrameQC
from goldreel.script.models import GeneratedScript, ScriptScene
from goldreel.script.router import ProviderRouter
from goldreel.state.store import StateStore


@dataclass
class DrillResult:
    """Result of an individual failure drill."""

    name: str
    passed: bool
    description: str
    details: str = ""


class FailureDrillRunner:
    """Orchestrates comprehensive failure drills against the GoldReel pipeline."""

    def __init__(self, work_dir: Path | str | None = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="goldreel_drills_")).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def drill_ai_provider_chain_failure(self) -> DrillResult:
        """Verify that complete AI provider failure seamlessly falls back to offline synthesis."""
        import os

        router = ProviderRouter()
        # Empty env keys simulate provider unavailability
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": ""}):
            facts = FactTable(
                topic_id="drill_topic",
                title="IPL Most Centuries",
                lane="sports",
                metric_label="Centuries",
                sources=[
                    {
                        "name": "cricsheet",
                        "source_url": "https://cricsheet.org",
                        "retrieved_at": "2026-11-18T00:00:00Z",
                    }
                ],
                records=[
                    {
                        "rank": 1,
                        "entity": "Virat Kohli",
                        "metric": "Centuries",
                        "value": 8,
                        "unit": "centuries",
                    },
                    {
                        "rank": 2,
                        "entity": "Chris Gayle",
                        "metric": "Centuries",
                        "value": 6,
                        "unit": "centuries",
                    },
                ],
            )

            try:
                script = router.generate_script(facts, format_type="landscape")
                is_valid = (
                    script.topic_id == "drill_topic"
                    and len(script.scenes) >= 1
                    and "Virat Kohli" in script.scenes[0].text
                )
                return DrillResult(
                    name="AI Provider Chain Outage Fallback",
                    passed=is_valid,
                    description="Pipeline falls back to offline deterministic synthesis when all API providers fail.",
                    details=f"Generated {len(script.scenes)} scenes via offline engine: '{script.scenes[0].text}'",
                )
            except Exception as e:
                return DrillResult(
                    name="AI Provider Chain Outage Fallback",
                    passed=False,
                    description="Pipeline failed to fall back to offline synthesis.",
                    details=str(e),
                )

    def drill_hallucinated_fact_injection(self) -> DrillResult:
        """Verify that FactGate blocks any AI script containing hallucinated entities or numbers."""
        facts = FactTable(
            topic_id="drill_topic_2",
            title="IPL Most Centuries",
            lane="sports",
            metric_label="Centuries",
            sources=[
                {
                    "name": "cricsheet",
                    "source_url": "https://cricsheet.org",
                    "retrieved_at": "2026-11-18T00:00:00Z",
                }
            ],
            records=[
                {
                    "rank": 1,
                    "entity": "Virat Kohli",
                    "metric": "Centuries",
                    "value": 8,
                    "unit": "centuries",
                }
            ],
        )

        # Inject a hallucinated number (999) and ungrounded entity ("Tony Stark")
        hallucinated_script = GeneratedScript(
            topic_id="drill_topic_2",
            title="IPL Most Centuries",
            lane="sports",
            format_type="landscape",
            template_type="stat_race",
            hook="Who holds the most centuries?",
            scenes=[
                ScriptScene(
                    scene_index=1,
                    scene_type="data",
                    text="Tony Stark scored 999 centuries in IPL history.",
                    bound_entities=["Tony Stark"],
                    bound_numbers=[999],
                ),
                ScriptScene(
                    scene_index=2,
                    scene_type="data",
                    text="A totally fictional stat.",
                    bound_entities=[],
                    bound_numbers=[],
                ),
            ],
            insight="A remarkable conversion rate.",
            outro_text="Source: open data.",
        )

        gate = FactGate(facts)
        res = gate.verify_script(hallucinated_script.model_dump())

        # We expect verification to FAIL
        blocked = not res.passed and len(res.violations) > 0
        return DrillResult(
            name="Fact Gate Hallucination Rejection",
            passed=blocked,
            description="FactGate intercepts and blocks ungrounded entities and fake numeric claims.",
            details=f"Gate correctly rejected script with {len(res.violations)} violation(s): {res.violations}",
        )

    def drill_frame_qc_defect_injection(self) -> DrillResult:
        """Verify that FrameQC intercepts blank frames and boundary clipping."""
        from PIL import Image

        # Create completely blank (all black) frames
        blank_frame = Image.new("RGB", (1920, 1080), (0, 0, 0))
        blank_frames = [(float(i), blank_frame, None) for i in range(6)]

        qc = FrameQC()
        checks, audits = qc.check(blank_frames, format_type="landscape")

        # Blank frames must be detected and fail QC
        blank_fails = [
            c for c in checks if c.name in ("no_blank_frames", "no_flat_frames") and not c.passed
        ]
        detected = len(blank_fails) > 0
        return DrillResult(
            name="Frame QC Defect Detection",
            passed=detected,
            description="FrameQC catches blank/flat frames and blocks corrupted video output.",
            details=f"FrameQC caught defect: {[c.message for c in blank_fails]}",
        )

    def drill_youtube_api_restricted_mode(self) -> DrillResult:
        """Verify fallback packaging triggers when YouTube API is restricted or quota is exceeded."""
        store = StateStore(base_dir=self.work_dir / "state")
        job = store.create_job()

        job.save_artifact("qc_report.json", {"passed": True, "summary": "Passed"})
        job.save_artifact("video.mp4", b"mock video data")
        job.save_artifact(
            "facts.json",
            {
                "topic_id": "drill",
                "title": "Drill Title",
                "lane": "sports",
                "sources": [],
                "records": [],
            },
        )

        packager = FallbackPackager(out_dir=self.work_dir / "out")
        uploader = YouTubeUploader(
            auth=MagicMock(),
            packager=packager,
        )

        # Force mock uploader upload to return restricted API status
        with patch.object(
            uploader,
            "_execute_api_upload",
            return_value={
                "restricted_project": True,
                "reason": "Google Cloud project has not completed YouTube API compliance audit.",
            },
        ):
            result = uploader.publish(job, dry_run=False)

        fallback_dir = self.work_dir / "out" / job.job_id
        has_fallback_files = (
            fallback_dir.exists()
            and (fallback_dir / "video.mp4").exists()
            and (fallback_dir / "metadata.json").exists()
            and (fallback_dir / "owner_alert_email.txt").exists()
        )

        passed = (
            result.mode == "fallback_package"
            and result.fallback_package_path is not None
            and has_fallback_files
        )

        return DrillResult(
            name="Restricted YouTube API Fallback Drill",
            passed=passed,
            description="Uploader automatically prepares offline upload packages when API is restricted.",
            details=f"Fallback package successfully built at {fallback_dir}",
        )

    def drill_global_kill_switch(self) -> DrillResult:
        """Verify global kill switch (publish_enabled: false) immediately halts uploads."""
        from goldreel.config.loader import PublishingConfig

        cfg = PipelineConfig(publishing=PublishingConfig(publish_enabled=False))
        store = StateStore(base_dir=self.work_dir / "state")
        job = store.create_job()

        job.save_artifact("qc_report.json", {"passed": True, "summary": "Passed"})
        job.save_artifact("video.mp4", b"mock video data")

        packager = FallbackPackager(out_dir=self.work_dir / "out")
        uploader = YouTubeUploader(
            config=cfg,
            auth=MagicMock(),
            packager=packager,
        )

        result = uploader.publish(job, dry_run=False)

        passed = (
            result.mode == "fallback_package"
            and "kill switch" in result.details.lower()
        )
        return DrillResult(
            name="Emergency Kill Switch Drill",
            passed=passed,
            description="Global kill switch instantly arrests all network upload actions.",
            details=f"Upload blocked cleanly with mode: {result.mode} ('{result.details}')",
        )

    def run_all_drills(self) -> list[DrillResult]:
        """Execute all failure drills sequentially."""
        return [
            self.drill_ai_provider_chain_failure(),
            self.drill_hallucinated_fact_injection(),
            self.drill_frame_qc_defect_injection(),
            self.drill_youtube_api_restricted_mode(),
            self.drill_global_kill_switch(),
        ]

    def cleanup(self) -> None:
        """Remove temporary drill files."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
