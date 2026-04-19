from dataclasses import replace
from model import (
    FinancialState,
    PersonalState,
    YearlyDecisionsPlan,
    MortgageStrategy,
)


class FixedMortgage(MortgageStrategy):
    """
    Models a fixed-rate mortgage payment.
    """

    def __call__(
        self,
        financial: FinancialState,
        personal: PersonalState,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:

        total_owed = financial.mortgage_principal * (
            1 + financial.mortgage_interest_rate
        )
        payment = min(total_owed, financial.mortgage_annual_payment)
        return replace(plan, to_mortgage=max(0, payment))
