from dataclasses import dataclass

from model import (
    IncomeStrategy,
    InvestmentRebalancingStrategy,
    LifestyleSpendingStrategy,
    MortgageStrategy,
    PayrollStrategy,
    SavingsStrategy,
    TaxStrategy,
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
    tax_strat: TaxStrategy
    rebalance_strat: InvestmentRebalancingStrategy
