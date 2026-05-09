from typing import Callable

import numpy as np
from typing import List
from models import (
    FinancialState,
    WorldState,
    PersonalState,
    MarketConditionsProvider,
    RegulationsFactory,
)
from decisions_config import YearlyDecisionsConfiguration
from simulation_runner import run_simulation

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
        final_net_worths = []
        failure_ages = []

        for i in range(self.trials):
            # reinstantiate the decisions strategies fresh for each simulation run
            decisions_strategy = decisions_strategy_factory()
            history = run_simulation(
                years=years,
                initial_world=initial_world,
                initial_financial=initial_financial,
                initial_personal=initial_personal,
                market_conditions_provider=market_provider,
                regulations_factory=regulations_factory,
                config=decisions_strategy,
                random_seed=i,
            )

            # Check for failure (if history is shorter than the requested years)
            if len(history) < years:
                last_record = history[-1]
                failure_ages.append(
                    last_record[1].age
                )  # PersonalState.age is at index 1
                final_net_worths.append(0.0)
            else:
                last_financial = history[-1][3]  # FinancialState is at index 3
                # Calculate simple net worth (assets - mortgage)
                net_worth = (
                    last_financial.taxable_brokerage_balance
                    + last_financial.cash_balance
                    + last_financial.traditional_retirement_balance
                    + last_financial.roth_retirement_balance
                    + last_financial.hsa_balance
                    + last_financial.primary_residence_value
                    - last_financial.mortgage_principal
                )
                final_net_worths.append(net_worth)

        return {
            "success_rate": len([nw for nw in final_net_worths if nw > 0])
            / self.trials,
            "median_net_worth": np.median(final_net_worths),
            "failure_ages": failure_ages,
        }
