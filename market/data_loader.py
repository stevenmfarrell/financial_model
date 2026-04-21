import csv
from pathlib import Path
from typing import Dict
from models import MarketConditions


def load_market_conditions_from_csv(
    file_path: str | Path = "historical.csv",
) -> Dict[int, MarketConditions]:
    """
    Reads a CSV of yearly market data and returns a dictionary keyed by year.

    Expected CSV Headers:
    year, annual_inflation_rate, annual_stock_return, annual_bond_return,
    annual_cash_return, annual_home_appreciation_rate
    """
    market_conditions_map: Dict[int, MarketConditions] = {}

    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            # Parse the year to use as the dictionary key
            year = int(row["year"])

            # Instantiate the MarketConditions dataclass for that year
            market_conditions_map[year] = MarketConditions(
                annual_inflation_rate=float(row["annual_inflation_rate"]),
                annual_stock_return=float(row["annual_stock_return"]),
                annual_bond_return=float(row["annual_bond_return"]),
                annual_cash_return=float(row["annual_cash_return"]),
                annual_home_appreciation_rate=float(
                    row["annual_home_appreciation_rate"]
                ),
            )

    return market_conditions_map


def loaded_data_to_list(
    historical_data: Dict[int, MarketConditions],
) -> list[MarketConditions]:
    """
    Sorts the historical market data by year and returns a list of MarketConditions.
    """
    # Sort the dictionary keys (years) to ensure chronological order
    sorted_years = sorted(historical_data.keys())

    # Return the MarketConditions objects in that sorted order
    return [historical_data[year] for year in sorted_years]
