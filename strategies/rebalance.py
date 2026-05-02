from dataclasses import replace

from models import (
    FinancialState,
    InvestmentRebalancingStrategy,
    SimulationContext,
)


def linear_rebalance_calculator(
    age: int,
    initial_stock_ratio: float = 0.9,
    final_stock_ratio: float = 0.2,
    glide_start_age: int = 30,
    glide_end_age: int = 65,
) -> float:
    if age <= glide_start_age:
        stock_ratio = initial_stock_ratio
    elif age >= glide_end_age:
        stock_ratio = final_stock_ratio
    else:
        years_into_glide_path = age - glide_start_age
        stock_ratio = initial_stock_ratio - (
            years_into_glide_path / (glide_end_age - glide_start_age)
        ) * (initial_stock_ratio - final_stock_ratio)
    return stock_ratio


class ConstantAllocationRebalance(InvestmentRebalancingStrategy):
    """Rebalances to a constant stock/bond allocation every year."""

    def __init__(self, target_stock_ratio: float):
        self.target_stock_ratio = target_stock_ratio

    def __call__(self, context: SimulationContext) -> FinancialState:
        # Simply updates the allocation percentages for the next year
        return replace(
            context.financial,
            taxable_brokerage_stock_allocation=self.target_stock_ratio,
            traditional_retirement_stock_allocation=self.target_stock_ratio,
            roth_retirement_stock_allocation=self.target_stock_ratio,
            hsa_stock_allocation=self.target_stock_ratio,
        )


class GlidePathRebalance(InvestmentRebalancingStrategy):
    """Starts with a high stock allocation and gradually reduces it as you age."""

    def __init__(
        self,
        initial_stock_ratio: float = 0.9,
        final_stock_ratio: float = 0.2,
        glide_start_age: int = 30,
        glide_end_age: int = 65,
    ):
        self.initial_stock_ratio = initial_stock_ratio
        self.final_stock_ratio = final_stock_ratio
        self.glide_start_age = glide_start_age
        self.glide_end_age = glide_end_age

    def __call__(self, context: SimulationContext) -> FinancialState:
        stock_ratio = linear_rebalance_calculator(
            context.personal.age,
            self.initial_stock_ratio,
            self.final_stock_ratio,
            self.glide_start_age,
            self.glide_end_age,
        )

        return replace(
            context.financial,
            taxable_brokerage_stock_allocation=stock_ratio,
            traditional_retirement_stock_allocation=stock_ratio,
            roth_retirement_stock_allocation=stock_ratio,
            hsa_stock_allocation=stock_ratio,
        )


class TaxAwareGlidePathRebalance(InvestmentRebalancingStrategy):
    """Rebalance to a target overall allocation by age, prioritizing stocks in tax advantaged hsa and roth accounts, and bonds in traditional accounts"""

    def __init__(
        self,
        initial_stock_ratio: float = 0.9,
        final_stock_ratio: float = 0.2,
        glide_start_age: int = 30,
        glide_end_age: int = 65,
    ):
        self.initial_stock_ratio = initial_stock_ratio
        self.final_stock_ratio = final_stock_ratio
        self.glide_start_age = glide_start_age
        self.glide_end_age = glide_end_age

    def __call__(self, context: SimulationContext) -> FinancialState:
        financial = context.financial
        stock_ratio = linear_rebalance_calculator(
            context.personal.age,
            self.initial_stock_ratio,
            self.final_stock_ratio,
            self.glide_start_age,
            self.glide_end_age,
        )

        investments = (
            financial.hsa_balance
            + financial.traditional_retirement_balance
            + financial.roth_retirement_balance
            + financial.taxable_brokerage_balance
        )
        remaining_stock_to_allocate = stock_ratio * investments

        # 3. Tax-Efficient Allocation Waterfall
        # Order: HSA -> Roth -> Brokerage -> Traditional
        # This prioritizes tax-free growth and preferential capital gains rates.

        # HSA Allocation
        hsa_stock_amt = min(financial.hsa_balance, remaining_stock_to_allocate)
        hsa_alloc = (
            hsa_stock_amt / financial.hsa_balance if financial.hsa_balance > 0 else 0
        )
        remaining_stock_to_allocate -= hsa_stock_amt

        # Roth Allocation
        roth_stock_amt = min(
            financial.roth_retirement_balance, remaining_stock_to_allocate
        )
        roth_alloc = (
            roth_stock_amt / financial.roth_retirement_balance
            if financial.roth_retirement_balance > 0
            else 0
        )
        remaining_stock_to_allocate -= roth_stock_amt

        # Taxable Brokerage Allocation
        brokerage_stock_amt = min(
            financial.taxable_brokerage_balance, remaining_stock_to_allocate
        )
        brokerage_alloc = (
            brokerage_stock_amt / financial.taxable_brokerage_balance
            if financial.taxable_brokerage_balance > 0
            else 0
        )
        remaining_stock_to_allocate -= brokerage_stock_amt

        # Traditional Retirement Allocation (The "Bond Bucket")
        trad_stock_amt = min(
            financial.traditional_retirement_balance, remaining_stock_to_allocate
        )
        trad_alloc = (
            trad_stock_amt / financial.traditional_retirement_balance
            if financial.traditional_retirement_balance > 0
            else 0
        )

        return replace(
            financial,
            hsa_stock_allocation=hsa_alloc,
            roth_retirement_stock_allocation=roth_alloc,
            taxable_brokerage_stock_allocation=brokerage_alloc,
            traditional_retirement_stock_allocation=trad_alloc,
        )
