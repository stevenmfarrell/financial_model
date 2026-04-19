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


class IRS401kLimit2026(RegulatoryCalculator):
    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index

        return calculate_401k_limit_kernel(
            age=context.personal.age, base_limit=23500.0 * inf, catchup_amt=7500.0 * inf
        )


class IRSHSALimit2026(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the HSA logic kernel.
    Handles inflation scaling and state extraction.
    """

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index
        personal = context.personal

        # The Adapter 'Bakes' the nominal constants for the current year
        return calculate_hsa_limit_kernel(
            age=personal.age,
            is_married=personal.marital_status == "married",
            nominal_single_limit=4150.0 * inf,
            nominal_family_limit=8300.0 * inf,
            nominal_catchup_amt=1000.0 * inf,
        )


class IRSHouseholdRothIRALimit2026(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the Roth IRA logic kernel.
    Bakes nominal constants and extracts marital status.
    """

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index
        personal = context.personal

        return calculate_household_roth_ira_limit_kernel(
            age=personal.age,
            is_married=personal.marital_status == "married",
            nominal_base_limit=7000.0 * inf,
            nominal_catchup_amt=1000.0 * inf,
        )
