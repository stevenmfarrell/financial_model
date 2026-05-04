import pandas as pd
from typing import (
    Annotated,
    Any,
    List,
    TypeAliasType,
    get_args,
    get_origin,
    get_type_hints,
)
from dataclasses import fields

from simulation_runner import SimulationOutputRecord


def is_nominal_currency_type(annotation: Any) -> bool:
    """Helper to check if a type hint is Annotated with 'is_nominal_currency'."""

    # 1. Unwrap the 3.12 Type Alias if present
    if isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__

    # 2. Proceed with standard Annotated check
    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        return "is_nominal_currency" in args

    return False


def create_history_dataframe(
    history: List[SimulationOutputRecord], to_real_dollars: bool = True
) -> pd.DataFrame:
    """
    Converts a simulation history into a pandas DataFrame for analysis.
    Captures all dataclass fields and @property methods with specific prefixes.
    """
    rows = []
    class_currency_maps = {}
    currency_columns = set()
    for world, personal, market, financial, metrics, decisions in history:
        row = {}

        def extract_data(obj: Any, prefix: str):
            cls = type(obj)
            if cls not in class_currency_maps:
                # Identify currency fields/properties once per class
                currency_names = []

                # 1. Check Fields
                hints = get_type_hints(cls, include_extras=True)
                for name, hint in hints.items():
                    if is_nominal_currency_type(hint):
                        currency_names.append(f"{prefix}{name}")

                # 2. Check Properties
                for name in dir(cls):
                    attr = getattr(cls, name)
                    if isinstance(attr, property):
                        # Inspect the return type of the property's getter
                        prop_hints = get_type_hints(attr.fget, include_extras=True)
                        return_hint = prop_hints.get("return")
                        if is_nominal_currency_type(return_hint):
                            currency_names.append(f"{prefix}{name}")

                class_currency_maps[cls] = currency_names

            # Add identified columns to the global set for later adjustment
            currency_columns.update(class_currency_maps[cls])

            # Standard extraction (using existing logic)
            data = {f"{prefix}{f.name}": getattr(obj, f.name) for f in fields(obj)}
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

    df = pd.DataFrame(rows)

    if to_real_dollars:
        for col in currency_columns:
            if col in df.columns:
                df[f"{col}_real"] = df[col] / df["cumulative_inflation_index"]

    return df
