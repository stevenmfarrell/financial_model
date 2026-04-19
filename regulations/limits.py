from models import (
    RegulatoryCalculator,
    SimulationContext,
    YearlyDecisionsPlan,
)
from regulatory_kernel.limits import (
    calculate_401k_limit_kernel,
    calculate_household_roth_ira_limit_kernel,
    calculate_hsa_limit_kernel,
)


class InflationTracking401kLimit(RegulatoryCalculator):
    """
    Generic 401(k) limit calculator that scales baseline values by inflation.
    Baseline values are injected at initialization.
    """

    def __init__(self, base_limit: float, catchup_amt: float):
        self.base_limit = base_limit
        self.catchup_amt = catchup_amt

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        # Scale the baseline values by the simulation's cumulative inflation index
        inf = context.world.cumulative_inflation_index

        return calculate_401k_limit_kernel(
            age=context.personal.age,
            base_limit=self.base_limit * inf,
            catchup_amt=self.catchup_amt * inf,
        )


class InflationTrackingHSALimit(RegulatoryCalculator):
    """
    Generic HSA limit calculator that scales baseline values by inflation.
    Baseline values (single, family, catchup) are injected at initialization.
    """

    def __init__(self, single_limit: float, family_limit: float, catchup_amt: float):
        self.single_limit = single_limit
        self.family_limit = family_limit
        self.catchup_amt = catchup_amt

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index
        personal = context.personal

        return calculate_hsa_limit_kernel(
            age=personal.age,
            is_married=personal.marital_status == "married",
            nominal_single_limit=self.single_limit * inf,
            nominal_family_limit=self.family_limit * inf,
            nominal_catchup_amt=self.catchup_amt * inf,
        )


class InflationTrackingHouseholdRothIRALimit(RegulatoryCalculator):
    """
    Generic Roth IRA limit calculator that scales baseline values by inflation.
    Baseline values (base limit, catchup) are injected at initialization.
    """

    def __init__(self, base_limit: float, catchup_amt: float):
        self.base_limit = base_limit
        self.catchup_amt = catchup_amt

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index
        personal = context.personal

        return calculate_household_roth_ira_limit_kernel(
            age=personal.age,
            is_married=personal.marital_status == "married",
            nominal_base_limit=self.base_limit * inf,
            nominal_catchup_amt=self.catchup_amt * inf,
        )
