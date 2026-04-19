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


class CombinedIncome(IncomeStrategy):
    def __init__(self, *strats: IncomeStrategy):
        self.strats = strats

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        gross_earned_income = 0
        other_taxable_income = 0
        social_security_recieved = 0
        for strat in self.strats:
            result = strat(context, plan)
            gross_earned_income += result.gross_earned_income
            other_taxable_income += result.other_taxable_income
            social_security_recieved += result.social_security_recieved

        return replace(
            plan,
            gross_earned_income=gross_earned_income,
            social_security_recieved=social_security_recieved,
            other_taxable_income=other_taxable_income,
        )


class SocialSecurityIncome(IncomeStrategy):
    """
    Models income recieved by Social Security
    """

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        social_security_recieved = context.regulations.get_social_security_benefits(
            context, plan
        )
        return replace(plan, social_security_recieved=social_security_recieved)
