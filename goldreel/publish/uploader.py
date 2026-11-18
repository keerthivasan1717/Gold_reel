"""Central YouTube video publisher and safety gateway.

Strictly follows docs/PLAN.md Section 7 & 8 and docs/GEMINI.md Section 5:
- Master kill switch verification (config.publish_enabled)
- Automated rate limiting (max uploads per day & per week)
- QC gate prerequisite check
- Resumable upload with scheduled publishAt
- Automatic detection of unverified Google project / restricted API status
- Fallback packaging into out/<job_id>/
"""

import json
from pathlib import Path
from typing import Any

import httpx

from goldreel.config.loader import PipelineConfig, load_pipeline_config
from goldreel.facts.models import FactTable
from goldreel.publish.auth import YouTubeAuth
from goldreel.publish.fallback import FallbackPackager
from goldreel.publish.models import PublishMetadata, PublishResult
from goldreel.publish.scheduler import PublishHistory, PublishScheduler
from goldreel.publish.thumbnail import ThumbnailGenerator
from goldreel.script.models import GeneratedScript
from goldreel.state.store import JobState


class YouTubeUploader:
    """Orchestrates YouTube Data API v3 publishing, safety limits, and restricted-API fallback."""

    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    THUMBNAIL_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"

    def __init__(
        self,
        config: PipelineConfig | None = None,
        auth: YouTubeAuth | None = None,
        history: PublishHistory | None = None,
        packager: FallbackPackager | None = None,
    ):
        self.config = config or load_pipeline_config()
        self.auth = auth or YouTubeAuth()
        self.history = history or PublishHistory()
        self.scheduler = PublishScheduler(self.history)
        self.packager = packager or FallbackPackager()
        self.thumbnail_gen = ThumbnailGenerator()

    def prepare_metadata(self, job: JobState) -> PublishMetadata:
        """Assemble complete publishing metadata package from job artifacts."""
        script_path = job.job_dir / "script.json"
        credits_path = job.job_dir / "credits.txt"

        title = "GoldReel Data Insights"
        format_type = "landscape"
        tags = ["data", "visualization", "statistics", "records"]

        if script_path.exists():
            try:
                with open(script_path, encoding="utf-8") as f:
                    s_data = json.load(f)
                title = s_data.get("title", title)
                format_type = s_data.get("format_type", "landscape")
            except Exception:
                pass

        description = "Automated data visualization by GoldReel."
        if credits_path.exists():
            try:
                description = credits_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Compute scheduled release timestamp
        publish_at = self.scheduler.compute_publish_time(format_type=format_type)

        return PublishMetadata(
            title=title[:100],
            description=description[:5000],
            tags=tags,
            category_id="28" if "sports" not in title.lower() else "17",
            privacy_status="private",
            publish_at=publish_at,
            made_for_kids=self.config.publishing.made_for_kids,
            synthetic_content_disclosure=self.config.publishing.synthetic_content_disclosure,
        )

    def ensure_thumbnail(self, job: JobState, metadata: PublishMetadata) -> Path:
        """Generate thumbnail if not already present in job directory."""
        thumb_path = job.job_dir / "thumbnail.png"
        if thumb_path.exists():
            return thumb_path

        facts_path = job.job_dir / "facts.json"
        script_path = job.job_dir / "script.json"

        fact_table = None
        script = None

        if facts_path.exists():
            try:
                with open(facts_path, encoding="utf-8") as f:
                    fact_table = FactTable(**json.load(f))
            except Exception:
                pass

        if script_path.exists():
            try:
                with open(script_path, encoding="utf-8") as f:
                    script = GeneratedScript(**json.load(f))
            except Exception:
                pass

        format_type = script.format_type if script else "landscape"
        if fact_table and script:
            self.thumbnail_gen.generate(fact_table, script, thumb_path, format_type=format_type)
            job.register_existing_file(thumb_path)
            return thumb_path

        # Minimal fallback thumbnail
        from PIL import Image

        img = Image.new("RGB", (1280, 720), (10, 10, 10))
        img.save(thumb_path)
        job.register_existing_file(thumb_path)
        return thumb_path

    def publish(self, job: JobState, dry_run: bool = False) -> PublishResult:
        """Publish a job video to YouTube or package into out/<job_id>/."""
        job.mark_stage_start("publish")

        # 1. Prerequisite: Check Quality Control Stage
        qc_report_path = job.job_dir / "qc_report.json"
        if not qc_report_path.exists():
            err_msg = "Cannot publish: Quality Control gate (qc_report.json) not found in job state"
            job.mark_stage_failed("publish", error=err_msg)
            return PublishResult(
                job_id=job.job_id,
                success=False,
                mode="dry_run" if dry_run else "scheduled",
                details=err_msg,
            )

        try:
            with open(qc_report_path, encoding="utf-8") as f:
                qc_data = json.load(f)
            if not qc_data.get("passed", False):
                err_msg = f"Cannot publish: Quality Control failed ({qc_data.get('summary', 'Checks failed')})"
                job.mark_stage_failed("publish", error=err_msg)
                return PublishResult(
                    job_id=job.job_id,
                    success=False,
                    mode="dry_run" if dry_run else "scheduled",
                    details=err_msg,
                )
        except Exception as e:
            err_msg = f"Cannot parse QC report: {e}"
            job.mark_stage_failed("publish", error=err_msg)
            return PublishResult(
                job_id=job.job_id,
                success=False,
                mode="dry_run" if dry_run else "scheduled",
                details=err_msg,
            )

        # 2. Prepare metadata and thumbnail
        metadata = self.prepare_metadata(job)
        self.ensure_thumbnail(job, metadata)

        # 3. Check Master Kill Switch
        if not self.config.publishing.publish_enabled or dry_run:
            mode_desc = (
                "Dry-run mode" if dry_run else "Publish kill switch active (publish_enabled=False)"
            )
            pkg_path = self.packager.package(
                job=job,
                metadata=metadata,
                reason=f"{mode_desc}. Network upload safely bypassed.",
            )
            result = PublishResult(
                job_id=job.job_id,
                success=True,
                mode="dry_run" if dry_run else "fallback_package",
                scheduled_at=metadata.publish_at,
                fallback_package_path=str(pkg_path),
                details=f"{mode_desc}. Release package saved in out/{job.job_id}/.",
            )
            job.save_artifact("publish_result.json", result.model_dump())
            job.mark_stage_completed(
                "publish",
                metadata={
                    "mode": result.mode,
                    "scheduled_at": result.scheduled_at,
                    "package_dir": str(pkg_path),
                },
            )
            return result

        # 4. Check Upload Limits & Quota
        can_pub, limit_reason = self.scheduler.can_publish(
            max_per_day=self.config.publishing.max_uploads_per_day,
            max_per_week=self.config.publishing.max_uploads_per_week,
        )
        if not can_pub:
            pkg_path = self.packager.package(
                job=job,
                metadata=metadata,
                reason=f"Rate limit hit: {limit_reason}.",
            )
            result = PublishResult(
                job_id=job.job_id,
                success=True,
                mode="fallback_package",
                fallback_package_path=str(pkg_path),
                details=f"Rate limit protection triggered ({limit_reason}). Packaged in out/.",
            )
            job.save_artifact("publish_result.json", result.model_dump())
            job.mark_stage_completed(
                "publish", metadata={"mode": "fallback_package", "reason": limit_reason}
            )
            return result

        # 5. Authenticate with YouTube Data API v3
        access_token = self.auth.get_access_token()
        if not access_token:
            pkg_path = self.packager.package(
                job=job,
                metadata=metadata,
                reason="No YouTube OAuth credentials configured or token expired.",
            )
            result = PublishResult(
                job_id=job.job_id,
                success=True,
                mode="fallback_package",
                is_restricted_api=True,
                fallback_package_path=str(pkg_path),
                details="OAuth credentials missing or unconfigured. Packaged into out/ for 3-minute Studio upload.",
            )
            job.save_artifact("publish_result.json", result.model_dump())
            job.mark_stage_completed(
                "publish", metadata={"mode": "fallback_package", "is_restricted_api": True}
            )
            return result

        # 6. Execute Resumable API Upload
        video_path = job.job_dir / "video.mp4"
        if not video_path.exists():
            err = f"Video file not found at {video_path}"
            job.mark_stage_failed("publish", error=err)
            return PublishResult(job_id=job.job_id, success=False, mode="scheduled", details=err)

        upload_res = self._execute_api_upload(video_path, metadata, access_token)

        if upload_res.get("restricted_project") or upload_res.get("error"):
            # Restricted API detected (project has not passed compliance audit)
            reason = upload_res.get(
                "reason", "Google Cloud project has not completed YouTube API compliance audit."
            )
            pkg_path = self.packager.package(job, metadata, reason=reason)
            result = PublishResult(
                job_id=job.job_id,
                success=True,
                mode="fallback_package",
                is_restricted_api=True,
                fallback_package_path=str(pkg_path),
                details=f"Restricted API detected ({reason}). Packaged in out/ for 3-minute Studio upload.",
            )
            job.save_artifact("publish_result.json", result.model_dump())
            job.mark_stage_completed(
                "publish", metadata={"mode": "fallback_package", "is_restricted_api": True}
            )
            return result

        # Success path
        video_id = upload_res["video_id"]
        youtube_url = f"https://youtu.be/{video_id}"

        # Upload thumbnail
        self._upload_thumbnail(video_id, job.job_dir / "thumbnail.png", access_token)

        # Record in publish history
        self.history.record_upload(
            job_id=job.job_id,
            video_id=video_id,
            scheduled_at=metadata.publish_at,
            mode="scheduled",
        )

        result = PublishResult(
            job_id=job.job_id,
            success=True,
            mode="scheduled",
            video_id=video_id,
            youtube_url=youtube_url,
            scheduled_at=metadata.publish_at,
            details=f"Video successfully uploaded and scheduled for {metadata.publish_at}.",
        )
        job.save_artifact("publish_result.json", result.model_dump())
        job.mark_stage_completed(
            "publish",
            metadata={
                "video_id": video_id,
                "youtube_url": youtube_url,
                "scheduled_at": metadata.publish_at,
                "mode": "scheduled",
            },
        )
        return result

    def _execute_api_upload(
        self,
        video_path: Path,
        metadata: PublishMetadata,
        access_token: str,
    ) -> dict[str, Any]:
        """Perform resumable upload with YouTube Data API v3."""
        snippet = {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "categoryId": metadata.category_id,
        }
        status = {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": metadata.made_for_kids,
        }
        if metadata.publish_at:
            status["publishAt"] = metadata.publish_at

        body = {"snippet": snippet, "status": status}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(video_path.stat().st_size),
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                init_res = client.post(
                    f"{self.UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                    headers=headers,
                    json=body,
                )

                if init_res.status_code == 403:
                    return {
                        "restricted_project": True,
                        "reason": "YouTube Data API compliance audit not completed (HTTP 403 Forbidden)",
                    }

                if init_res.status_code not in (200, 201):
                    return {
                        "error": True,
                        "reason": f"API init failed with HTTP {init_res.status_code}",
                    }

                upload_uri = init_res.headers.get("Location")
                if not upload_uri:
                    return {"error": True, "reason": "No upload Location URI returned"}

                # Stream video content to resumable session URI
                with open(video_path, "rb") as video_file:
                    video_bytes = video_file.read()

                put_headers = {"Content-Length": str(len(video_bytes)), "Content-Type": "video/mp4"}
                put_res = client.put(upload_uri, headers=put_headers, content=video_bytes)

                if put_res.status_code in (200, 201):
                    data = put_res.json()
                    return {"video_id": data.get("id")}
                return {
                    "error": True,
                    "reason": f"Upload PUT failed with HTTP {put_res.status_code}",
                }
        except Exception as e:
            return {"error": True, "reason": str(e)}

    def _upload_thumbnail(self, video_id: str, thumb_path: Path, access_token: str) -> None:
        """Set thumbnail for uploaded video via YouTube Data API v3."""
        if not thumb_path.exists():
            return
        url = f"{self.THUMBNAIL_URL}?videoId={video_id}"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "image/png"}
        try:
            with httpx.Client(timeout=20.0) as client:
                with open(thumb_path, "rb") as f:
                    client.post(url, headers=headers, content=f.read())
        except Exception:
            pass
