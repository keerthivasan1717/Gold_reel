"""State store for pipeline jobs.

Manages idempotent, resumable job directories under state/<job_id>/ with plain file artifacts,
hashes, and stage completion tracking.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field

StageStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class StageRecord(BaseModel):
    status: StageStatus = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    content_hash: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobManifest(BaseModel):
    job_id: str
    created_at: str
    updated_at: str
    stages: dict[str, StageRecord] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)


def compute_content_hash(data: str | bytes | dict | list) -> str:
    """Compute sha256 hex digest for arbitrary input."""
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, sort_keys=True, ensure_ascii=True).encode("utf-8")
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    elif isinstance(data, bytes):
        payload = data
    else:
        payload = str(data).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class JobState:
    """Encapsulates state, files, and stage tracking for a single job run."""

    def __init__(self, job_dir: Path, manifest: JobManifest):
        self.job_dir = job_dir
        self.manifest = manifest

    @property
    def job_id(self) -> str:
        return self.manifest.job_id

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_manifest(self) -> None:
        self.manifest.updated_at = self._now_iso()
        manifest_path = self.job_dir / "manifest.json"
        tmp_path = self.job_dir / "manifest.json.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(self.manifest.model_dump_json(indent=2))
        tmp_path.replace(manifest_path)

    def mark_stage_start(self, stage: str) -> None:
        rec = self.manifest.stages.get(stage, StageRecord())
        rec.status = "running"
        rec.started_at = self._now_iso()
        rec.error = None
        self.manifest.stages[stage] = rec
        self.save_manifest()

    def mark_stage_completed(
        self,
        stage: str,
        content_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        rec = self.manifest.stages.get(stage, StageRecord())
        rec.status = "completed"
        rec.completed_at = self._now_iso()
        if content_hash:
            rec.content_hash = content_hash
        if metadata:
            rec.metadata.update(metadata)
        self.manifest.stages[stage] = rec
        self.save_manifest()

    def mark_stage_failed(self, stage: str, error: str) -> None:
        rec = self.manifest.stages.get(stage, StageRecord())
        rec.status = "failed"
        rec.completed_at = self._now_iso()
        rec.error = error
        self.manifest.stages[stage] = rec
        self.save_manifest()

    def is_stage_completed(self, stage: str, expected_hash: str | None = None) -> bool:
        rec = self.manifest.stages.get(stage)
        if not rec or rec.status != "completed":
            return False
        if expected_hash is not None:
            return rec.content_hash == expected_hash
        return True

    def save_artifact(self, filename: str, content: str | bytes | dict | list) -> Path:
        """Save artifact file within the job directory and register in manifest."""
        target = self.job_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, (dict, list)):
            with open(target, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, default=str)
        elif isinstance(content, str):
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        elif isinstance(content, bytes):
            with open(target, "wb") as f:
                f.write(content)
        else:
            with open(target, "w", encoding="utf-8") as f:
                f.write(str(content))

        rel_path = str(target.relative_to(self.job_dir))
        if rel_path not in self.manifest.artifacts:
            self.manifest.artifacts.append(rel_path)
            self.save_manifest()

        return target

    def register_existing_file(self, file_path: Path) -> Path:
        """Register an existing file within job_dir into the manifest."""
        rel_path = str(file_path.relative_to(self.job_dir))
        if rel_path not in self.manifest.artifacts:
            self.manifest.artifacts.append(rel_path)
            self.save_manifest()
        return file_path

    def load_artifact(self, filename: str) -> Any:
        """Load artifact file from the job directory."""
        target = self.job_dir / filename
        if not target.exists():
            raise FileNotFoundError(f"Artifact not found: {target}")

        if target.suffix == ".json":
            with open(target, encoding="utf-8") as f:
                return json.load(f)
        return target.read_text(encoding="utf-8")


class StateStore:
    """Manages creation, retrieval, and listing of pipeline jobs."""

    def __init__(self, base_dir: Path | str = "state"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_job(self, job_id: str | None = None) -> JobState:
        jid = job_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        job_dir = self.base_dir / jid
        if job_dir.exists():
            raise FileExistsError(f"Job already exists: {jid}")
        job_dir.mkdir(parents=True, exist_ok=False)

        now = datetime.now(timezone.utc).isoformat()
        manifest = JobManifest(
            job_id=jid,
            created_at=now,
            updated_at=now,
            stages={},
            artifacts=[],
        )
        state = JobState(job_dir, manifest)
        state.save_manifest()
        return state

    def get_job(self, job_id: str) -> JobState:
        job_dir = self.base_dir / job_id
        manifest_path = job_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Job manifest not found for {job_id}")

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        manifest = JobManifest.model_validate(data)
        return JobState(job_dir, manifest)

    def list_jobs(self) -> list[JobManifest]:
        jobs: list[JobManifest] = []
        if not self.base_dir.exists():
            return jobs
        for job_dir in sorted(self.base_dir.iterdir(), reverse=True):
            manifest_file = job_dir / "manifest.json"
            if job_dir.is_dir() and manifest_file.exists():
                try:
                    with open(manifest_file, encoding="utf-8") as f:
                        data = json.load(f)
                    jobs.append(JobManifest.model_validate(data))
                except Exception:
                    continue
        return jobs

