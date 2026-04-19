from dataclasses import replace
from models import (
    FinancialState,
    PersonalState,
    WorldState,
    YearlyDecisionsPlan,
    PayrollStrategy,
)


class StandardPayrollStrategy(PayrollStrategy):
    """
    Manages statutory and elective payroll deductions.
    Calculates 401k contributions, HSA deferrals, and employer matching logic.
    """

    def __init__(
        self,
        trad_401k_contribution: float = 23500.0,  # 2026 Projected Limit
        hsa_contribution: float = 4300.0,  # 2026 Projected Individual Limit
        match_percent: float = 1.0,  # 100% match
        match_cap_percent: float = 0.04,  # Up to 4% of gross salary
        match_hsa: float = 0,
    ):
        self.trad_401k_contribution = trad_401k_contribution
        self.hsa_contribution = hsa_contribution
        self.match_percent = match_percent
        self.match_cap_percent = match_cap_percent
        self.match_hsa = match_hsa

    def __call__(
        self,
        world: WorldState,
        financial: FinancialState,
        personal: PersonalState,
        plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        # 1. Read the salary established by the IncomeStrategy
        salary = plan.gross_earned_income
        remaining_funds = max(0.0, salary)

        # If there's no income, payroll deductions are zero
        if remaining_funds <= 0:
            return plan

        # 2. Priority 1: HSA Contribution
        actual_hsa = min(remaining_funds, self.hsa_contribution)
        remaining_funds -= actual_hsa

        # 3. Priority 2: 401k Contribution
        actual_401k = min(remaining_funds, self.trad_401k_contribution)
        remaining_funds -= actual_401k

        # 4. Calculate Employer Match
        # Match is based on the actual 401k contribution made
        potential_match = actual_401k * self.match_percent
        actual_match = min(potential_match, salary * self.match_cap_percent)

        # 5. Update the Ledger
        return replace(
            plan,
            pretax_to_trad_401k=actual_401k,
            pretax_to_hsa=actual_hsa,
            match_to_trad_401k=actual_match,
            match_to_hsa=self.match_hsa if actual_hsa > 0 else 0,
        )
