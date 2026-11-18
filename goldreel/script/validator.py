"""Validation engine for generated scripts.

Enforces:
1. Fact Gate pass (every number and date verified in FactTable).
2. Pacing & duration constraints (landscape 120-180s, portrait 30-45s).
3. Mandatory stated original insight (non-negotiable per docs/GEMINI.md).
"""

from dataclasses import dataclass, field

from goldreel.facts.gate import FactGate, FactGateResult
from goldreel.facts.models import FactTable
from goldreel.script.models import GeneratedScript


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    word_count: int = 0
    fact_gate_result: FactGateResult | None = None

    @property
    def summary(self) -> str:
        if self.passed:
            return f"VALIDATION PASSED (word_count={self.word_count})"
        return f"VALIDATION FAILED with {len(self.violations)} violation(s):\n" + "\n".join(
            f"  - {v}" for v in self.violations
        )


class ScriptValidator:
    """Validates structural, factual, and pacing compliance of a GeneratedScript."""

    def __init__(self, fact_table: FactTable):
        self.fact_table = fact_table
        self.gate = FactGate(fact_table)

    def validate(
        self,
        script: GeneratedScript,
        min_duration_sec: float | None = None,
        max_duration_sec: float | None = None,
    ) -> ValidationResult:
        violations: list[str] = []

        # 1. Fact Gate Check
        gate_res = self.gate.verify_script(script.model_dump())
        if not gate_res.passed:
            violations.extend(gate_res.violations)

        # 2. Mandatory Insight Check
        if not script.insight or len(script.insight.strip().split()) < 3:
            violations.append(
                "Script lacks a valid stated analytical insight (minimum 3 words required)."
            )

        # 3. Word Count & Duration Pacing Check
        total_words = script.total_words
        # Words per second bounds: 1.8 to 2.8 words/sec
        min_words = int(min_duration_sec * 1.8) if min_duration_sec else 40
        max_words = int(max_duration_sec * 2.8) if max_duration_sec else 500

        if total_words < min_words:
            violations.append(
                f"Script is too brief: {total_words} words (minimum {min_words} words required for target duration)."
            )
        elif total_words > max_words:
            violations.append(
                f"Script is too verbose: {total_words} words (maximum {max_words} words allowed for target duration)."
            )

        # 4. Outro & Credits Check
        if not script.outro_text or len(script.outro_text.strip()) < 5:
            violations.append("Script lacks proper dataset outro attribution.")

        passed = len(violations) == 0
        return ValidationResult(
            passed=passed,
            violations=violations,
            word_count=total_words,
            fact_gate_result=gate_res,
        )
