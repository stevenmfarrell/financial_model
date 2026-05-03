from dataclasses import replace

from models import (
    FinancialState,
    SimulationContext,
    WithdrawalStrategy,
    YearlyDecisionsPlan,
)
from regulatory_kernel.limits import calculate_uniform_lifetime_divisor


class SequentialWithdrawal(WithdrawalStrategy):
    """
    Meets cash shortfall by withdrawing from assets in an age-optimized order.
    The sequence shifts at age 60 (penalty-free Roth/Trad) and age 65 (penalty-free HSA).
    This sequence minimizes the taxes due any particular year.
    """

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        financial = context.financial
        age = context.personal.age

        plan = replace(
            plan,
            from_traditional_retirement=0,
            from_hsa_nonmedical=0,
            from_taxable_brokerage_growth=0,
            from_taxable_brokerage_basis=0,
            from_roth_retirement_basis=0,
            from_roth_conversion_penalized=0,
            from_roth_retirement_earnings=0,
            from_cash_reserve=0,
        )

        # --- Required Minimum Distribution (RMD) logic ---
        rmd_amount = 0.0
        # RMD Age is 73 for those born after 1950, 75 for those born after 1959
        rmd_start_age = 75
        if age >= rmd_start_age:
            divisor = calculate_uniform_lifetime_divisor(age)
            if divisor > 0:
                rmd_amount = financial.traditional_retirement_balance / divisor

        # Apply RMD immediately to the plan
        plan = replace(plan, from_traditional_retirement=rmd_amount)
        # ----------------------

        shortfall = max(0.0, plan.current_cash_shortfall)

        if shortfall <= 0:
            return plan

        # 1. Define the optimal sequence based on current age
        if age < 60:
            # Pre-60: Avoid 10% penalty on Trad/Roth, 20% on HSA.
            # Order: Cash -> Brokerage -> Roth Basis -> Trad -> Roth Earnings -> HSA
            order = ["cash", "brokerage", "roth_basis", "trad", "roth_earnings", "hsa"]
        elif age < 65:
            # 60-64: Trad/Roth penalties gone. Roth (Tax-Free) > Trad (Taxable).
            # Order: Cash -> Brokerage -> Roth Basis -> Roth Earnings -> Trad -> HSA
            order = ["cash", "brokerage", "roth_basis", "roth_earnings", "trad", "hsa"]
        else:
            # 65+: All penalties gone. HSA/Trad are functionally tied (income tax).
            order = ["cash", "brokerage", "roth_basis", "roth_earnings", "trad", "hsa"]

        # 2. Execute withdrawal waterfall
        updates = {}
        for bucket in order:
            if shortfall <= 0:
                break

            withdrawn, shortfall, bucket_updates = self._withdraw_from_bucket(
                bucket, shortfall, financial
            )
            updates.update(bucket_updates)

        return replace(plan, **updates)

    def _withdraw_from_bucket(
        self, bucket: str, shortfall: float, financial: FinancialState
    ):
        """Dispatches to the specific helper for the given bucket name."""
        helpers = {
            "cash": self._withdraw_cash,
            "brokerage": self._withdraw_brokerage,
            "roth_basis": self._withdraw_roth_basis,
            "trad": self._withdraw_trad,
            "roth_earnings": self._withdraw_roth_earnings,
            "hsa": self._withdraw_hsa_nonmedical,
        }
        return helpers[bucket](shortfall, financial)

    def _withdraw_cash(self, shortfall: float, financial: FinancialState):
        amount = min(shortfall, financial.cash_balance)
        return amount, shortfall - amount, {"from_cash_reserve": amount}

    def _withdraw_brokerage(self, shortfall: float, financial: FinancialState):
        amount = min(shortfall, financial.taxable_brokerage_balance)
        basis_ratio = 0.0
        if amount > 0 and financial.taxable_brokerage_balance > 0:
            basis_ratio = (
                financial.taxable_brokerage_basis / financial.taxable_brokerage_balance
            )

        # Apply a parabolic basis skew formula
        # This simulates picking high-basis lots first.
        skewed_basis_fraction = 1.0 - (1.0 - basis_ratio) ** 2

        # Determine the dollar amounts
        basis_withdrawn = min(
            amount * skewed_basis_fraction, financial.taxable_brokerage_basis
        )
        growth_withdrawn = amount - basis_withdrawn

        return (
            amount,
            shortfall - amount,
            {
                "from_taxable_brokerage_basis": basis_withdrawn,
                "from_taxable_brokerage_growth": growth_withdrawn,
            },
        )

    def _withdraw_roth_basis(self, shortfall: float, financial: FinancialState):
        amount = min(shortfall, financial.roth_basis)
        return amount, shortfall - amount, {"from_roth_retirement_basis": amount}

    def _withdraw_trad(self, shortfall: float, financial: FinancialState):
        amount = min(shortfall, financial.traditional_retirement_balance)
        return amount, shortfall - amount, {"from_traditional_retirement": amount}

    def _withdraw_roth_earnings(self, shortfall: float, financial: FinancialState):
        # Balance minus basis = earnings
        earnings_avail = max(
            0.0, financial.roth_retirement_balance - financial.roth_basis
        )
        amount = min(shortfall, earnings_avail)
        return amount, shortfall - amount, {"from_roth_retirement_earnings": amount}

    def _withdraw_hsa_nonmedical(self, shortfall: float, financial: FinancialState):
        amount = min(shortfall, financial.hsa_balance)
        return amount, shortfall - amount, {"from_hsa_nonmedical": amount}
