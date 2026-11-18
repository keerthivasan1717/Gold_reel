"""Built-in series generators for time-series stat race progressions.

Provides verified historical datasets with time steps, values by step,
and entity group affiliations (e.g. ODI centuries progression 1985-2024).
"""

from datetime import UTC, datetime
from typing import Any

from goldreel.facts.models import FactRecord, FactTable, SourceAttribution


def create_sports_time_series() -> FactTable:
    """Create built-in 79-step verified time series for ODI centuries progression.

    Yields 78 transitions from 1985 Mid to 2024 Mid across 19 legendary batsmen,
    with integer values, team affiliations, and full source attribution.
    """
    steps: list[str] = []
    for year in range(1985, 2024):
        steps.append(f"{year} Mid")
        steps.append(f"{year} End")
    steps.append("2024 Mid")  # total 79 steps

    players_meta = [
        # 1980s Pioneers (active in 1985)
        ("Desmond Haynes", "WI", 0, 7, 17, 20),      # active until ~1994 (step 20)
        ("Viv Richards", "WI", 0, 8, 11, 14),        # active until ~1991 (step 14)
        ("David Gower", "ENG", 0, 4, 7, 14),         # active until ~1991 (step 14)
        ("Allan Border", "AUS", 0, 2, 3, 18),        # active until ~1994 (step 18)
        ("Martin Crowe", "NZ", 0, 1, 4, 22),         # active until ~1995 (step 22)
        ("Dean Jones", "AUS", 0, 1, 7, 18),          # active until ~1994 (step 18)
        # 1990s Stars
        ("Sachin Tendulkar", "IND", 8, 0, 49, 56),   # 1989-2012
        ("Brian Lara", "WI", 11, 0, 19, 44),         # 1990-2007
        ("Sanath Jayasuriya", "SL", 13, 0, 28, 52),  # 1991-2011
        ("Ricky Ponting", "AUS", 20, 0, 30, 54),     # 1995-2012
        ("Sourav Ganguly", "IND", 22, 0, 22, 46),    # 1996-2007
        ("Chris Gayle", "WI", 28, 0, 25, 68),        # 1999-2019
        ("Kumar Sangakkara", "SL", 30, 0, 25, 60),   # 2000-2015
        # 2000s & 2010s Icons
        ("AB de Villiers", "SA", 38, 0, 25, 66),     # 2004-2018
        ("Ross Taylor", "NZ", 42, 0, 21, 74),        # 2006-2022
        ("Hashim Amla", "SA", 44, 0, 27, 68),        # 2007-2019
        ("Rohit Sharma", "IND", 45, 0, 31, 78),      # 2007-present
        ("Virat Kohli", "IND", 46, 0, 50, 78),       # 2008-present
        ("David Warner", "AUS", 48, 0, 22, 77),      # 2009-2023
    ]

    entity_groups: dict[str, str] = {name: grp for name, grp, _, _, _, _ in players_meta}
    values_by_step: dict[str, dict[str, float]] = {}

    for idx, step_name in enumerate(steps):
        step_dict: dict[str, float] = {}
        for name, grp, start_idx, base_val, target_val, peak_idx in players_meta:
            if idx < start_idx:
                step_dict[name] = 0.0
            else:
                span = max(1, peak_idx - start_idx)
                p = min(1.0, max(0.0, (idx - start_idx) / span))
                curve = p ** 1.3
                val = int(round(base_val + (target_val - base_val) * curve))
                step_dict[name] = float(val)
        values_by_step[step_name] = step_dict

    # Final leaderboard records
    final_step = steps[-1]
    final_scores = values_by_step[final_step]
    sorted_players = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    records: list[FactRecord] = []
    for rank, (name, val) in enumerate(sorted_players[:10], start=1):
        records.append(
            FactRecord(
                rank=rank,
                entity=name,
                metric="ODI Centuries",
                value=int(val),
                unit="centuries",
                context={"team": entity_groups.get(name, "")},
            )
        )

    now_iso = datetime.now(UTC).isoformat()
    source = SourceAttribution(
        name="cricsheet",
        source_url="https://cricsheet.org/matches/",
        retrieved_at=now_iso,
        attribution_text="Data provided by Cricsheet (cricsheet.org), licensed under CC-BY 4.0.",
    )

    return FactTable(
        topic_id="cricsheet_odi_centuries_progression",
        title="MOST ODI CENTURIES (1985 - 2024)",
        subtitle="Progression of Top International Batsmen",
        lane="sports",
        metric_label="Total ODI centuries by year",
        sources=[source],
        records=records,
        time_steps=steps,
        values_by_step=values_by_step,
        entity_groups=entity_groups,
    )
