from dataclasses import dataclass
from typing import Callable, Literal, Protocol


@dataclass(frozen=True)
class WorldState:
    year: int
    cumulative_inflation_index: float = 1


@dataclass(frozen=True)
class MarketConditions:
    annual_inflation_rate: float
    annual_stock_return: float
    annual_bond_return: float
    annual_cash_return: float
    annual_home_appreciation_rate: float


@dataclass(frozen=True)
class PersonalState:
    age: int
    marital_status: Literal["married", "single"]
    real_earnings_history: tuple[float, ...] = ()
    social_security_claiming_age: int = 67


@dataclass(frozen=True)
class FinancialState:
    taxable_brokerage_balance: float = 0.0
    taxable_brokerage_basis: float = 0.0
    taxable_brokerage_stock_allocation: float = (
        0.0  # Fraction of brokerage balance in stocks
    )
    cash_balance: float = 0.0

    # --- Tax-Advantaged Accounts ---
    traditional_retirement_balance: float = 0.0
    traditional_retirement_stock_allocation: float = (
        0.0  # Fraction of retirement balance in stocks
    )
    roth_retirement_balance: float = 0.0
    roth_contribution_basis: float = 0.0  # amount directly contributed (no conversions)
    roth_retirement_stock_allocation: float = (
        0.0  # Fraction of retirement balance in stocks
    )
    hsa_balance: float = 0.0
    hsa_stock_allocation: float = 0.0  # Fraction of HSA balance in stocks

    # --- Illiquid / Liabilities ---
    primary_residence_value: float = 0.0
    mortgage_principal: float = 0.0
    mortgage_interest_rate: float = 0.0
    mortgage_annual_payment: float = 0.0

    @property
    def total_assets(self) -> float:
        """Calculates the sum of all asset accounts."""
        return (
            self.taxable_brokerage_balance
            + self.cash_balance
            + self.traditional_retirement_balance
            + self.roth_retirement_balance
            + self.hsa_balance
            + self.primary_residence_value
        )

    @property
    def liquid_assets(self) -> float:
        """Calculates total assets excluding the primary residence."""
        return self.total_assets - self.primary_residence_value

    @property
    def total_liabilities(self) -> float:
        """Calculates total debt, including mortgage and any accrued tax."""
        return self.mortgage_principal

    @property
    def net_worth(self) -> float:
        """The total value of all assets minus all liabilities."""
        return self.total_assets - self.total_liabilities


@dataclass(frozen=True)
class YearlyDecisionsPlan:
    # --- Inflows ---
    gross_earned_income: float = 0
    social_security_recieved: float = 0
    other_taxable_income: float = 0  # e.g., Bonuses or 1099 work

    # --- Pre-Tax Payroll Deductions ---
    pretax_to_trad_401k: float = 0
    pretax_to_hsa: float = 0

    # --- Post-Tax Payroll Deductions ---
    payroll_to_roth_401k: float = 0

    # --- Employer Matches (Non-cashflow impacts) ---
    match_to_trad_401k: float = 0
    match_to_hsa: float = 0
    match_to_roth_401k: float = 0

    # --- Mandatory Outflows ---
    to_taxes: float = 0
    to_mortgage: float = 0
    to_lifestyle_spending: float = 0

    # --- Post-Tax Savings (Discretionary) ---
    to_roth_ira: float = 0
    to_brokerage: float = 0
    to_cash_reserve: float = 0

    # --- Withdrawals (Decumulation) ---
    from_traditional_retirement: float = 0
    from_hsa: float = 0
    from_taxable_brokerage_growth: float = 0
    from_taxable_brokerage_basis: float = 0
    from_roth_retirement_basis: float = 0  # Tax-free, penalty-free
    from_roth_retirement_earnings: float = 0  # Taxable + 10% penalty if < 60

    from_cash_reserve: float = 0

    @property
    def taxable_wages(self) -> float:
        """The 'fixed' portion of taxable income from payroll."""
        return (
            (
                self.gross_earned_income
                + self.other_taxable_income
                + self.match_to_roth_401k
            )
            - self.pretax_to_trad_401k
            - self.pretax_to_hsa
        )

    @property
    def from_roth_retirement(self) -> float:
        """The total amount pulled from Roth for cash flow balancing."""
        return self.from_roth_retirement_basis + self.from_roth_retirement_earnings

    @property
    def net_salary_cash_flow(self) -> float:
        """The actual 'take-home' cash from the paycheck after all deductions and taxes."""
        return (
            self.gross_earned_income
            + self.social_security_recieved
            + self.other_taxable_income
            - self.pretax_to_trad_401k
            - self.pretax_to_hsa
            - self.payroll_to_roth_401k
            - self.to_taxes
        )

    @property
    def current_cash_shortfall(self) -> float:
        """If positive, you need to withdraw. If negative, you have a surplus."""
        return (
            self.to_lifestyle_spending + self.to_mortgage
        ) - self.net_salary_cash_flow

    @property
    def total_inflows(self) -> float:
        return (
            self.gross_earned_income
            + self.social_security_recieved
            + self.other_taxable_income
            + self.from_traditional_retirement
            + self.from_roth_retirement
            + self.from_taxable_brokerage_basis
            + self.from_taxable_brokerage_growth
            + self.from_hsa
            + self.from_cash_reserve
        )

    @property
    def total_outflows(self) -> float:
        return (
            self.pretax_to_trad_401k
            + self.pretax_to_hsa
            + self.payroll_to_roth_401k
            + self.to_taxes
            + self.to_mortgage
            + self.to_lifestyle_spending
            + self.to_roth_ira
            + self.to_brokerage
            + self.to_cash_reserve
        )

    @property
    def is_balanced(self) -> bool:
        """Verifies if the plan is logically sound (within 1 dollar)."""
        return abs(self.total_inflows - self.total_outflows) < 1


class RegulatoryCalculator(Protocol):
    def __call__(
        self,
        context: "SimulationContext",
        plan: YearlyDecisionsPlan,
    ) -> float:
        """Calculates amount based on the current state and personal info."""
        ...


@dataclass(frozen=True)
class RegulatoryEnvironment:
    get_annual_401k_limit: RegulatoryCalculator
    get_annual_hsa_limit: RegulatoryCalculator
    get_annual_ira_limit: RegulatoryCalculator
    get_taxes_due: RegulatoryCalculator
    get_social_security_benefits: RegulatoryCalculator
    get_taxable_income: RegulatoryCalculator


@dataclass(frozen=True)
class SimulationContext:
    world: WorldState
    personal: PersonalState
    financial: FinancialState
    regulations: RegulatoryEnvironment


RegulationsFactory = Callable[[WorldState], RegulatoryEnvironment]


class YearlyDecisionStrategy(Protocol):
    def __call__(
        self,
        context: SimulationContext,
        existing_plan: YearlyDecisionsPlan,
    ) -> YearlyDecisionsPlan:
        """Updates the YearlyDecisionsPlan based on the current state and personal info."""
        ...


class SavingsStrategy(YearlyDecisionStrategy):
    """Updates the savings allocations in the decisions plan."""

    ...


class WithdrawalStrategy(YearlyDecisionStrategy):
    """Returns a plan for how to meet the shortfall by withdrawing from different buckets."""

    ...


class IncomeStrategy(YearlyDecisionStrategy):
    """Returns total income for the year."""

    ...


class PayrollStrategy(YearlyDecisionStrategy):
    """Allocates income into pre-tax retirement accounts and collects employer match."""

    ...


class LifestyleSpendingStrategy(YearlyDecisionStrategy):
    """Returns the desired spending amount for the year. NOT including mortgage payments or taxes, just the "lifestyle" spending."""

    ...


class MortgageStrategy(YearlyDecisionStrategy):
    """
    Manage mortgage payments
    """

    ...


class InvestmentRebalancingStrategy(Protocol):
    def __call__(self, context: SimulationContext) -> FinancialState:
        """Returns a new FinancialState with rebalanced allocations according to the strategy."""
        ...
