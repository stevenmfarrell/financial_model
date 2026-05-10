from dataclasses import replace
from typing import Protocol

from models import (
    FinancialState,
    InvestmentRebalancingStrategy,
    SimulationContext,
)


class TargetAllocationProtocol(Protocol):
    """
    Implementations must take an age and return a target stock ratio.
    """

    def __call__(self, age: int) -> float: ...


class LinearGlidePath:
    """
    Implements TargetAllocationProtocol.
    Calculates a stock ratio that transitions linearly between two ages.
    """

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

    def __call__(self, age: int) -> float:
        # Before the glide begins
        if age <= self.glide_start_age:
            return self.initial_stock_ratio

        # After the glide ends
        if age >= self.glide_end_age:
            return self.final_stock_ratio

        # Linear interpolation logic
        age_range = self.glide_end_age - self.glide_start_age
        ratio_range = self.final_stock_ratio - self.initial_stock_ratio

        # Progress is a value from 0.0 to 1.0
        progress = (age - self.glide_start_age) / age_range

        return self.initial_stock_ratio + (progress * ratio_range)


class BondTentGlidePath:
    """
    Implements TargetAllocationProtocol.
    Creates a V-shaped (or 'Tent') allocation:
    1. High stock ratio early on.
    2. Linear glide-down to a 'Peak' (lowest stock point) at retirement.
    3. Linear glide-up back to a higher target post-retirement.
    """

    def __init__(
        self,
        initial_stock_ratio: float = 0.9,
        peak_stock_ratio: float = 0.6,
        final_stock_ratio: float = 0.8,
        glide_down_start_age: int = 35,
        retirement_age: int = 45,
        glide_up_end_age: int = 55,
    ):
        self.initial_stock_ratio = initial_stock_ratio
        self.peak_stock_ratio = peak_stock_ratio
        self.final_stock_ratio = final_stock_ratio

        self.glide_down_start_age = glide_down_start_age
        self.retirement_age = retirement_age
        self.glide_up_end_age = glide_up_end_age

    def __call__(self, age: int) -> float:
        # Phase 1: Pre-Glide (The Build-up)
        if age <= self.glide_down_start_age:
            return self.initial_stock_ratio

        # Phase 2: Glide-Down (Approaching Retirement)
        if self.glide_down_start_age < age < self.retirement_age:
            progress = (age - self.glide_down_start_age) / (
                self.retirement_age - self.glide_down_start_age
            )
            return self.initial_stock_ratio + progress * (
                self.peak_stock_ratio - self.initial_stock_ratio
            )

        # Phase 3: The Peak (The Retirement Date)
        if age == self.retirement_age:
            return self.peak_stock_ratio

        # Phase 4: Glide-Up (Post-Retirement Recovery)
        if self.retirement_age < age < self.glide_up_end_age:
            progress = (age - self.retirement_age) / (
                self.glide_up_end_age - self.retirement_age
            )
            return self.peak_stock_ratio + progress * (
                self.final_stock_ratio - self.peak_stock_ratio
            )

        # Phase 5: Steady State (Late Retirement)
        return self.final_stock_ratio


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

    def __init__(self, target_allocation_provider: TargetAllocationProtocol):
        self.target_allocation_provider = target_allocation_provider

    def __call__(self, context: SimulationContext) -> FinancialState:

        # 1. Determine Target Stock Ratio for the current age
        stock_ratio = self.target_allocation_provider(context.personal.age)

        return replace(
            context.financial,
            traditional_retirement_stock_allocation=stock_ratio,
            roth_retirement_stock_allocation=stock_ratio,
            hsa_stock_allocation=stock_ratio,
        )


class TaxAwareGlidePathRebalance(InvestmentRebalancingStrategy):
    """Rebalance to a target overall allocation by age, prioritizing stocks in tax advantaged hsa and roth accounts, and bonds in traditional accounts"""

    def __init__(self, target_allocation_provider: TargetAllocationProtocol):
        self.target_allocation_provider = target_allocation_provider

    def __call__(self, context: SimulationContext) -> FinancialState:
        financial = context.financial

        # 1. Determine Target Stock Ratio for the current age
        stock_ratio = self.target_allocation_provider(context.personal.age)

        # 2. Calculate Total Portfolio Value
        total_investments = (
            financial.hsa_balance
            + financial.traditional_retirement_balance
            + financial.roth_retirement_balance
            + financial.taxable_brokerage_balance
        )
        total_target_stock_dollars = stock_ratio * total_investments

        # 3. Account for Taxable holdings first
        # We assume the taxable mix is a fixed constraint to avoid triggering capital gains
        taxable_stock_dollars = (
            financial.taxable_brokerage_balance
            * financial.taxable_brokerage_stock_allocation
        )

        # This is the amount of stock we need to place in tax-advantaged accounts
        remaining_stock_to_allocate = max(
            0, total_target_stock_dollars - taxable_stock_dollars
        )

        # 4. Tax-Efficient Allocation Waterfall
        # Priority Order: HSA -> Roth -> Traditional

        # HSA Allocation (Prioritize highest growth here)
        hsa_stock_amt = min(financial.hsa_balance, remaining_stock_to_allocate)
        hsa_alloc = (
            hsa_stock_amt / financial.hsa_balance if financial.hsa_balance > 0 else 0
        )
        remaining_stock_to_allocate -= hsa_stock_amt

        # Roth Allocation (Second priority for growth)
        roth_stock_amt = min(
            financial.roth_retirement_balance, remaining_stock_to_allocate
        )
        roth_alloc = (
            roth_stock_amt / financial.roth_retirement_balance
            if financial.roth_retirement_balance > 0
            else 0
        )
        remaining_stock_to_allocate -= roth_stock_amt

        # Traditional Allocation (The "Bond Bucket" / Remaining Stocks)
        # Anything not filled by HSA/Roth or required for the bond target goes here.
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
            traditional_retirement_stock_allocation=trad_alloc,
        )
