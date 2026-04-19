from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    RegulatoryCalculator,
)
from regulatory_kernel.tax import (
    calculate_capital_gains_tax_kernel,
    calculate_early_withdrawal_penalty_kernel,
    calculate_federal_tax_2026_kernel,
    calculate_flat_tax_kernel,
    calculate_taxable_income_2026_kernel,
)


class USFederalIncomeTax2026(RegulatoryCalculator):
    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        world, personal = context.world, context.personal
        inf = world.cumulative_inflation_index
        is_married = personal.marital_status == "married"

        std_deduction = 32200 if is_married else 16100
        raw_brackets = (
            [
                (24800, 0.10),
                (100800, 0.12),
                (211400, 0.22),
                (403550, 0.24),
                (512450, 0.32),
                (768700, 0.35),
                (float("inf"), 0.37),
            ]
            if is_married
            else [
                (12400, 0.10),
                (50400, 0.12),
                (105700, 0.22),
                (201775, 0.24),
                (256225, 0.32),
                (640600, 0.35),
                (float("inf"), 0.37),
            ]
        )

        adj_brackets = [
            (limit * inf if limit != float("inf") else limit, rate)
            for limit, rate in raw_brackets
        ]

        return calculate_federal_tax_2026_kernel(
            taxable_income=context.regulations.get_taxable_income(context, plan),
            wages=plan.gross_earned_income,
            adj_standard_deduction=std_deduction * inf,
            adj_brackets=adj_brackets,
            adj_ss_wage_base=184500 * inf,
            adj_addl_med_threshold=(250000 if is_married else 200000) * inf,
            fica_rates=(0.062, 0.0145, 0.009),
        )


class BrokerageCapitalGainsTax(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the capital gains logic kernel.
    Calculates tax on the 'Gain' portion of brokerage liquidations.
    """

    def __init__(self, long_term_rate: float = 0.15):
        self.rate = long_term_rate

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        growth_liquidated = plan.from_taxable_brokerage_growth

        return calculate_capital_gains_tax_kernel(
            growth_amount=growth_liquidated, rate=self.rate
        )


class FlatStateIncomeTaxStrategy(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the flat tax logic kernel.
    Useful for modeling state taxes (e.g., Utah's 4.65% rate).
    """

    def __init__(self, rate: float, label: str = "State Tax"):
        self.rate = rate
        self.label = label

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        ordinary_income = context.regulations.get_taxable_income(context, plan)
        growth_income = plan.from_taxable_brokerage_growth

        return calculate_flat_tax_kernel(
            taxable_base_ordinary=ordinary_income,
            brokerage_growth=growth_income,
            rate=self.rate,
        )


class CombinedTaxCalculator(RegulatoryCalculator):
    """Aggregates multiple tax components (Fed, State, Gains)."""

    def __init__(self, *strategies: RegulatoryCalculator):
        self.strategies = strategies

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        taxes = 0.0

        for strat in self.strategies:
            taxes += strat(context, plan)

        return taxes


class TaxableIncomeCalculator2026(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the taxable income logic kernel.
    """

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index

        # For MFJ 2026 estimates:
        BASE_THRESHOLD = 32000.0 * inf
        UPPER_THRESHOLD = 44000.0 * inf
        # 50% of the range between 32k and 44k is 6k
        MIDDLE_TIER_CAP = 6000.0 * inf

        # Delegate extraction to the kernel
        return calculate_taxable_income_2026_kernel(
            taxable_wages=plan.taxable_wages,
            traditional_withdrawals=plan.from_traditional_retirement,
            ss_received=plan.social_security_recieved,
            ss_base_threshold=BASE_THRESHOLD,
            ss_upper_threshold=UPPER_THRESHOLD,
            ss_middle_tier_cap=MIDDLE_TIER_CAP,
        )


class EarlyWithdrawalPenaltyCalculator(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the penalty logic kernel.
    """

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        return calculate_early_withdrawal_penalty_kernel(
            traditional_withdrawals=plan.from_traditional_retirement,
            hsa_withdrawals=plan.from_hsa,
            age=context.personal.age,
        )
