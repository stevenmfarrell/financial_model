from dataclasses import replace

from models import FinancialState, PersonalState, WorldState


class ConstantAllocationRebalance:
    """Rebalances to a constant stock/bond allocation every year."""

    def __init__(self, target_stock_ratio: float):
        self.target_stock_ratio = target_stock_ratio

    def __call__(
        self, financial: FinancialState, personal: PersonalState
    ) -> FinancialState:
        # Simply updates the allocation percentages for the next year
        return replace(
            financial,
            taxable_brokerage_stock_allocation=self.target_stock_ratio,
            traditional_retirement_stock_allocation=self.target_stock_ratio,
            roth_retirement_stock_allocation=self.target_stock_ratio,
            hsa_stock_allocation=self.target_stock_ratio,
        )


class GlidePathRebalance:
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

    def __call__(
        self, world: WorldState, financial: FinancialState, personal: PersonalState
    ) -> FinancialState:
        if personal.age <= self.glide_start_age:
            stock_ratio = self.initial_stock_ratio
        elif personal.age >= self.glide_end_age:
            stock_ratio = self.final_stock_ratio
        else:
            years_into_glide_path = personal.age - self.glide_start_age
            stock_ratio = self.initial_stock_ratio - (
                years_into_glide_path / (self.glide_end_age - self.glide_start_age)
            ) * (self.initial_stock_ratio - self.final_stock_ratio)

        return replace(
            financial,
            taxable_brokerage_stock_allocation=stock_ratio,
            traditional_retirement_stock_allocation=stock_ratio,
            roth_retirement_stock_allocation=stock_ratio,
            hsa_stock_allocation=stock_ratio,
        )
