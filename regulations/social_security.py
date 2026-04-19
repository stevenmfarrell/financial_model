from models import (
    RegulatoryCalculator,
    SimulationContext,
    YearlyDecisionsPlan,
)
from regulatory_kernel.social_security import calculate_social_security_payout_kernel


class SocialSecurityPayout2026(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the Social Security logic kernel.
    """

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> float:
        inf = context.world.cumulative_inflation_index
        indexed_history = tuple(e * inf for e in context.personal.real_earnings_history)
        return calculate_social_security_payout_kernel(
            indexed_earnings_history=indexed_history,
            current_age=context.personal.age,
            claiming_age=context.personal.social_security_claiming_age,
            b1=1200.0 * inf,
            b2=7200.0 * inf,
        )
