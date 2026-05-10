from dataclasses import replace
from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    IncomeStrategy,
)


class RetirementWages(IncomeStrategy):
    """
    Models a standard career path: constant real wage until a specific
    retirement age, then zero earned income.
    """

    def __init__(self, initial_salary: float, retirement_age: int):
        self.initial_salary = initial_salary
        self.retirement_age = retirement_age

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # Determine the real wage based on age
        real_wage = (
            0.0 if context.personal.age >= self.retirement_age else self.initial_salary
        )

        # Inflate to nominal dollars
        nominal_income = real_wage * context.world.cumulative_inflation_index

        return replace(plan, gross_earned_income=nominal_income)


class BaristaRetirementWages(IncomeStrategy):
    """
    Models a 'Barista FIRE' path: high-earning years followed by a
    lower-stress, lower-paying role before full retirement.
    """

    def __init__(
        self,
        initial_salary: float,
        barista_salary: float,
        barista_retirement_age: int,
        full_retirement_age: int,
    ):
        self.initial_salary = initial_salary
        self.barista_salary = barista_salary
        self.barista_retirement_age = barista_retirement_age
        self.full_retirement_age = full_retirement_age

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # Step-down logic for real wages
        if context.personal.age >= self.full_retirement_age:
            real_wage = 0.0
        elif context.personal.age >= self.barista_retirement_age:
            real_wage = self.barista_salary
        else:
            real_wage = self.initial_salary

        # Inflate to nominal dollars
        nominal_income = real_wage * context.world.cumulative_inflation_index

        return replace(plan, gross_earned_income=nominal_income)


class SocialSecurityIncome(IncomeStrategy):
    """
    Models income received by Social Security
    """

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        social_security_received = context.regulations.get_social_security_benefits(
            context, plan
        )
        return replace(plan, social_security_received=social_security_received)


class InvestmentIncomeStrategy(IncomeStrategy):
    """Get income from interest, dividends and bond yields in taxable accounts. Tax advantaged accounts are not considered."""

    # TODO cash interest reserves should count here
    def __call__(
        self, context: SimulationContext, decisions: YearlyDecisionsPlan
    ) -> YearlyDecisionsPlan:
        financial = context.financial
        market = context.market
        brokerage_stock_dividends = (
            financial.taxable_brokerage_balance
            * financial.taxable_brokerage_stock_allocation
            * market.annual_stock_dividend_yield
        )
        brokerage_bond_yield_cash = (
            financial.taxable_brokerage_balance
            * (1 - financial.taxable_brokerage_stock_allocation)
            * market.annual_stock_dividend_yield
        )
        cash_interest = market.annual_cash_return * financial.cash_balance
        return replace(
            decisions,
            ordinary_dividends_received=0.05 * brokerage_stock_dividends
            + brokerage_bond_yield_cash
            + cash_interest,
            qualified_dividends_received=0.95 * brokerage_stock_dividends,
        )
