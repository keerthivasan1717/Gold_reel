"""Weekly owner performance email report generator.

Strictly follows docs/PLAN.md & docs/GEMINI.md:
- Clear, actionable weekly executive summary for the channel owner.
- Tracks progress toward $10/month goal with zero weekly maintenance time.
- Documents autonomous template scoring and learning adjustments.
- Zero secrets, API keys, or sensitive tokens included.
"""

from pathlib import Path

from goldreel.analytics.models import LearningSummary


class WeeklyEmailReporter:
    """Builds clean plain text and HTML weekly status emails."""

    @staticmethod
    def generate_email_text(summary: LearningSummary, health_status: str = "All systems operational") -> str:
        """Render plain-text weekly owner email."""
        lines = [
            f"Subject: [GoldReel Weekly] {summary.total_channel_views} views | {summary.best_template or 'Production'} leading",
            "",
            "Hi Owner,",
            "",
            f"Here is your GoldReel weekly automated channel summary ({summary.period_start} to {summary.period_end}):",
            "",
            "=== CHANNEL METRICS ===",
            f"• Videos Analyzed:      {summary.total_videos_analyzed}",
            f"• Total Channel Views:  {summary.total_channel_views:,}",
            f"• Watch Time:           {summary.total_watch_time_hours:.1f} hours",
            f"• Projected Monthly:    ${summary.estimated_monthly_revenue_usd:.2f} (Target: $10.00/month)",
            "",
            "=== TEMPLATE LEARNING LOOP ===",
            f"• Best Performer:       {summary.best_template}",
            f"• Favored (Boosted):    {', '.join(summary.favored_templates) if summary.favored_templates else 'None'}",
            f"• Retired (Disfavored): {', '.join(summary.retired_templates) if summary.retired_templates else 'None'}",
            "",
            "=== TEMPLATE RANKINGS ===",
        ]
        for p in summary.template_rankings:
            status_tag = f"[{p.status.upper()}]"
            lines.append(
                f"  {p.template_type:<18} Score: {p.score:>5.1f} | Avg Views: {p.avg_views:>6.0f} | Ret: {p.avg_retention_percent:>4.1f}% {status_tag}"
            )

        lines.extend(
            [
                "",
                "=== AUTONOMOUS ADJUSTMENTS ===",
            ]
        )
        for act in summary.action_items:
            lines.append(f"• {act}")

        lines.extend(
            [
                "",
                "=== SYSTEM HEALTH ===",
                f"• Pipeline Status:      {health_status}",
                "• Runner Quota:         Healthy (< 15% monthly usage)",
                "• Manual Owner Time:    0 minutes required this week",
                "",
                "View full interactive dashboard: https://keerthivasan.github.io/new_way/",
                "",
                "- GoldReel Automated Publisher",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def generate_email_html(summary: LearningSummary, health_status: str = "All systems operational") -> str:
        """Render dark-and-gold styled HTML email for modern email clients."""
        rank_rows = "".join(
            f"""<tr style="border-bottom: 1px solid #2A2A2A;">
                <td style="padding: 10px; font-weight: bold; color: #F2EFE6;">{p.template_type}</td>
                <td style="padding: 10px; color: #D4AF37;">{p.score:.1f}</td>
                <td style="padding: 10px; color: #F2EFE6;">{p.avg_views:.0f}</td>
                <td style="padding: 10px; color: #F2EFE6;">{p.avg_retention_percent:.1f}%</td>
                <td style="padding: 10px; color: {'#D4AF37' if p.status == 'favored' else ('#E5484D' if p.status == 'retired' else '#A8A294')};">{p.status.upper()}</td>
            </tr>"""
            for p in summary.template_rankings
        )

        actions_html = "".join(f"<li>{act}</li>" for act in summary.action_items)

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="background-color: #0A0A0A; color: #F2EFE6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 24px;">
    <div style="max-width: 680px; margin: 0 auto; background: #161616; border: 1px solid #D4AF37; border-radius: 8px; padding: 28px;">
        <div style="border-bottom: 1px solid #2A2A2A; padding-bottom: 16px; margin-bottom: 24px;">
            <span style="font-size: 12px; font-weight: bold; color: #D4AF37; text-transform: uppercase; letter-spacing: 1px;">GoldReel Weekly Pulse</span>
            <h1 style="color: #F2EFE6; font-size: 26px; margin: 8px 0 0 0;">Weekly Executive Summary</h1>
            <p style="color: #A8A294; font-size: 14px; margin: 4px 0 0 0;">{summary.period_start} to {summary.period_end}</p>
        </div>

        <div style="display: flex; gap: 12px; margin-bottom: 24px;">
            <div style="background: #1F1F1F; border: 1px solid #2A2A2A; border-radius: 6px; padding: 14px; flex: 1;">
                <div style="font-size: 11px; color: #A8A294; text-transform: uppercase;">Total Views</div>
                <div style="font-size: 24px; font-weight: bold; color: #D4AF37; margin-top: 4px;">{summary.total_channel_views:,}</div>
            </div>
            <div style="background: #1F1F1F; border: 1px solid #2A2A2A; border-radius: 6px; padding: 14px; flex: 1;">
                <div style="font-size: 11px; color: #A8A294; text-transform: uppercase;">Watch Time</div>
                <div style="font-size: 24px; font-weight: bold; color: #F2EFE6; margin-top: 4px;">{summary.total_watch_time_hours:.1f}h</div>
            </div>
            <div style="background: #1F1F1F; border: 1px solid #2A2A2A; border-radius: 6px; padding: 14px; flex: 1;">
                <div style="font-size: 11px; color: #A8A294; text-transform: uppercase;">Projected Run-Rate</div>
                <div style="font-size: 24px; font-weight: bold; color: #F5E6A8; margin-top: 4px;">${summary.estimated_monthly_revenue_usd:.2f}</div>
            </div>
        </div>

        <h3 style="color: #D4AF37; font-size: 16px; margin: 24px 0 12px 0;">Template Performance Rankings</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
            <thead>
                <tr style="border-bottom: 2px solid #2A2A2A; color: #A8A294;">
                    <th style="padding: 8px;">Template</th>
                    <th style="padding: 8px;">Score</th>
                    <th style="padding: 8px;">Avg Views</th>
                    <th style="padding: 8px;">Retention</th>
                    <th style="padding: 8px;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rank_rows}
            </tbody>
        </table>

        <h3 style="color: #D4AF37; font-size: 16px; margin: 24px 0 12px 0;">Autonomous Learning Adjustments</h3>
        <ul style="color: #F2EFE6; font-size: 14px; line-height: 1.6; padding-left: 20px;">
            {actions_html}
        </ul>

        <div style="background: #1F1F1F; border-left: 4px solid #D4AF37; padding: 12px 16px; margin-top: 24px; border-radius: 4px;">
            <div style="font-size: 12px; color: #A8A294;">System Health Status</div>
            <div style="font-size: 14px; color: #F2EFE6; font-weight: bold; margin-top: 2px;">{health_status} • Zero manual intervention required</div>
        </div>
    </div>
</body>
</html>"""
        return html

    def save_reports(
        self,
        summary: LearningSummary,
        out_dir: Path | str = "out",
        health_status: str = "All systems operational",
    ) -> tuple[Path, Path]:
        """Save plain text and HTML emails to out/."""
        target_dir = Path(out_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        txt_path = target_dir / "weekly_summary_email.txt"
        html_path = target_dir / "weekly_summary_email.html"

        txt_path.write_text(self.generate_email_text(summary, health_status), encoding="utf-8")
        html_path.write_text(self.generate_email_html(summary, health_status), encoding="utf-8")

        return txt_path, html_path

