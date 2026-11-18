"""AI Provider router with automatic fallback chain and rate limit handling.

Reads provider chain and models from config/providers.json.
Supports Google Gemini, Groq, and a deterministic offline synthesizer for local/CI dry-runs.
"""

import json
import logging
import os
from typing import Any

import httpx

from goldreel.config.loader import ProvidersConfig, load_providers_config
from goldreel.facts.models import FactTable
from goldreel.script.models import GeneratedScript, ScriptScene
from goldreel.script.prompts import SYSTEM_PROMPT, build_script_prompt

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Manages AI provider calls with automatic fallback across the chain."""

    def __init__(self, providers_config: ProvidersConfig | None = None):
        self.config = providers_config or load_providers_config()

    def generate_script(
        self,
        fact_table: FactTable,
        format_type: str = "landscape",
        target_duration_sec: int = 150,
        template_type: str = "stat_race",
    ) -> GeneratedScript:
        """Attempt generation through provider chain; fall back to deterministic synthesizer if needed."""
        prompt = build_script_prompt(
            fact_table=fact_table,
            format_type=format_type,
            target_duration_sec=target_duration_sec,
        )

        for provider_key in self.config.default_chain:
            provider_info = self.config.providers.get(provider_key)
            if not provider_info:
                continue

            api_key = os.getenv(provider_info.env_key)
            if not api_key:
                logger.info(
                    "Skipping provider '%s': %s not found in environment.",
                    provider_key,
                    provider_info.env_key,
                )
                continue

            try:
                logger.info(
                    "Attempting script generation with provider '%s' (%s)",
                    provider_key,
                    provider_info.model,
                )
                raw_response = self._call_provider(provider_key, provider_info, prompt)
                parsed = self._parse_json_response(raw_response)
                script = GeneratedScript.model_validate(parsed)
                return script
            except Exception as e:
                logger.warning(
                    "Provider '%s' failed: %s. Falling back to next in chain.",
                    provider_key,
                    str(e),
                )
                continue

        logger.info(
            "All external providers exhausted or unconfigured. Using deterministic synthesizer."
        )
        return self.synthesize_script(
            fact_table=fact_table,
            format_type=format_type,
            target_duration_sec=target_duration_sec,
            template_type=template_type,
        )

    def _call_provider(self, key: str, info: Any, prompt: str) -> str:
        """Call external LLM API via httpx."""
        api_key = os.environ[info.env_key]

        if key == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{info.model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\n" + prompt}]}],
                "generationConfig": {
                    "temperature": info.temperature,
                    "maxOutputTokens": info.max_tokens,
                },
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

        elif key == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": info.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": info.temperature,
                "max_tokens": info.max_tokens,
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]

        raise ValueError(f"Unknown provider: {key}")

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Strip markdown fences if present and parse json."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

    def synthesize_script(
        self,
        fact_table: FactTable,
        format_type: str = "landscape",
        target_duration_sec: int = 150,
        template_type: str = "stat_race",
    ) -> GeneratedScript:
        """Deterministic, 100% fact-compliant script generator for dry-runs and offline CI runs."""
        scenes: list[ScriptScene] = []
        is_short = format_type == "portrait" or target_duration_sec <= 60
        top_records = fact_table.records[:5] if is_short else fact_table.records[:10]

        hook = f"Who leads the all-time record for {fact_table.title}?"

        for idx, rec in enumerate(top_records, start=1):
            rank_label = f"Rank {rec.rank or idx}"
            unit_str = f" {rec.unit}" if rec.unit else ""
            line = f"At {rank_label} is {rec.entity} with {rec.value}{unit_str}."
            scenes.append(
                ScriptScene(
                    scene_index=idx,
                    scene_type="data",
                    text=line,
                    target_duration_sec=round(target_duration_sec / max(len(top_records), 1), 1),
                    bound_entities=[rec.entity],
                    bound_numbers=[rec.value],
                )
            )

        leader = top_records[0]
        runner_up = top_records[1] if len(top_records) > 1 else None

        if (
            runner_up
            and isinstance(leader.value, (int, float))
            and isinstance(runner_up.value, (int, float))
        ):
            diff = leader.value - runner_up.value
            insight = (
                f"{leader.entity} leads at {leader.value}, maintaining a lead over {runner_up.entity}."
                if diff > 0
                else f"{leader.entity} and {runner_up.entity} remain closely tied at the summit."
            )
        else:
            insight = f"{leader.entity} stands clear at the top of {fact_table.title}."

        source_name = fact_table.sources[0].name.title() if fact_table.sources else "Official Data"
        outro_text = (
            f"Verified open data from {source_name}. Subscribe to GoldReel for daily data insights."
        )

        return GeneratedScript(
            topic_id=fact_table.topic_id,
            title=fact_table.title,
            lane=fact_table.lane,
            format_type="landscape" if format_type == "landscape" else "portrait",
            template_type=template_type,
            hook=hook,
            scenes=scenes,
            insight=insight,
            outro_text=outro_text,
            estimated_duration_sec=float(target_duration_sec),
        )
