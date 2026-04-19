from dataclasses import replace
from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    MortgageStrategy,
)


class FixedMortgage(MortgageStrategy):
    """
    Models a fixed-rate mortgage payment.
    """

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:

        financial = context.financial
        total_owed = financial.mortgage_principal * (
            1 + financial.mortgage_interest_rate
        )
        payment = min(total_owed, financial.mortgage_annual_payment)
        return replace(plan, to_mortgage=max(0, payment))
