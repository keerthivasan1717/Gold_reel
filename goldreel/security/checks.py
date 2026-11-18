"""Secret scanning and safety checks.

Ensures no private keys, API secrets, or forbidden files (.env, credentials)
are committed, tracked, or present in project files as required by GEMINI.md.
"""

import re
import subprocess
from pathlib import Path

# Suspicious token regexes
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Private key block"),
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google API key pattern"),
    (re.compile(r"gsk_[a-zA-Z0-9]{30,}"), "Groq API key pattern"),
    (re.compile(r"sk-[a-zA-Z0-9]{32,}"), "Secret key pattern"),
    (
        re.compile(
            r"""(?i)(?:api_key|client_secret|access_token|private_key)\s*[:=]\s*["'][a-zA-Z0-9_\-]{20,}["']"""
        ),
        "API/Client secret pattern",
    ),
]

FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    "config/local.json",
    "youtube_credentials.json",
    "youtube_token.json",
    "client_secrets.json",
}

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    "cache",
    "state",
    "out",
    "docs-site",
    "tests",
}


def get_git_tracked_files(repo_root: Path) -> list[Path] | None:
    """Retrieve list of files tracked by git if git repository exists."""
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            files: list[Path] = []
            for line in res.stdout.splitlines():
                if line.strip():
                    files.append(repo_root / line.strip())
            return files
    except Exception:
        pass
    return None


def scan_for_secrets(project_root: Path | None = None) -> list[str]:
    """Scan tracked and project files for exposed secrets or forbidden credentials files."""
    root = (project_root or Path.cwd()).resolve()
    violations: list[str] = []

    # 1. Check for tracked forbidden filenames
    tracked = get_git_tracked_files(root)
    if tracked is not None:
        files_to_check = []
        for f in tracked:
            if any(part in IGNORE_DIRS for part in f.parts):
                continue
            files_to_check.append(f)
            rel = str(f.relative_to(root)).replace("\\", "/")
            if rel in FORBIDDEN_FILENAMES or f.name in FORBIDDEN_FILENAMES:
                violations.append(f"Forbidden sensitive file is tracked in git: {rel}")
    else:
        # Fallback to traversing files
        files_to_check = []
        for p in root.rglob("*"):
            if p.is_file():
                if any(part in IGNORE_DIRS for part in p.parts):
                    continue
                files_to_check.append(p)
                rel = str(p.relative_to(root)).replace("\\", "/")
                if rel in FORBIDDEN_FILENAMES or p.name in FORBIDDEN_FILENAMES:
                    violations.append(f"Forbidden sensitive file found: {rel}")

    # 2. Check file content
    for file_path in files_to_check:
        if not file_path.is_file():
            continue
        # Skip binary files, sample fixtures, or large assets
        if file_path.suffix in {".ttf", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".zip", ".gz"}:
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, label in SECRET_PATTERNS:
            if pattern.search(content):
                rel = str(file_path.relative_to(root)).replace("\\", "/")
                violations.append(f"{label} detected in {rel}")

    return violations


def ensure_no_secrets_or_raise(project_root: Path | None = None) -> None:
    """Startup verification: raises RuntimeError if any secret pattern is found."""
    violations = scan_for_secrets(project_root)
    if violations:
        msg = "Security check failed - secret or credential detected:\n" + "\n".join(violations)
        raise RuntimeError(msg)
