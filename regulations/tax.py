from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    RegulatoryCalculator,
)
from regulatory_kernel.tax import (
    calculate_capital_gains_tax_kernel,
    calculate_early_withdrawal_penalty_kernel,
    calculate_federal_tax_kernel,
    calculate_flat_tax_kernel,
    calculate_taxable_income_kernel,
)


class InflationTrackingFederalTaxCalculator(RegulatoryCalculator):
    """
    Generic Federal Income Tax calculator that scales thresholds
    and deductions by inflation.
    """

    def __init__(
        self,
        std_deduction_married: float,
        std_deduction_single: float,
        brackets_married: list[tuple[float, float]],
        brackets_single: list[tuple[float, float]],
        ss_wage_base: float,
        med_threshold_married: float,
        med_threshold_single: float,
        fica_rates: tuple[float, float, float],
    ):
        self.std_deduction_married = std_deduction_married
        self.std_deduction_single = std_deduction_single
        self.brackets_married = brackets_married
        self.brackets_single = brackets_single
        self.ss_wage_base = ss_wage_base
        self.med_threshold_married = med_threshold_married
        self.med_threshold_single = med_threshold_single
        self.fica_rates = fica_rates

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index
        is_married = context.personal.marital_status == "married"

        # 1. Scale Standard Deduction
        std_deduction = (
            self.std_deduction_married if is_married else self.std_deduction_single
        ) * inf

        # 2. Scale Tax Brackets
        raw_brackets = self.brackets_married if is_married else self.brackets_single
        adj_brackets = [
            (limit * inf if limit != float("inf") else limit, rate)
            for limit, rate in raw_brackets
        ]

        # 3. Scale FICA and Medicare Thresholds
        adj_ss_wage_base = self.ss_wage_base * inf
        adj_med_threshold = (
            self.med_threshold_married if is_married else self.med_threshold_single
        ) * inf

        return calculate_federal_tax_kernel(
            taxable_income=context.regulations.get_taxable_income(context, plan),
            wages=plan.gross_earned_income,
            adj_standard_deduction=std_deduction,
            adj_brackets=adj_brackets,
            adj_ss_wage_base=adj_ss_wage_base,
            adj_addl_med_threshold=adj_med_threshold,
            fica_rates=self.fica_rates,
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


class InflationTrackingTaxableIncomeCalculator(RegulatoryCalculator):
    """
    Generic taxable income calculator that scales Social Security
    taxability thresholds by inflation.
    """

    def __init__(
        self,
        ss_base_threshold: float,
        ss_upper_threshold: float,
        ss_middle_tier_cap: float,
    ):
        self.ss_base_threshold = ss_base_threshold
        self.ss_upper_threshold = ss_upper_threshold
        self.ss_middle_tier_cap = ss_middle_tier_cap

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        inf = context.world.cumulative_inflation_index

        return calculate_taxable_income_kernel(
            taxable_wages=plan.taxable_wages,
            traditional_withdrawals=plan.from_traditional_retirement,
            roth_earnings_withdrawals=plan.from_roth_retirement_earnings,
            hsa_non_medical_withdrawals=plan.from_hsa_nonmedical,
            trad_to_roth_conversion=plan.trad_to_roth_conversion,
            age=context.personal.age,
            ss_received=plan.social_security_recieved,
            ss_base_threshold=self.ss_base_threshold * inf,
            ss_upper_threshold=self.ss_upper_threshold * inf,
            ss_middle_tier_cap=self.ss_middle_tier_cap * inf,
        )


class EarlyWithdrawalPenaltyCalculator(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the penalty logic kernel.
    """

    def __call__(self, context: SimulationContext, plan: YearlyDecisionsPlan) -> float:
        return calculate_early_withdrawal_penalty_kernel(
            traditional_withdrawals=plan.from_traditional_retirement,
            hsa_non_medical_withdrawals=plan.from_hsa_nonmedical,
            roth_earnings_withdrawals=plan.from_roth_retirement_earnings,
            age=context.personal.age,
        )
