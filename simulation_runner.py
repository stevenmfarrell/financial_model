# financial_model/runner.py

from typing import List
from dataclasses import replace
from decisions_config import YearlyDecisionsConfiguration
from inflation import to_real_dollars
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
from simulate_year import BankruptcyError, simulate_year

SimulationOutputRecord = tuple[
    WorldState,
    PersonalState,
    MarketConditions,
    FinancialState,
    YearlyMetrics,
    YearlyDecisionsPlan,
]


def nominal_history_to_real_history(
    nominal_history: List[SimulationOutputRecord],
) -> List[SimulationOutputRecord]:
    """Deflate a list of SimulationOutputRecords into real dollars"""
    real_history = []
    for world, personal, market, financial, metrics, decisions in nominal_history:
        inf_index = world.cumulative_inflation_index

        real_history.append(
            (
                world,
                personal,
                market,
                to_real_dollars(financial, inf_index),
                to_real_dollars(metrics, inf_index),
                to_real_dollars(decisions, inf_index),
            )
        )
    return real_history


def run_simulation(
    years: int,
    initial_world: WorldState,
    initial_financial: FinancialState,
    initial_personal: PersonalState,
    market_conditions_provider: MarketConditionsProvider,
    regulations_factory: RegulationsFactory,
    config: YearlyDecisionsConfiguration,
    random_seed: int | None = None,
    return_real_dollars: bool = True,
) -> List[SimulationOutputRecord]:
    """
    Runs the simulation for X years and returns a history of the states, in real dollars by default
    """
    history: List[SimulationOutputRecord] = []
    year_start_financial = initial_financial
    year_start_personal = initial_personal
    year_start_world = initial_world

    market_conditions_list = market_conditions_provider(years, random_seed)

    for i in range(years):
        market = market_conditions_list[i]
        try:
            # 1. Simulate the year
            (
                year_end_world,
                year_end_financial,
                year_end_personal,
                metrics,
                decisions,
            ) = simulate_year(
                world=year_start_world,
                financial=year_start_financial,
                personal=year_start_personal,
                market=market,
                regulations_factory=regulations_factory,
                config=config,
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
        except BankruptcyError as e:
            print(f"Simulation failed at age {year_start_personal.age}: {e}")
            break

        # Move to start of next year
        year_start_world = replace(year_end_world, year=year_end_world.year + 1)
        year_start_personal = year_end_personal
        year_start_financial = year_end_financial

    if return_real_dollars:
        real_history = nominal_history_to_real_history(history)
        return real_history
    else:
        return history
