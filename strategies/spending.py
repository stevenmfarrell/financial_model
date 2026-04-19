from dataclasses import replace

from models import (
    LifestyleSpendingStrategy,
    SimulationContext,
    YearlyDecisionsPlan,
)


class InflationAdjustedSpending(LifestyleSpendingStrategy):
    """
    Calculates desired lifestyle spending by adjusting a base 'Year 0'
    amount for the cumulative effects of inflation.
    """

    def __init__(self, base_spending_today_dollars: float):
        """
        base_spending_today_dollars: The amount you want to spend in Year 0 purchasing power.
        """
        self.base_spending = base_spending_today_dollars

    def __call__(
        self,
        context: SimulationContext,
        existing_plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        nominal_spending = self.base_spending * context.world.cumulative_inflation_index
        return replace(existing_plan, to_lifestyle_spending=nominal_spending)
