from dataclasses import replace
from models import (
    SimulationContext,
    YearlyDecisionsPlan,
    PayrollStrategy,
)


class MaximizeContributionsPayroll(PayrollStrategy):
    """
    Aggressively try to maximize all possible pre-tax contributions
    """

    def __init__(
        self,
        match_401k_percent: float = 1.0,  # 100% match
        match_401k_cap_percent: float = 0.04,  # Up to 4% of gross salary
        match_hsa_amount: float = 0,
    ):
        self.match_401k_percent = match_401k_percent
        self.match_401k_cap_percent = match_401k_cap_percent
        self.match_hsa = match_hsa_amount

    def __call__(
        self,
        context: SimulationContext,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # 1. Read the salary established by the IncomeStrategy
        salary = plan.gross_earned_income
        remaining_funds = max(0.0, salary)

        # If there's no income, payroll deductions are zero
        if remaining_funds <= 0:
            return plan

        # 2. Priority 1: HSA Contribution
        actual_hsa = min(
            remaining_funds,
            context.regulations.get_annual_hsa_limit(
                context.world, context.personal, plan
            ),
        )
        remaining_funds -= actual_hsa

        # 3. Priority 2: 401k Contribution
        actual_401k = min(
            remaining_funds,
            context.regulations.get_annual_401k_limit(
                context.world, context.personal, plan
            ),
        )
        remaining_funds -= actual_401k

        # 4. Calculate Employer Match
        # Match is based on the actual 401k contribution made
        potential_match = actual_401k * self.match_401k_percent
        actual_match = min(potential_match, salary * self.match_401k_cap_percent)

        # 5. Update the Ledger
        return replace(
            plan,
            pretax_to_trad_401k=actual_401k,
            pretax_to_hsa=actual_hsa,
            match_to_trad_401k=actual_match,
            match_to_hsa=self.match_hsa if actual_hsa > 0 else 0,
        )
