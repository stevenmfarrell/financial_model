from dataclasses import replace
from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    WithdrawalStrategy,
)


class SequentialWithdrawal(WithdrawalStrategy):
    """
    Meets any cash shortfall by withdrawing from assets in a specific
    tax-efficient order: Cash -> Brokerage -> Traditional -> Roth.
    """

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        financial = context.financial
        # 1. Identify how much cash we actually need to find
        # If shortfall is negative, we have a surplus and don't need to withdraw.
        shortfall = max(0.0, plan.current_cash_shortfall)

        if shortfall <= 0:
            return plan

        # 2. Sequential Liquidation Logic
        # We check the actual 'state' for available balances

        # Priority 1: Cash Reserves
        from_cash = min(shortfall, financial.cash_balance)
        shortfall -= from_cash

        # Priority 2: Taxable Brokerage
        from_brokerage = min(shortfall, financial.taxable_brokerage_balance)
        from_taxable_brokerage_basis = 0.0
        from_taxable_brokerage_growth = 0.0
        if from_brokerage > 0 and financial.taxable_brokerage_balance > 0:
            # Calculate what percentage of the account is basis
            basis_ratio = (
                financial.taxable_brokerage_basis / financial.taxable_brokerage_balance
            )
            from_taxable_brokerage_basis = from_brokerage * basis_ratio
            from_taxable_brokerage_growth = (
                from_brokerage - from_taxable_brokerage_basis
            )

        shortfall -= from_brokerage

        # Priority 3: Traditional Retirement (Taxable)
        from_trad = min(shortfall, financial.traditional_retirement_balance)
        shortfall -= from_trad

        # Priority 4: Roth Retirement (Tax-Free)
        from_roth = min(shortfall, financial.roth_retirement_balance)
        shortfall -= from_roth

        # Priority 5: HSA (Tax-Free for medical, or taxable after 65)
        from_hsa = min(shortfall, financial.hsa_balance)
        shortfall -= from_hsa

        # 3. Update the Plan
        return replace(
            plan,
            from_cash_reserve=from_cash,
            from_taxable_brokerage_basis=from_taxable_brokerage_basis,
            from_taxable_brokerage_growth=from_taxable_brokerage_growth,
            from_traditional_retirement=from_trad,
            from_roth_retirement=from_roth,
            from_hsa=from_hsa,
        )
