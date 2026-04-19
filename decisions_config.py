from dataclasses import dataclass

from models import (
    IncomeStrategy,
    InvestmentRebalancingStrategy,
    LifestyleSpendingStrategy,
    MortgageStrategy,
    PayrollStrategy,
    SavingsStrategy,
    WithdrawalStrategy,
)


@dataclass(frozen=True, kw_only=True)
class YearlyDecisionsConfiguration:
    income_strat: IncomeStrategy
    payroll_strat: PayrollStrategy
    mortgage_strat: MortgageStrategy
    savings_strat: SavingsStrategy
    withdrawal_strat: WithdrawalStrategy
    lifestyle_spending_strat: LifestyleSpendingStrategy
    rebalance_strat: InvestmentRebalancingStrategy
