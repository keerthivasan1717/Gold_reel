"""Comprehensive repository security scanner and hardening auditor.

Strictly enforces GEMINI.md Section 6:
- Zero secrets committed, tracked, logged, or published.
- Scans working directory, git index, git commit history, and public artifacts (docs-site/, out/).
- Enforces strict protection for .env, youtube_credentials.json, and private keys.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from goldreel.security.checks import FORBIDDEN_FILENAMES, SECRET_PATTERNS


@dataclass
class SecurityAuditReport:
    """Detailed results of the security audit."""

    passed: bool
    tracked_violations: list[str] = field(default_factory=list)
    history_violations: list[str] = field(default_factory=list)
    artifact_violations: list[str] = field(default_factory=list)
    untracked_risks: list[str] = field(default_factory=list)

    @property
    def total_violations(self) -> int:
        return (
            len(self.tracked_violations)
            + len(self.history_violations)
            + len(self.artifact_violations)
        )


class RepositorySecurityScanner:
    """Performs deep static analysis across working tree, git log, and build artifacts."""

    def __init__(self, repo_root: Path | str | None = None):
        self.root = Path(repo_root or Path.cwd()).resolve()

    def scan_git_history(self, max_commits: int = 50) -> list[str]:
        """Scan recent git commit diffs for accidental credentials."""
        violations: list[str] = []
        try:
            res = subprocess.run(
                ["git", "log", f"-n{max_commits}", "-p", "--no-color"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                return violations

            current_commit = "HEAD"
            current_file = ""
            for line in res.stdout.splitlines():
                if line.startswith("commit "):
                    current_commit = line.split()[1][:8]
                elif line.startswith("+++ b/"):
                    current_file = line[6:]
                elif line.startswith("+") and not line.startswith("+++"):
                    if current_file.startswith("tests/") or current_file.startswith("goldreel/security/"):
                        continue
                    added_text = line[1:]
                    for pattern, label in SECRET_PATTERNS:
                        if pattern.search(added_text):
                            violations.append(
                                f"Secret pattern '{label}' detected in commit {current_commit} ({current_file})"
                            )
                            break
        except Exception as e:
            violations.append(f"Git history scan error: {e}")
        return violations

    def scan_artifacts(self) -> list[str]:
        """Ensure no secrets or tokens exist in public build outputs or logs."""
        violations: list[str] = []
        public_dirs = [self.root / "docs-site", self.root / "out"]

        for pub_dir in public_dirs:
            if not pub_dir.exists():
                continue
            for f in pub_dir.rglob("*"):
                if f.is_file() and f.suffix in {".html", ".css", ".txt", ".json", ".log"}:
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        for pattern, label in SECRET_PATTERNS:
                            if pattern.search(content):
                                rel = f.relative_to(self.root)
                                violations.append(
                                    f"Secret pattern '{label}' leaked into build artifact: {rel}"
                                )
                                break
                    except Exception:
                        pass
        return violations

    def check_untracked_secrets(self) -> list[str]:
        """Check if any sensitive credentials exist untracked and verify they are git-ignored."""
        risks: list[str] = []
        for forbidden in FORBIDDEN_FILENAMES:
            target = self.root / forbidden
            if target.exists():
                # Verify git-ignore status
                res = subprocess.run(
                    ["git", "check-ignore", "-q", str(target)],
                    cwd=self.root,
                    capture_output=True,
                    check=False,
                )
                if res.returncode != 0:
                    risks.append(f"Sensitive file {forbidden} exists on disk but is NOT git-ignored!")
        return risks

    def run_full_audit(self) -> SecurityAuditReport:
        """Run complete repository security scan."""
        from goldreel.security.checks import scan_for_secrets

        tracked_violations = scan_for_secrets(self.root)
        history_violations = self.scan_git_history()
        artifact_violations = self.scan_artifacts()
        untracked_risks = self.check_untracked_secrets()

        passed = (
            len(tracked_violations) == 0
            and len(history_violations) == 0
            and len(artifact_violations) == 0
            and len(untracked_risks) == 0
        )

        return SecurityAuditReport(
            passed=passed,
            tracked_violations=tracked_violations,
            history_violations=history_violations,
            artifact_violations=artifact_violations,
            untracked_risks=untracked_risks,
        )
