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

        results: List[SimulationResults] = []

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
