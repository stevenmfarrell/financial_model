from dataclasses import replace
from models import (
    FinancialState,
    PersonalState,
    WorldState,
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
        world: WorldState,
        financial: FinancialState,
        personal: PersonalState,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # Determine the real wage based on age
        real_wage = 0.0 if personal.age >= self.retirement_age else self.initial_salary

        # Inflate to nominal dollars
        nominal_income = real_wage * world.cumulative_inflation_index

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
        world: WorldState,
        financial: FinancialState,
        personal: PersonalState,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # Step-down logic for real wages
        if personal.age >= self.full_retirement_age:
            real_wage = 0.0
        elif personal.age >= self.barista_retirement_age:
            real_wage = self.barista_salary
        else:
            real_wage = self.initial_salary

        # Inflate to nominal dollars
        nominal_income = real_wage * world.cumulative_inflation_index

        return replace(plan, gross_earned_income=nominal_income)
