"""Restricted API and safe-mode fallback packager.

Strictly follows docs/PLAN.md Section 7 & docs/GEMINI.md Section 5:
- Packages verified video, thumbnail, and complete metadata into out/<job_id>/
- Generates step-by-step YouTube Studio upload instructions
- Creates owner alert email template for immediate 3-minute manual batch upload
"""

import json
import shutil
from pathlib import Path

from goldreel.publish.models import PublishMetadata
from goldreel.state.store import JobState


class FallbackPackager:
    """Creates a standalone, ready-to-upload release package in out/<job_id>/."""

    def __init__(self, out_dir: Path | str = "out"):
        self.out_dir = Path(out_dir).resolve()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def package(
        self,
        job: JobState,
        metadata: PublishMetadata,
        reason: str,
    ) -> Path:
        """Create a complete upload package in out/<job_id>/."""
        target_dir = self.out_dir / job.job_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Video MP4
        src_video = job.job_dir / "video.mp4"
        if src_video.exists():
            shutil.copy2(src_video, target_dir / "video.mp4")

        # 2. Thumbnail
        src_thumb = job.job_dir / "thumbnail.png"
        if src_thumb.exists():
            shutil.copy2(src_thumb, target_dir / "thumbnail.png")

        # 3. Publish Metadata
        meta_dict = metadata.model_dump()
        meta_dict["fallback_reason"] = reason
        with open(target_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=2)

        # 4. Step-by-step Upload Instructions
        instructions = (
            f"=== GOLDREEL MANUAL UPLOAD GUIDE (Job: {job.job_id}) ===\n\n"
            f"REASON FOR FALLBACK:\n{reason}\n\n"
            "INSTRUCTIONS FOR YOUTUBE STUDIO (Takes ~3 minutes):\n"
            "1. Navigate to https://studio.youtube.com and click 'CREATE' -> 'Upload videos'.\n"
            "2. Select file: video.mp4 (located in this folder).\n"
            f"3. Title: {metadata.title}\n"
            "4. Description: Copy from metadata.json or paste the description below:\n"
            f"--------------------------------------------------\n"
            f"{metadata.description}\n"
            f"--------------------------------------------------\n"
            "5. Thumbnail: Upload thumbnail.png (located in this folder).\n"
            "6. Audience: Select 'No, it is not made for kids'.\n"
            "7. Altered or Synthetic Content: Select 'Yes' (contains synthetic narration).\n"
            f"8. Tags: {', '.join(metadata.tags) if metadata.tags else 'None'}\n"
            f"9. Visibility: Choose 'Schedule' and set release to: {metadata.publish_at or 'Preferred date/time'}\n"
            "10. Click 'Schedule'. Job publishing complete.\n"
        )
        with open(target_dir / "upload_instructions.txt", "w", encoding="utf-8") as f:
            f.write(instructions)

        # 5. Owner Alert Email Template
        email_content = (
            f"Subject: [GoldReel Action Needed] Video Ready for Upload: {metadata.title}\n\n"
            f"Hi Owner,\n\n"
            f"A new GoldReel video was produced and passed 100% of automated QC gates.\n"
            f"Because the YouTube API is currently in restricted/safe mode ({reason}), "
            f"the pipeline packaged all assets for manual release.\n\n"
            f"Package Location: {target_dir}\n"
            f"Video: {target_dir / 'video.mp4'}\n"
            f"Thumbnail: {target_dir / 'thumbnail.png'}\n"
            f"Target Scheduled Release: {metadata.publish_at}\n\n"
            "Follow the simple instructions in upload_instructions.txt to publish via YouTube Studio.\n\n"
            "- GoldReel Automated Pipeline\n"
        )
        with open(target_dir / "owner_alert_email.txt", "w", encoding="utf-8") as f:
            f.write(email_content)

        return target_dir
