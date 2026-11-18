"""Metadata Quality Control (QC) validating title, description, synthetic disclosure, and duration."""

import re

from goldreel.qc.models import QCCheckItem


class MetadataQC:
    """Automated metadata linter and duration compliance gate."""

    BANNED_TITLE_WORDS = [
        "SHOCKING",
        "CLICK HERE",
        "FREE MONEY",
        "MUST SEE",
        "SUBSCRIBE NOW",
        "YOU WON'T BELIEVE",
        "VIRAL",
        "INSANE HACK",
    ]

    def check_title(self, title: str) -> list[QCCheckItem]:
        """Verify title length, casing, and absence of clickbait spam."""
        checks: list[QCCheckItem] = []
        clean_title = title.strip()

        # Length check
        length_pass = 10 <= len(clean_title) <= 100
        checks.append(
            QCCheckItem(
                name="title_length",
                category="metadata",
                passed=length_pass,
                severity="critical",
                message=f"Title length is {len(clean_title)} chars (target: 10-100)",
                measured_value=len(clean_title),
                target_value="10 to 100 chars",
            )
        )

        # Casing check (no excessive all-caps)
        letters = [c for c in clean_title if c.isalpha()]
        if letters:
            upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            casing_pass = upper_ratio <= 0.70
            checks.append(
                QCCheckItem(
                    name="title_casing",
                    category="metadata",
                    passed=casing_pass,
                    severity="warning",
                    message=f"Uppercase letter ratio is {upper_ratio:.1%} (max allowed: 70.0%)",
                    measured_value=round(upper_ratio, 2),
                    target_value="<= 0.70",
                )
            )

        # Banned buzzwords
        found_banned = [w for w in self.BANNED_TITLE_WORDS if w in clean_title.upper()]
        checks.append(
            QCCheckItem(
                name="title_editorial_quality",
                category="metadata",
                passed=len(found_banned) == 0,
                severity="critical",
                message="Title adheres to editorial quality standards"
                if not found_banned
                else f"Title contains prohibited spam keyword(s): {', '.join(found_banned)}",
                measured_value=found_banned,
            )
        )

        return checks

    def check_description(self, description: str) -> list[QCCheckItem]:
        """Verify attributions, synthetic disclosure, and hashtag limits."""
        checks: list[QCCheckItem] = []
        desc_lower = description.lower()

        # 1. Source attribution presence
        has_source = any(
            k in desc_lower
            for k in [
                "source:",
                "data provided by",
                "cricsheet",
                "wikidata",
                "football-data",
                "adapted from",
            ]
        )
        checks.append(
            QCCheckItem(
                name="source_attribution_present",
                category="metadata",
                passed=has_source,
                severity="critical",
                message="Data provenance attribution verified in description"
                if has_source
                else "Missing required data source attribution in description",
            )
        )

        # 2. Music attribution presence
        has_music = any(
            k in desc_lower
            for k in [
                "music:",
                "license",
                "creative commons",
                "cc by",
                "free music archive",
                "pixabay",
            ]
        )
        checks.append(
            QCCheckItem(
                name="music_attribution_present",
                category="metadata",
                passed=has_music,
                severity="critical",
                message="Music license attribution verified in description"
                if has_music
                else "Missing required music copyright/license attribution in description",
            )
        )

        # 3. Synthetic content disclosure (YouTube requirement)
        has_synthetic = any(
            k in desc_lower
            for k in [
                "synthetic",
                "automated data",
                "piper tts",
                "ai narration",
                "automated pipeline",
            ]
        )
        checks.append(
            QCCheckItem(
                name="synthetic_content_disclosure",
                category="metadata",
                passed=has_synthetic,
                severity="critical",
                message="Synthetic narration / automated visualization disclosure present"
                if has_synthetic
                else "Missing mandatory synthetic content disclosure statement",
            )
        )

        # 4. Length limits
        length_pass = len(description) <= 5000
        checks.append(
            QCCheckItem(
                name="description_length",
                category="metadata",
                passed=length_pass,
                severity="critical",
                message=f"Description length is {len(description)} chars (limit: <= 5000)",
                measured_value=len(description),
                target_value="<= 5000",
            )
        )

        # 5. Hashtag limits (YouTube ignores all tags if > 15)
        hashtags = re.findall(r"#\w+", description)
        tags_pass = len(hashtags) <= 15
        checks.append(
            QCCheckItem(
                name="hashtag_count",
                category="metadata",
                passed=tags_pass,
                severity="warning",
                message=f"Contains {len(hashtags)} hashtag(s) (max recommended: 15)",
                measured_value=len(hashtags),
                target_value="<= 15",
            )
        )

        return checks

    def check_duration(
        self,
        duration_sec: float,
        format_type: str = "landscape",
        is_dry_run: bool = False,
    ) -> list[QCCheckItem]:
        """Validate video duration against platform and lane constraints."""
        checks: list[QCCheckItem] = []

        if format_type == "portrait":
            # YouTube Shorts hard ceiling: 60.0s
            hard_limit_pass = duration_sec <= 60.0
            checks.append(
                QCCheckItem(
                    name="short_hard_ceiling",
                    category="duration",
                    passed=hard_limit_pass,
                    severity="critical",
                    message=f"Short duration {duration_sec:.1f}s <= 60.0s hard YouTube Shorts limit",
                    measured_value=round(duration_sec, 2),
                    target_value="<= 60.0s",
                )
            )

            if not is_dry_run:
                target_pass = 30.0 <= duration_sec <= 45.0
                checks.append(
                    QCCheckItem(
                        name="short_target_duration",
                        category="duration",
                        passed=target_pass,
                        severity="warning",
                        message=f"Short duration {duration_sec:.1f}s within target 30-45s cadence",
                        measured_value=round(duration_sec, 2),
                        target_value="30.0 to 45.0s",
                    )
                )
            else:
                checks.append(
                    QCCheckItem(
                        name="preview_duration",
                        category="duration",
                        passed=duration_sec >= 1.0,
                        severity="critical",
                        message=f"Preview duration {duration_sec:.1f}s is valid",
                        measured_value=round(duration_sec, 2),
                    )
                )
        else:
            # Landscape long-form
            if not is_dry_run:
                target_pass = 120.0 <= duration_sec <= 200.0
                checks.append(
                    QCCheckItem(
                        name="longform_target_duration",
                        category="duration",
                        passed=target_pass,
                        severity="warning",
                        message=f"Long video duration {duration_sec:.1f}s within target 160-200s cadence",
                        measured_value=round(duration_sec, 2),
                        target_value="160.0 to 200.0s",
                    )
                )
            else:
                checks.append(
                    QCCheckItem(
                        name="preview_duration",
                        category="duration",
                        passed=duration_sec >= 1.0,
                        severity="critical",
                        message=f"Preview duration {duration_sec:.1f}s is valid",
                        measured_value=round(duration_sec, 2),
                    )
                )

        return checks
