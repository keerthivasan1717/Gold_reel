"""Tests for static dashboard generation and design token compliance."""

from pathlib import Path

from goldreel.dashboard.generator import DashboardGenerator


def test_dashboard_generates_valid_html_and_css(tmp_path: Path):
    """Verify DashboardGenerator compiles docs-site/ with design tokens and required sections."""
    out_dir = tmp_path / "docs-site"
    gen = DashboardGenerator(out_dir=out_dir)
    html_p, css_p = gen.generate()

    assert html_p.exists()
    assert css_p.exists()

    # Verify CSS contains required tokens from tokens.py
    css_content = css_p.read_text(encoding="utf-8")
    assert "--bg:#0a0a0a" in css_content or "--bg: #0a0a0a" in css_content
    assert "--gold:#d4af37" in css_content or "--gold: #d4af37" in css_content
    assert "--ivory:#f2efe6" in css_content or "--ivory: #f2efe6" in css_content
    assert "--line:#2a2a2a" in css_content or "--line: #2a2a2a" in css_content
    assert "--glow:0 0 18px rgba(212,175,55,.35)" in css_content or "18px" in css_content

    # Verify HTML contains all 5 sections from docs/DESIGN.md Section 9
    html_content = html_p.read_text(encoding="utf-8")

    # 1. Status strip
    assert "LAST RUN" in html_content
    assert "NEXT SCHEDULED RELEASE" in html_content
    assert "PUBLISH MODE" in html_content

    # 2. Pipeline board
    assert "Latest Pipeline Run:" in html_content
    assert "pipeline-scroll" in html_content
    assert "stage-card" in html_content

    # 3. Template performance scores
    assert "Template Performance" in html_content
    assert "Autonomous Learning Loop" in html_content
    assert "bar-container" in html_content

    # 4. System health and safety
    assert "System Health & Safety" in html_content
    assert "Cricsheet DB" in html_content
    assert "CI Runner Quota" in html_content

    # 5. Production History and metrics
    assert "Production History & Metrics" in html_content
    assert "data-table" in html_content
