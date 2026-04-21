import pandas as pd
from typing import Any, List
from models import FinancialState, PersonalState, WorldState, YearlyDecisionsPlan
from dataclasses import fields

from simulation_runner import SimulationOutputRecord


def create_history_dataframe(
    history: List[SimulationOutputRecord],
) -> pd.DataFrame:
    """
    Converts a simulation history into a pandas DataFrame for analysis.
    Captures all dataclass fields and @property methods with specific prefixes.
    """
    rows = []

    for world, personal, market, financial, decisions in history:
        row = {}

        # Helper to extract both fields and @property values
        def extract_data(obj: Any, prefix: str):
            # 1. Get standard dataclass fields
            data = {
                f"{prefix}{field.name}": getattr(obj, field.name)
                for field in fields(obj)
            }

            # 2. Get @property methods (like taxable_wages, net_salary_cash_flow)
            cls = type(obj)
            props = [
                name
                for name, value in cls.__dict__.items()
                if isinstance(value, property)
            ]
            for prop in props:
                data[f"{prefix}{prop}"] = getattr(obj, prop)

            return data

        # Combine all snapshots into one flat row
        row.update(extract_data(world, ""))
        row.update(extract_data(personal, ""))
        row.update(extract_data(market, "mkt_"))
        row.update(extract_data(financial, "state_"))
        row.update(extract_data(decisions, "decisions_"))

        rows.append(row)

    return pd.DataFrame(rows)
