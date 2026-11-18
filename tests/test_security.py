"""Tests for GoldReel security secret scanning."""

import pytest

from goldreel.security.checks import (
    ensure_no_secrets_or_raise,
    scan_for_secrets,
)


def test_clean_repo_passes_scan(tmp_path):
    # Empty or clean directory
    (tmp_path / "hello.py").write_text("print('clean code')", encoding="utf-8")
    violations = scan_for_secrets(tmp_path)
    assert len(violations) == 0
    ensure_no_secrets_or_raise(tmp_path)


def test_forbidden_credentials_file_detected(tmp_path):
    (tmp_path / ".env").write_text("SOME_SECRET=12345", encoding="utf-8")
    violations = scan_for_secrets(tmp_path)
    assert any(".env" in v for v in violations)

    with pytest.raises(RuntimeError):
        ensure_no_secrets_or_raise(tmp_path)


def test_private_key_pattern_detected(tmp_path):
    fake_key_file = tmp_path / "compromised.pem"
    fake_key_file.write_text(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...", encoding="utf-8"
    )
    violations = scan_for_secrets(tmp_path)
    assert any("Private key" in v for v in violations)

    with pytest.raises(RuntimeError):
        ensure_no_secrets_or_raise(tmp_path)
