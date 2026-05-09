from dataclasses import replace
from typing import Optional

from models import (
    LifestyleSpendingStrategy,
    SimulationContext,
    YearlyDecisionsPlan,
)


class InflationAdjustedSpending(LifestyleSpendingStrategy):
    """
    Calculates desired lifestyle spending by adjusting a base 'Year 0'
    amount for the cumulative effects of inflation.
    """

    def __init__(self, base_spending_today_dollars: float):
        """
        base_spending_today_dollars: The amount you want to spend in Year 0 purchasing power.
        """
        self.base_spending = base_spending_today_dollars

    def __call__(
        self,
        context: SimulationContext,
        existing_plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        nominal_spending = self.base_spending * context.world.cumulative_inflation_index
        return replace(existing_plan, to_lifestyle_spending=nominal_spending)


class GuytonKlingerSpendingStrategy(LifestyleSpendingStrategy):
    def __init__(
        self,
        base_spending_today_dollars: float,
        activation_age: int,
        absolute_floor_today_dollars: float,  # <--- NEW: Hard minimum
        absolute_ceiling_today_dollars: float,  # <--- NEW: Hard maximum
        capital_preservation_trigger: float = 1.20,
        prosperity_trigger: float = 0.80,
        adjustment_cut: float = 0.10,
        adjustment_increase: float = 0.10,
        apply_portfolio_rule: bool = True,
    ):
        self.base_spending = base_spending_today_dollars
        self.activation_age = activation_age
        self.absolute_floor = absolute_floor_today_dollars
        self.absolute_ceiling = absolute_ceiling_today_dollars
        self.preservation_trigger = capital_preservation_trigger
        self.prosperity_trigger = prosperity_trigger
        self.adjustment_cut = adjustment_cut
        self.adjustment_increase = adjustment_increase
        self.apply_portfolio_rule = apply_portfolio_rule

        # State tracked for a single Monte Carlo trial
        self._current_nominal_spending = base_spending_today_dollars
        self._previous_inflation_index = 1.0
        self._initial_withdrawal_rate: Optional[float] = None
        self._previous_portfolio_value: Optional[float] = None

    def __call__(
        self,
        context: SimulationContext,
        existing_plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:

        current_portfolio = context.financial.liquid_assets
        current_inflation_index = context.world.cumulative_inflation_index
        marginal_inflation = current_inflation_index / self._previous_inflation_index

        is_active = context.personal.age >= self.activation_age

        # 1. Apply the Portfolio Rule (Only if active)
        if (
            is_active
            and self.apply_portfolio_rule
            and self._previous_portfolio_value is not None
            and current_portfolio < self._previous_portfolio_value
        ):
            marginal_inflation = 1.0

        proposed_spending = self._current_nominal_spending * marginal_inflation

        fixed_income = (
            existing_plan.social_security_received
            + existing_plan.gross_earned_income
            + existing_plan.other_taxable_income
        )
        required_withdrawal = max(0.0, proposed_spending - fixed_income)

        # 2. Apply Dynamic Guardrails (Only if active and portfolio exists)
        if is_active and current_portfolio > 0:
            current_withdrawal_rate = required_withdrawal / current_portfolio

            if self._initial_withdrawal_rate is None:
                self._initial_withdrawal_rate = current_withdrawal_rate
            else:
                if current_withdrawal_rate > (
                    self._initial_withdrawal_rate * self.preservation_trigger
                ):
                    proposed_spending *= 1 - self.adjustment_cut
                elif current_withdrawal_rate < (
                    self._initial_withdrawal_rate * self.prosperity_trigger
                ):
                    proposed_spending *= 1 + self.adjustment_increase

        # 3. Apply Absolute Guardrails (The Hard Clamps)
        nominal_floor = self.absolute_floor * current_inflation_index
        nominal_ceiling = self.absolute_ceiling * current_inflation_index

        # Clamp the proposed spending between the inflation-adjusted floor and ceiling
        proposed_spending = max(nominal_floor, min(proposed_spending, nominal_ceiling))

        # 4. Persist state for the next simulated year
        self._current_nominal_spending = proposed_spending
        self._previous_inflation_index = current_inflation_index
        self._previous_portfolio_value = current_portfolio

        return replace(existing_plan, to_lifestyle_spending=proposed_spending)
