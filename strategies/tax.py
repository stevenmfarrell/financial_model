from dataclasses import replace
from typing import Literal
from model import (
    FinancialState,
    PersonalState,
    YearlyDecisionsPlan,
    TaxStrategy,
)


class USFederalIncomeTax2026(TaxStrategy):
    """
    Implements 2026 US Federal logic with inflation-indexed brackets
    and early withdrawal penalties.
    """

    def __init__(self, filing_status: Literal["single", "mfj"] = "single"):
        self.filing_status = filing_status
        self.standard_deduction = 16100 if filing_status == "single" else 32200

        # FICA rates and base
        self.ss_rate, self.ss_wage_base = 0.062, 184500
        self.med_rate, self.addl_med_rate = 0.0145, 0.009
        self.addl_med_threshold = 200000 if filing_status == "single" else 250000

        # Base 2026 brackets (to be scaled by inflation index)
        if filing_status == "single":
            self.brackets = [
                (12400, 0.10),
                (50400, 0.12),
                (105700, 0.22),
                (201775, 0.24),
                (256225, 0.32),
                (640600, 0.35),
                (float("inf"), 0.37),
            ]
        else:
            self.brackets = [
                (24800, 0.10),
                (100800, 0.12),
                (211400, 0.22),
                (403550, 0.24),
                (512450, 0.32),
                (768700, 0.35),
                (float("inf"), 0.37),
            ]

    def __call__(
        self,
        financial: FinancialState,
        personal: PersonalState,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # 1. Inflation Adjustment
        # Scale deduction and brackets to maintain real-dollar thresholds
        inf_factor = financial.cumulative_inflation_index
        adj_standard_deduction = self.standard_deduction * inf_factor

        # 2. FICA Calculation (using nominal wages)
        wages = plan.gross_earned_income
        ss_tax = min(wages, self.ss_wage_base * inf_factor) * self.ss_rate
        med_tax = wages * self.med_rate
        addl_med_tax = (
            max(0, wages - (self.addl_med_threshold * inf_factor)) * self.addl_med_rate
        )
        fica_total = ss_tax + med_tax + addl_med_tax

        # 3. Income Tax Calculation
        taxable_base = max(0.0, plan.total_taxable_income - adj_standard_deduction)
        income_tax = 0.0
        prev_limit = 0.0

        for limit, rate in self.brackets:
            # Scale bracket limit by inflation (except for infinity)
            adj_limit = limit * inf_factor if limit != float("inf") else limit

            taxable_in_bracket = min(taxable_base, adj_limit) - prev_limit
            if taxable_in_bracket > 0:
                income_tax += taxable_in_bracket * rate
            prev_limit = adj_limit
            if taxable_base <= adj_limit:
                break

        # 4. Early Withdrawal Penalty
        # 10% penalty on Traditional distributions before age 59.5
        # Since age is an integer in the model, we use < 60 as the penalty threshold
        early_withdrawal_penalty = 0.0
        if personal.age < 60:
            early_withdrawal_penalty = plan.from_traditional_retirement * 0.10

        # 20% penalty on HSA distributions for non-medical use before age 65
        hsa_penalty = 0.20 * plan.from_hsa if personal.age < 65 else 0.0

        # Return updated plan with cumulative taxes
        return replace(
            plan,
            to_taxes=plan.to_taxes
            + fica_total
            + income_tax
            + early_withdrawal_penalty
            + hsa_penalty,
        )


class BrokerageCapitalGainsTax(TaxStrategy):
    """Calculates tax on the 'Gain' portion of brokerage liquidations."""

    def __init__(self, long_term_rate: float = 0.15):
        self.rate = long_term_rate

    def __call__(
        self, financial: FinancialState, personal: PersonalState, plan
    ) -> YearlyDecisionsPlan:
        if plan.from_taxable_brokerage <= 0 or financial.taxable_brokerage_balance <= 0:
            return plan

        # Determine how much of the withdrawal is actually a gain
        gain_ratio = (
            financial.taxable_brokerage_balance - financial.taxable_brokerage_basis
        ) / financial.taxable_brokerage_balance
        taxable_gain = plan.from_taxable_brokerage * max(0.0, gain_ratio)

        cap_gains_tax = taxable_gain * self.rate

        # Stack this tax on top of whatever is already there
        return replace(plan, to_taxes=plan.to_taxes + cap_gains_tax)


class FlatIncomeTaxStrategy(TaxStrategy):
    """
    Applies a simple flat percentage tax to all taxable income.
    Useful for modeling state taxes (e.g., Utah's 4.65% rate).
    """

    def __init__(self, rate: float, label: str = "State Tax"):
        self.rate = rate
        self.label = label

    def __call__(self, financial, personal, plan) -> YearlyDecisionsPlan:
        # Calculate ordinary taxable income
        taxable_base = plan.total_taxable_income

        # Add capital gains from brokerage if they exist
        if plan.from_taxable_brokerage > 0 and financial.taxable_brokerage_balance > 0:
            gain_ratio = (
                financial.taxable_brokerage_balance - financial.taxable_brokerage_basis
            ) / financial.taxable_brokerage_balance
            taxable_gain = plan.from_taxable_brokerage * max(0.0, gain_ratio)
            taxable_base += taxable_gain

        tax_amount = taxable_base * self.rate
        return replace(plan, to_taxes=plan.to_taxes + tax_amount)


class CombinedTaxStrategy(TaxStrategy):
    """Aggregates multiple tax components (Fed, State, Gains)."""

    def __init__(self, *strategies: TaxStrategy):
        self.strategies = strategies

    def __call__(self, state, personal, plan) -> YearlyDecisionsPlan:
        # We reset the to_taxes to 0 before running the stack to avoid double-counting
        # during the iterative solver loops.
        current_plan = replace(plan, to_taxes=0.0)

        for strat in self.strategies:
            current_plan = strat(state, personal, current_plan)

        return current_plan
