import pandas as pd
from typing import Any, List
from model import FinancialState, PersonalState, YearlyDecisionsPlan
from dataclasses import fields


def create_history_dataframe(
    history: List[tuple[PersonalState, FinancialState, YearlyDecisionsPlan]],
) -> pd.DataFrame:
    """
    Converts a simulation history into a pandas DataFrame for analysis.
    Captures all dataclass fields and @property methods with specific prefixes.
    """
    rows = []

    for personal, state, decisions in history:
        row = {}

        # Helper to extract both fields and @property values
        def extract_data(obj: Any, prefix: str):
            # 1. Get standard dataclass fields
            data = {
                f"{prefix}_{field.name}": getattr(obj, field.name)
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
                data[f"{prefix}_{prop}"] = getattr(obj, prop)

            return data

        # Combine all three snapshots into one flat row
        row.update(extract_data(personal, "personal"))
        row.update(extract_data(state, "state"))
        row.update(extract_data(decisions, "decisions"))

        rows.append(row)

    return pd.DataFrame(rows)
