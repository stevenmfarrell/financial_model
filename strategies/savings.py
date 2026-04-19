from dataclasses import replace
from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    SavingsStrategy,
)


class WaterfallSavings(SavingsStrategy):
    """
    Allocates post-tax surplus cash to discretionary savings.
    Priority: Cash Reserve (Emergency Fund) -> Roth IRA -> Brokerage.
    """

    def __init__(self, target_cash_reserve: float):
        """
        target_cash_reserve: The total balance you want to maintain in liquid cash.
        roth_ira_limit: The maximum annual contribution for a Roth IRA.
        """
        self.target_cash_reserve = target_cash_reserve

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # 1. Determine if we have a surplus (negative shortfall = extra cash)
        surplus = max(0.0, -plan.current_cash_shortfall)

        if surplus <= 0:
            return plan

        # 2. Priority 1: Cash Reserve (Fill the gap to the target)
        # We look at the 'state' to see what we already have in the bank.
        cash_gap = max(0.0, self.target_cash_reserve - context.financial.cash_balance)
        to_cash = min(surplus, cash_gap)
        surplus -= to_cash

        # 3. Priority 2: Roth IRA
        to_roth_ira = min(surplus, context.regulations.annual_ira_limit)
        surplus -= to_roth_ira

        # 4. Priority 3: Taxable Brokerage (The "Overflow" bucket)
        to_brokerage = surplus

        # 5. Update the Plan
        return replace(
            plan,
            to_cash_reserve=to_cash,
            to_roth_ira=to_roth_ira,
            to_brokerage=to_brokerage,
        )
