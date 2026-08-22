from dataclasses import fields
from typing import Any

import pandas as pd

from simulation_runner import SimulationOutputRecord


def create_history_dataframe(history: list[SimulationOutputRecord]) -> pd.DataFrame:
    """
    Converts a simulation history into a pandas DataFrame.
    Strictly extracts the exact state of the provided objects.
    """
    rows = []

    # Adjust unpacking here if your history tuple structure changes
    for world, personal, market, financial, metrics, decisions in history:
        row = {}

        def extract_data(obj: Any, prefix: str):
            cls = type(obj)

            # Extract standard dataclass fields
            data = {f"{prefix}{f.name}": getattr(obj, f.name) for f in fields(obj)}

            # Extract dynamically calculated @property getters
            for name in dir(cls):
                if isinstance(getattr(cls, name), property):
                    data[f"{prefix}{name}"] = getattr(obj, name)

            return data

        # Combine all snapshots into one flat row
        row.update(extract_data(world, ""))
        row.update(extract_data(personal, ""))
        row.update(extract_data(market, "mkt_"))
        row.update(extract_data(financial, "state_"))
        row.update(extract_data(decisions, "decisions_"))
        row.update(extract_data(metrics, "metrics_"))

        rows.append(row)

    return pd.DataFrame(rows)
