from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    RegulatoryCalculator,
)
from regulatory_kernel.tax import (
    IncomeSources,
    calculate_capital_gains_tax,
    calculate_early_withdrawal_penalty,
    calculate_federal_taxable_wages,
    calculate_fica_tax,
    calculate_fica_taxable_wages,
    calculate_net_investment_income_tax,
    calculate_ordinary_adjusted_gross_income,
    calculate_ordinary_income_tax,
    calculate_state_flat_tax,
    calculate_taxable_segments,
    get_net_investment_income,
    get_tax_bracket_limit,
)


class InflationTrackingFederalTaxCalculator(RegulatoryCalculator):
    """
    Generic Federal Income Tax calculator that scales thresholds
    and deductions by inflation, utilizing sequential tax calculations.
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
        ss_base_threshold_married: float,
        ss_base_threshold_single: float,
        ss_upper_threshold_married: float,
        ss_upper_threshold_single: float,
        ss_middle_tier_cap_married: float,
        ss_middle_tier_cap_single: float,
        # --- New Parameters for LTCG and NIIT ---
        ltcg_brackets_married: list[tuple[float, float]],
        ltcg_brackets_single: list[tuple[float, float]],
        niit_threshold_married: float,
        niit_threshold_single: float,
    ):
        self.std_deduction_married = std_deduction_married
        self.std_deduction_single = std_deduction_single
        self.brackets_married = brackets_married
        self.brackets_single = brackets_single
        self.ss_wage_base = ss_wage_base
        self.med_threshold_married = med_threshold_married
        self.med_threshold_single = med_threshold_single
        self.fica_rates = fica_rates

        self.ss_base_threshold_married = ss_base_threshold_married
        self.ss_base_threshold_single = ss_base_threshold_single
        self.ss_upper_threshold_married = ss_upper_threshold_married
        self.ss_upper_threshold_single = ss_upper_threshold_single
        self.ss_middle_tier_cap_married = ss_middle_tier_cap_married
        self.ss_middle_tier_cap_single = ss_middle_tier_cap_single

        self.ltcg_brackets_married = ltcg_brackets_married
        self.ltcg_brackets_single = ltcg_brackets_single
        self.niit_threshold_married = niit_threshold_married
        self.niit_threshold_single = niit_threshold_single

    def __call__(
        self, context: "SimulationContext", plan: "YearlyDecisionsPlan"
    ) -> float:
        inf = context.world.cumulative_inflation_index
        is_married = context.personal.marital_status == "married"

        # --- 1. Scale All Thresholds and Brackets by Inflation ---
        std_deduction = (
            self.std_deduction_married if is_married else self.std_deduction_single
        ) * inf

        raw_brackets = self.brackets_married if is_married else self.brackets_single
        adj_brackets = [
            (limit * inf if limit != float("inf") else limit, rate)
            for limit, rate in raw_brackets
        ]

        raw_ltcg_brackets = (
            self.ltcg_brackets_married if is_married else self.ltcg_brackets_single
        )
        adj_ltcg_brackets = [
            (limit * inf if limit != float("inf") else limit, rate)
            for limit, rate in raw_ltcg_brackets
        ]

        adj_ss_wage_base = self.ss_wage_base * inf
        adj_med_threshold = (
            self.med_threshold_married if is_married else self.med_threshold_single
        ) * inf
        adj_niit_threshold = (
            self.niit_threshold_married if is_married else self.niit_threshold_single
        ) * inf

        adj_ss_base = (
            self.ss_base_threshold_married
            if is_married
            else self.ss_base_threshold_single
        ) * inf
        adj_ss_upper = (
            self.ss_upper_threshold_married
            if is_married
            else self.ss_upper_threshold_single
        ) * inf
        adj_ss_mid_cap = (
            self.ss_middle_tier_cap_married
            if is_married
            else self.ss_middle_tier_cap_single
        ) * inf

        # --- 2. Build IncomeSources Dataclass ---
        income = IncomeSources(
            wages=plan.gross_earned_income,
            interest_and_dividends=0,  # TODO not modeled
            short_term_gains=0,  # TODO not modeled
            long_term_gains=plan.from_taxable_brokerage_growth,
        )

        # --- 3. Execute Tax Sequence ---

        # A. Calculate FICA
        fica_wages = calculate_fica_taxable_wages(
            income=income,
            health_insurance_premiums=plan.payroll_to_health_premiums,
            payroll_to_hsa=plan.payroll_to_hsa,
        )

        fica_tax = calculate_fica_tax(
            fica_taxable_wages=fica_wages,
            ss_wage_base=adj_ss_wage_base,
            addl_med_threshold=adj_med_threshold,
            fica_rates=self.fica_rates,
        )

        # B. Calculate Federal Taxable Wages
        federal_wages = calculate_federal_taxable_wages(
            fica_taxable_wages=fica_wages,
            payroll_to_trad_401k=getattr(plan, "payroll_to_trad_401k", 0.0),
            match_to_roth_401k=getattr(plan, "match_to_roth_401k", 0.0),
        )

        # C. Calculate Ordinary AGI (Includes Social Security Torpedo)
        ordinary_agi = calculate_ordinary_adjusted_gross_income(
            federal_taxable_wages=federal_wages,
            income=income,
            traditional_withdrawals=plan.from_traditional_retirement,
            roth_earnings_withdrawals=plan.from_roth_retirement_earnings,
            hsa_non_medical_withdrawals=plan.from_hsa_nonmedical,
            trad_to_roth_conversion=plan.trad_to_roth_conversion,
            age=context.personal.age,
            ss_received=plan.social_security_recieved,
            ss_base_threshold=adj_ss_base,
            ss_upper_threshold=adj_ss_upper,
            ss_middle_tier_cap=adj_ss_mid_cap,
        )

        # D. Split Taxable Segments (Applies Standard Deduction)
        taxable_segments = calculate_taxable_segments(
            ordinary_agi=ordinary_agi, income=income, standard_deduction=std_deduction
        )

        # E. Calculate Federal Ordinary Income Tax
        ordinary_tax = calculate_ordinary_income_tax(
            ordinary_taxable_income=taxable_segments.ordinary_taxable,
            tax_brackets=adj_brackets,
        )

        # F. Calculate Capital Gains Tax
        ltcg_tax = calculate_capital_gains_tax(
            ordinary_taxable_income=taxable_segments.ordinary_taxable,
            taxable_ltcg=taxable_segments.taxable_ltcg,
            ltcg_brackets=adj_ltcg_brackets,
        )

        # G. Calculate Net Investment Income Tax (NIIT)
        # NII MAGI includes all ordinary AGI plus Long Term Capital Gains
        magi = ordinary_agi + income.long_term_gains

        nii_base = get_net_investment_income(
            income=income, taxable_ltcg=taxable_segments.taxable_ltcg
        )

        niit_tax = calculate_net_investment_income_tax(
            magi=magi,
            net_investment_income=nii_base,
            filing_status_threshold=adj_niit_threshold,
        )

        penalties = calculate_early_withdrawal_penalty(
            traditional_withdrawals=plan.from_traditional_retirement,
            hsa_non_medical_withdrawals=plan.from_hsa_nonmedical,
            roth_earnings_withdrawals=plan.from_roth_retirement_earnings,
            age=context.personal.age,
        )

        return fica_tax + ordinary_tax + ltcg_tax + niit_tax + penalties

    def get_bracket_limit(
        self, context: SimulationContext, target_rate: float
    ) -> float:
        """Adapter to fetch inflation-adjusted bracket limits."""
        inf = context.world.cumulative_inflation_index
        is_married = context.personal.marital_status == "married"

        std_deduction = (
            self.std_deduction_married if is_married else self.std_deduction_single
        ) * inf

        raw_brackets = self.brackets_married if is_married else self.brackets_single

        # Scale the brackets by inflation
        adj_brackets = [
            (limit * inf if limit != float("inf") else limit, rate)
            for limit, rate in raw_brackets
        ]

        return get_tax_bracket_limit(target_rate, adj_brackets, std_deduction)


class FlatStateIncomeTaxStrategy(RegulatoryCalculator):
    """
    Adapter that connects simulation state to the flat tax logic kernel.
    Useful for modeling state taxes (like the current 4.55% flat rate here in Utah).
    """

    def __init__(self, rate: float, label: str = "State Tax"):
        self.rate = rate
        self.label = label

    def __call__(
        self, context: "SimulationContext", plan: "YearlyDecisionsPlan"
    ) -> float:
        # Assuming your context.regulations handles the standard deduction application
        ordinary_income = context.regulations.get_taxable_income(context, plan)

        # Ensure we safely access the growth property, defaulting to 0.0 if not present
        growth_income = getattr(plan, "from_taxable_brokerage_growth", 0.0)

        # The new function requires the combined total of ordinary income and capital gains
        total_taxable = ordinary_income + growth_income

        return calculate_state_flat_tax(
            total_taxable_income=total_taxable,
            state_rate=self.rate,
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
    Generic ordinary adjusted gross income calculator that scales Social Security
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

    def __call__(
        self, context: "SimulationContext", plan: "YearlyDecisionsPlan"
    ) -> float:
        inf = context.world.cumulative_inflation_index

        income = IncomeSources(
            wages=plan.gross_earned_income,
            interest_and_dividends=0,  # TODO implement,
            short_term_gains=0,  # TODO implement
            long_term_gains=plan.from_taxable_brokerage_growth,
        )

        fica_wages = calculate_fica_taxable_wages(
            income=income,
            health_insurance_premiums=plan.payroll_to_health_premiums,
            payroll_to_hsa=plan.payroll_to_hsa,
        )
        federal_wages = calculate_federal_taxable_wages(
            fica_taxable_wages=fica_wages,
            payroll_to_trad_401k=getattr(plan, "payroll_to_trad_401k", 0.0),
            match_to_roth_401k=getattr(plan, "match_to_roth_401k", 0.0),
        )

        return calculate_ordinary_adjusted_gross_income(
            federal_taxable_wages=federal_wages,
            income=income,  # Added the required dataclass
            traditional_withdrawals=plan.from_traditional_retirement,
            roth_earnings_withdrawals=plan.from_roth_retirement_earnings,
            hsa_non_medical_withdrawals=plan.from_hsa_nonmedical,
            trad_to_roth_conversion=plan.trad_to_roth_conversion,
            age=context.personal.age,
            ss_received=plan.social_security_recieved,  # Kept your original spelling
            ss_base_threshold=self.ss_base_threshold * inf,
            ss_upper_threshold=self.ss_upper_threshold * inf,
            ss_middle_tier_cap=self.ss_middle_tier_cap * inf,
        )
