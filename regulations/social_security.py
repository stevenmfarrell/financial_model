from models import (
    RegulatoryCalculator,
    SimulationContext,
    YearlyDecisionsPlan,
)
from regulatory_kernel.social_security import calculate_social_security_payout


class InflationTrackingSocialSecurityPayout(RegulatoryCalculator):
    """
    Generic Social Security benefit calculator that scales bend points by inflation.
    """

    def __init__(self, b1: float, b2: float, fra: int = 67):
        self.b1 = b1
        self.b2 = b2
        self.fra = fra

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> float:
        inf = context.world.cumulative_inflation_index
        # Earnings history is stored in real dollars; inflate to nominal for the kernel
        indexed_history = tuple(e * inf for e in context.personal.real_earnings_history)

        return calculate_social_security_payout(
            indexed_earnings_history=indexed_history,
            current_age=context.personal.age,
            claiming_age=context.personal.social_security_claiming_age,
            b1=self.b1 * inf,
            b2=self.b2 * inf,
            fra=self.fra,
        )
