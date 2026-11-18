"""Template performance scoring and autonomous learning loop."""

from datetime import UTC, datetime, timedelta

from goldreel.analytics.models import LearningSummary, TemplatePerformance, VideoAnalyticsRecord


class TemplateScorer:
    """Scores visual template performance and optimizes production selection weights."""

    RETIREMENT_THRESHOLD = 40.0
    FAVORED_THRESHOLD = 65.0
    MIN_VIDEOS_FOR_RETIREMENT = 2

    def score_templates(self, records: list[VideoAnalyticsRecord]) -> list[TemplatePerformance]:
        """Compute aggregate performance and weighted scores across templates."""
        if not records:
            # Return baseline neutral scores for standard templates
            return [
                TemplatePerformance(template_type="stat_race", score=70.0, status="favored", recommendation="Strong baseline viewer retention"),
                TemplatePerformance(template_type="ranked_countdown", score=50.0, status="neutral", recommendation="Standard countdown engagement"),
                TemplatePerformance(template_type="scroll_compare", score=68.0, status="favored", recommendation="High retention portrait Short format"),
                TemplatePerformance(template_type="milestone", score=45.0, status="neutral", recommendation="Solid milestone callout"),
            ]

        # Group records by template_type
        by_template: dict[str, list[VideoAnalyticsRecord]] = {}
        for r in records:
            by_template.setdefault(r.template_type, []).append(r)

        # Calculate max metrics for relative normalization
        max_avg_views = max(sum(r.views for r in group) / len(group) for group in by_template.values()) or 1.0
        max_avg_ret = max(sum(r.retention_percent for r in group) / len(group) for group in by_template.values()) or 1.0
        max_avg_ctr = max(sum(r.ctr_percent for r in group) / len(group) for group in by_template.values()) or 1.0

        performances: list[TemplatePerformance] = []
        for t_type, group in by_template.items():
            count = len(group)
            total_v = sum(r.views for r in group)
            avg_v = total_v / count
            avg_w = sum(r.watch_time_hours for r in group) / count
            avg_ret = sum(r.retention_percent for r in group) / count
            avg_ctr = sum(r.ctr_percent for r in group) / count

            # Normalized component scores (0.0 to 100.0)
            norm_v = (avg_v / max_avg_views) * 100.0
            norm_ret = (avg_ret / max_avg_ret) * 100.0
            norm_ctr = (avg_ctr / max_avg_ctr) * 100.0

            # Composite weighted formula: 40% views, 40% retention, 20% CTR
            composite_score = round(0.40 * norm_v + 0.40 * norm_ret + 0.20 * norm_ctr, 1)

            # Determine status
            if composite_score >= self.FAVORED_THRESHOLD:
                status = "favored"
                rec = f"Top performer (Score {composite_score}). Boost production allocation."
            elif composite_score < self.RETIREMENT_THRESHOLD and count >= self.MIN_VIDEOS_FOR_RETIREMENT:
                status = "retired"
                rec = f"Low performance (Score {composite_score} across {count} videos). Deprioritize."
            else:
                status = "neutral"
                rec = f"Stable engagement (Score {composite_score}). Continue monitoring."

            performances.append(
                TemplatePerformance(
                    template_type=t_type,
                    video_count=count,
                    total_views=total_v,
                    avg_views=round(avg_v, 1),
                    avg_watch_time_hours=round(avg_w, 2),
                    avg_retention_percent=round(avg_ret, 1),
                    avg_ctr_percent=round(avg_ctr, 1),
                    score=composite_score,
                    status=status,
                    recommendation=rec,
                )
            )

        # Sort descending by score
        performances.sort(key=lambda p: p.score, reverse=True)
        return performances

    def generate_learning_summary(
        self,
        records: list[VideoAnalyticsRecord],
        days: int = 7,
    ) -> LearningSummary:
        """Synthesize weekly channel performance and template adjustments."""
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        rankings = self.score_templates(records)

        total_vids = len(records)
        total_views = sum(r.views for r in records)
        total_watch = round(sum(r.watch_time_hours for r in records), 2)
        total_rev = round(sum(r.estimated_revenue_usd for r in records), 2)

        favored = [p.template_type for p in rankings if p.status == "favored"]
        retired = [p.template_type for p in rankings if p.status == "retired"]
        best = rankings[0].template_type if rankings else None

        actions = []
        if favored:
            actions.append(f"Allocate 60% of next week's schedule to favored templates: {', '.join(favored)}.")
        if retired:
            actions.append(f"Deprioritize weak templates from automated rotation: {', '.join(retired)}.")
        if not actions:
            actions.append("Maintain balanced template distribution while collecting audience retention signals.")

        return LearningSummary(
            period_start=start_date,
            period_end=end_date,
            total_videos_analyzed=total_vids,
            total_channel_views=total_views,
            total_watch_time_hours=total_watch,
            estimated_monthly_revenue_usd=round(total_rev * (30.0 / max(1, days)), 2),
            template_rankings=rankings,
            best_template=best,
            retired_templates=retired,
            favored_templates=favored,
            action_items=actions,
        )

