import numpy as np
import pandas as pd
from collections.abc import Callable
from typing import List


from decisions_config import YearlyDecisionsConfiguration

from models import (
    FinancialState,
    MarketConditionsProvider,
    PersonalState,
    RegulationsFactory,
    WorldState,
)
from simulation_runner import SimulationResults, run_simulation

type YearlyDecisionsConfigFactory = Callable[[], YearlyDecisionsConfiguration]


class MonteCarloRunner:
    def __init__(self, trials: int = 100):
        self.trials = trials

    def run(
        self,
        years: int,
        initial_world: WorldState,
        initial_financial: FinancialState,
        initial_personal: PersonalState,
        market_provider: MarketConditionsProvider,
        regulations_factory: RegulationsFactory,
        decisions_strategy_factory: YearlyDecisionsConfigFactory,
    ):

        results: list[SimulationResults] = []

        for i in range(self.trials):
            # reinstantiate the decisions strategies fresh for each simulation run
            decisions_strategy = decisions_strategy_factory()
            result = run_simulation(
                years=years,
                initial_world=initial_world,
                initial_financial=initial_financial,
                initial_personal=initial_personal,
                market_conditions_provider=market_provider,
                regulations_factory=regulations_factory,
                config=decisions_strategy,
                random_seed=i,
            )
            results.append(result)

        return results


def compute_median_balances_by_age(
    results: List[SimulationResults],
) -> pd.DataFrame:
    """
    Computes median net worth, median liquid assets, and percentiles (P10, P90)
    at each age across all Monte Carlo trials. Failed trials count as 0.0
    for ages after failure.
    """
    if not results:
        return pd.DataFrame()

    # Find the set of all ages across all trial histories
    all_ages = sorted(
        list(
            {
                record[1].age
                for r in results
                for record in r.history
            }
        )
    )

    rows = []
    for age in all_ages:
        net_worths = []
        liquid_assets_list = []
        for r in results:
            matching_records = [rec for rec in r.history if rec[1].age == age]
            if matching_records:
                financial = matching_records[0][3]
                net_worths.append(financial.net_worth)
                liquid_assets_list.append(financial.liquid_assets)
            else:
                # Trial failed before reaching this age
                net_worths.append(0.0)
                liquid_assets_list.append(0.0)

        nw_arr = np.array(net_worths)
        liq_arr = np.array(liquid_assets_list)

        rows.append(
            {
                "age": age,
                "median_net_worth": float(np.median(nw_arr)),
                "p10_net_worth": float(np.percentile(nw_arr, 10)),
                "p90_net_worth": float(np.percentile(nw_arr, 90)),
                "median_liquid_assets": float(np.median(liq_arr)),
                "p10_liquid_assets": float(np.percentile(liq_arr, 10)),
                "p90_liquid_assets": float(np.percentile(liq_arr, 90)),
            }
        )

    return pd.DataFrame(rows)

