"""Prompts and prompt builder for fact-bound script narration."""

import json

from goldreel.facts.models import FactTable

SYSTEM_PROMPT = """You are GoldReel AI, an automated voiceover scriptwriter for faceless YouTube data videos.
You write punchy, engaging narration that will be read aloud by a text-to-speech engine.

CRITICAL NON-NEGOTIABLE RULES:
1. TRUTH & FACTS ONLY: Every single number, ranking, date, year, and name you output MUST come directly from the provided Fact Table.
2. ZERO HALLUCINATION: Never add outside stats, unverified estimates, or invented trivia. If an AI writes a number not in the fact table, the automated Fact Gate rejects and discards the entire video.
3. ORIGINAL INSIGHT: Provide an analytical observation (e.g. noticing the gap between #1 and #2, or a timeline cluster) using only the verified facts.
4. TONE: Confident, fast-paced, high contrast. No fluff or corporate filler.
5. FORMAT: Return strictly valid JSON matching the requested schema.
"""


def build_script_prompt(
    fact_table: FactTable,
    format_type: str = "landscape",
    target_duration_sec: int = 150,
) -> str:
    """Construct user prompt binding the script directly to the verified fact table."""
    # Target word counts (assuming Piper TTS ~140 words/min)
    words_per_sec = 2.3
    target_words = int(target_duration_sec * words_per_sec)
    max_words = int(target_words * 1.15)
    min_words = int(target_words * 0.75)

    facts_payload = {
        "topic_id": fact_table.topic_id,
        "title": fact_table.title,
        "lane": fact_table.lane,
        "metric_rule": fact_table.metric_label,
        "sources": [s.model_dump() for s in fact_table.sources],
        "records": [r.model_dump() for r in fact_table.records],
    }

    prompt = f"""Generate a YouTube narration script for the following verified dataset:

FACT TABLE (Ground Truth):
{json.dumps(facts_payload, indent=2)}

FORMAT & DURATION CONSTRAINTS:
- Video Format: {format_type} ({"16:9 Landscape" if format_type == "landscape" else "9:16 Vertical Short"})
- Target Duration: ~{target_duration_sec} seconds
- Target Word Count: between {min_words} and {max_words} words

REQUIRED JSON SCHEMA:
{{
  "topic_id": "{fact_table.topic_id}",
  "title": "{fact_table.title}",
  "lane": "{fact_table.lane}",
  "format_type": "{format_type}",
  "template_type": "stat_race",
  "hook": "Opening sentence that poses the core question or tension",
  "scenes": [
    {{
      "scene_index": 1,
      "scene_type": "data",
      "text": "Narration text for this scene using ONLY numbers and names from the fact table",
      "target_duration_sec": 5.0,
      "bound_entities": ["Entity Name"],
      "bound_numbers": ["Verified Number"]
    }}
  ],
  "insight": "One or two sentences analyzing the pattern or record strictly from the numbers above",
  "outro_text": "Source: {fact_table.sources[0].name}. Subscribe for daily data stories."
}}

Output ONLY the JSON object. Do not include markdown code fences or conversational text.
"""
    return prompt
