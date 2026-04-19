# financial_model/runner.py

from typing import List, Union
from dataclasses import replace
from decisions_config import YearlyDecisionsConfiguration
from models import (
    FinancialState,
    PersonalState,
    MarketConditions,
    RegulationsFactory,
    WorldState,
    YearlyDecisionsPlan,
)
from simulate_year import simulate_financial_year


def run_simulation(
    years: int,
    initial_world: WorldState,
    initial_financial: FinancialState,
    initial_personal: PersonalState,
    market_input: Union[MarketConditions, List[MarketConditions]],
    regulations_factory: RegulationsFactory,
    config: YearlyDecisionsConfiguration,
) -> List[tuple[WorldState, PersonalState, FinancialState, YearlyDecisionsPlan]]:
    """
    Runs the simulation for X years and returns a history of the states.
    """
    history = []
    year_start_financial = initial_financial
    year_start_personal = initial_personal
    year_start_world = initial_world

    for i in range(years):
        # Determine market conditions for this specific year
        if isinstance(market_input, list):
            # Ensure we don't run out of market data
            market = market_input[i % len(market_input)]
        else:
            market = market_input

        # 1. Simulate the year
        year_end_world, year_end_financial, decisions = simulate_financial_year(
            world=year_start_world,
            financial=year_start_financial,
            personal=year_start_personal,
            market=market,
            regulations_factory=regulations_factory,
            config=config,
        )

        year_end_personal = replace(
            year_start_personal, age=year_start_personal.age + 1
        )

        # 2. Record the end-of-year state
        history.append(
            (year_end_world, year_end_personal, year_end_financial, decisions)
        )

        # Move to start of next year
        year_start_world = replace(year_end_world, year=year_end_world.year + 1)
        year_start_personal = year_end_personal

    return history
