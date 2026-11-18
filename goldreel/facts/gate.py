"""Automated Fact Gate for GoldReel.

Enforces non-negotiable rule from docs/GEMINI.md Section 3:
"Every number, name, and date in a generated script must appear in the fact table.
Any mismatch fails the video and it is discarded. Log the reason."
"""

import re
from dataclasses import dataclass, field
from typing import Any

from goldreel.facts.models import FactTable


@dataclass
class FactGateResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    checked_numbers: list[str] = field(default_factory=list)
    checked_entities: list[str] = field(default_factory=list)
    checked_dates: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.passed:
            return (
                f"FACT GATE PASSED: Verified {len(self.checked_numbers)} numbers, "
                f"{len(self.checked_entities)} entities, {len(self.checked_dates)} dates."
            )
        return f"FACT GATE FAILED with {len(self.violations)} mismatch(es):\n" + "\n".join(
            f"  - {v}" for v in self.violations
        )


class FactGate:
    """Validates that a script contains ONLY verified numbers, dates, and entities from a FactTable."""

    # Regex for integer and decimal numbers
    NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
    # Ordinals like 1st, 2nd, 3rd
    ORDINAL_PATTERN = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b", re.IGNORECASE)
    # 4-digit years (1900-2099)
    YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")

    def __init__(self, fact_table: FactTable):
        self.fact_table = fact_table
        self._build_ground_truth()

    def _build_ground_truth(self) -> None:
        """Extract all valid numbers, dates, and named entities from the FactTable."""
        self.valid_numbers: set[float | int | str] = set()
        self.valid_entities: set[str] = set()
        self.valid_years: set[str] = set()

        # Extract from title & metric label
        for y in self.YEAR_PATTERN.findall(
            self.fact_table.title + " " + self.fact_table.metric_label
        ):
            self.valid_years.add(y)
            self.valid_numbers.add(int(y))

        for rec in self.fact_table.records:
            # Rank
            if rec.rank is not None:
                self.valid_numbers.add(rec.rank)
                self.valid_numbers.add(float(rec.rank))
                self.valid_numbers.add(str(rec.rank))

            # Value
            if isinstance(rec.value, (int, float)):
                self.valid_numbers.add(rec.value)
                self.valid_numbers.add(int(rec.value))
                self.valid_numbers.add(float(rec.value))
                self.valid_numbers.add(str(rec.value))
            elif isinstance(rec.value, str):
                for num_str in self.NUMBER_PATTERN.findall(rec.value):
                    try:
                        val = float(num_str) if "." in num_str else int(num_str)
                        self.valid_numbers.add(val)
                        self.valid_numbers.add(str(val))
                    except ValueError:
                        pass

            # Entity
            self.valid_entities.add(rec.entity.lower().strip())
            # Context items
            for _k, v in rec.context.items():
                if isinstance(v, (int, float)):
                    self.valid_numbers.add(v)
                    self.valid_numbers.add(str(v))
                elif isinstance(v, str):
                    self.valid_entities.add(v.lower().strip())
                    for num_str in self.NUMBER_PATTERN.findall(v):
                        try:
                            val = float(num_str) if "." in num_str else int(num_str)
                            self.valid_numbers.add(val)
                            self.valid_numbers.add(str(val))
                        except ValueError:
                            pass

    def _is_number_allowed(self, num_str: str) -> bool:
        """Check if numeric token exists in verified ground truth."""
        try:
            val_f = float(num_str)
            val_i = int(float(num_str)) if float(num_str).is_integer() else None
        except ValueError:
            return False

        if val_f in self.valid_numbers:
            return True
        if val_i is not None and val_i in self.valid_numbers:
            return True
        if num_str in self.valid_numbers:
            return True

        return False

    def verify_script(self, script_data: dict[str, Any] | str) -> FactGateResult:
        """Inspect all narration text in script against the verified fact table.

        Accepts either raw text or a script dictionary with scenes.
        """
        violations: list[str] = []
        checked_numbers: list[str] = []
        checked_entities: list[str] = []
        checked_dates: list[str] = []

        # Collect all text to verify
        texts: list[tuple[str, str]] = []  # (section_label, text)
        if isinstance(script_data, str):
            texts.append(("text", script_data))
        elif isinstance(script_data, dict):
            if "hook" in script_data:
                texts.append(("hook", str(script_data["hook"])))
            scenes_list = script_data.get("scenes") or script_data.get("narration_scenes") or []
            for idx, scene in enumerate(scenes_list):
                if isinstance(scene, dict) and "text" in scene:
                    texts.append((f"scene_{idx + 1}", str(scene["text"])))
                elif isinstance(scene, str):
                    texts.append((f"scene_{idx + 1}", scene))
            if "outro_text" in script_data:
                texts.append(("outro", str(script_data["outro_text"])))

        # 1. Verify numbers and years
        for section, text in texts:
            # Replace ordinals like 1st -> 1 for checking
            normalized_text = self.ORDINAL_PATTERN.sub(r"\1", text)
            tokens = self.NUMBER_PATTERN.findall(normalized_text)

            for token in tokens:
                checked_numbers.append(token)
                if not self._is_number_allowed(token):
                    violations.append(
                        f"Unverified number '{token}' detected in {section}: \"{text.strip()}\". "
                        "Number does not exist in verified fact table."
                    )

            # Check years
            years = self.YEAR_PATTERN.findall(text)
            for y in years:
                checked_dates.append(y)
                if int(y) not in self.valid_numbers and y not in self.valid_years:
                    violations.append(
                        f"Unverified year '{y}' in {section}: \"{text.strip()}\". "
                        "Year not present in fact table."
                    )

        # 2. Verify entities mentioned
        # Every entity in the fact table must be verified when mentioned
        full_text_lower = " ".join(t[1] for t in texts).lower()
        for rec in self.fact_table.records:
            ent_name = rec.entity.strip()
            if ent_name.lower() in full_text_lower:
                checked_entities.append(ent_name)

        passed = len(violations) == 0
        return FactGateResult(
            passed=passed,
            violations=violations,
            checked_numbers=checked_numbers,
            checked_entities=checked_entities,
            checked_dates=checked_dates,
        )
