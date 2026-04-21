# financial_model/runner.py

from typing import List
from dataclasses import replace
from decisions_config import YearlyDecisionsConfiguration
from models import (
    FinancialState,
    MarketConditions,
    MarketConditionsProvider,
    PersonalState,
    RegulationsFactory,
    WorldState,
    YearlyDecisionsPlan,
    YearlyMetrics,
)
from simulate_year import simulate_year

SimulationOutputRecord = tuple[
    WorldState,
    PersonalState,
    MarketConditions,
    FinancialState,
    YearlyMetrics,
    YearlyDecisionsPlan,
]


def run_simulation(
    years: int,
    initial_world: WorldState,
    initial_financial: FinancialState,
    initial_personal: PersonalState,
    market_conditions_provider: MarketConditionsProvider,
    regulations_factory: RegulationsFactory,
    config: YearlyDecisionsConfiguration,
    random_seed: int | None = None,
) -> List[SimulationOutputRecord]:
    """
    Runs the simulation for X years and returns a history of the states.
    """
    history: List[SimulationOutputRecord] = []
    year_start_financial = initial_financial
    year_start_personal = initial_personal
    year_start_world = initial_world

    market_conditions_list = market_conditions_provider(years, random_seed)

    for i in range(years):
        market = market_conditions_list[i]

        # 1. Simulate the year
        year_end_world, year_end_financial, year_end_personal, metrics, decisions = (
            simulate_year(
                world=year_start_world,
                financial=year_start_financial,
                personal=year_start_personal,
                market=market,
                regulations_factory=regulations_factory,
                config=config,
            )
        )

        # 2. Record the end-of-year state
        history.append(
            (
                year_end_world,
                year_end_personal,
                market,
                year_end_financial,
                metrics,
                decisions,
            )
        )
        # Move to start of next year
        year_start_world = replace(year_end_world, year=year_end_world.year + 1)
        year_start_personal = year_end_personal
        year_start_financial = year_end_financial

    return history
