from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Optional, Protocol, Tuple

type NominalCurrency = Annotated[float, "is_nominal_currency"]


@dataclass(frozen=True)
class WorldState:
    year: int
    cumulative_inflation_index: float = 1


@dataclass(frozen=True)
class MarketConditions:
    annual_inflation_rate: float
    annual_total_stock_return: float  # includes dividend reinvestment
    annual_total_bond_return: float
    annual_cash_return: float
    annual_home_appreciation_rate: float
    annual_stock_dividend_yield: float = 0.01  # TODO use historical
    annual_bond_yield: float = 0.03  # TODO use historical


@dataclass(frozen=True)
class PersonalState:
    age: int
    marital_status: Literal["married", "single"]
    real_earnings_history: tuple[NominalCurrency, ...] = ()
    social_security_claiming_age: int = 67


@dataclass(frozen=True)
class FinancialState:
    taxable_brokerage_balance: NominalCurrency = 0.0
    taxable_brokerage_basis: NominalCurrency = 0.0
    taxable_brokerage_stock_allocation: float = (
        0.0  # Fraction of brokerage balance in stocks
    )
    cash_balance: NominalCurrency = 0.0

    # --- Tax-Advantaged Accounts ---
    traditional_retirement_balance: NominalCurrency = 0.0
    traditional_retirement_stock_allocation: float = (
        0.0  # Fraction of retirement balance in stocks
    )
    roth_retirement_balance: NominalCurrency = 0.0
    roth_basis: NominalCurrency = 0.0  # amount directly contributed or converted funds that have passed the required settling period. Might in fact be higher than the current balance. For liquidity, see roth_basis_balance

    roth_conversion_recent: Tuple[
        Tuple[int, NominalCurrency], ...
    ] = ()  # (year, amount) tuples, like ((2025, 30000), (2026, 35000))
    roth_retirement_stock_allocation: float = (
        0.0  # Fraction of retirement balance in stocks
    )
    hsa_balance: NominalCurrency = 0.0
    hsa_stock_allocation: float = 0.0  # Fraction of HSA balance in stocks

    # --- Illiquid / Liabilities ---
    primary_residence_value: NominalCurrency = 0.0
    mortgage_principal: NominalCurrency = 0.0
    mortgage_interest_rate: float = 0.0
    mortgage_annual_payment: NominalCurrency = 0.0

    @property
    def brokerage_basis_balance(self) -> NominalCurrency:
        """The portion of the account that is basis."""
        return min(self.taxable_brokerage_balance, self.taxable_brokerage_basis)

    @property
    def brokerage_growth_balance(self) -> NominalCurrency:
        """The portion of the account that is growth."""
        return self.taxable_brokerage_balance - self.brokerage_basis_balance

    @property
    def roth_basis_balance(self) -> NominalCurrency:
        """Priority 1: The portion of the account that is basis."""
        return min(self.roth_retirement_balance, self.roth_basis)

    @property
    def roth_conversion_recent_balance(self) -> NominalCurrency:
        """Priority 2: The portion of the remaining balance that is recent conversions."""
        conversion_total = sum(amount for _, amount in self.roth_conversion_recent)
        remaining = self.roth_retirement_balance - self.roth_basis_balance
        return min(remaining, conversion_total)

    @property
    def roth_growth_balance(self) -> NominalCurrency:
        """Priority 3: Whatever is left is growth."""
        # No min/max needed here; it naturally settles at 0 or higher.
        return (
            self.roth_retirement_balance
            - self.roth_basis_balance
            - self.roth_conversion_recent_balance
        )

    @property
    def liquid_assets(self) -> NominalCurrency:
        """Calculates total assets excluding the primary residence."""
        return (
            self.taxable_brokerage_balance
            + self.cash_balance
            + self.traditional_retirement_balance
            + self.roth_retirement_balance
            + self.hsa_balance
        )

    @property
    def total_assets(self) -> NominalCurrency:
        """Calculates the sum of all asset accounts."""
        return self.liquid_assets + self.primary_residence_value

    @property
    def total_liabilities(self) -> NominalCurrency:
        """Calculates total debt, including mortgage and any accrued tax."""
        return self.mortgage_principal

    @property
    def net_worth(self) -> NominalCurrency:
        """The total value of all assets minus all liabilities."""
        return self.total_assets - self.total_liabilities


@dataclass(frozen=True)
class YearlyDecisionsPlan:
    # --- Inflows ---
    gross_earned_income: NominalCurrency = 0
    social_security_received: NominalCurrency = 0
    other_taxable_income: NominalCurrency = 0  # e.g., Bonuses or 1099 work
    ordinary_dividends_received: NominalCurrency = 0
    qualified_dividends_received: NominalCurrency = 0

    # --- Pre-Tax Payroll Deductions ---
    payroll_to_trad_401k: NominalCurrency = 0
    payroll_to_hsa: NominalCurrency = 0
    payroll_to_health_premiums: NominalCurrency = 0

    # --- Post-Tax Payroll Deductions ---
    payroll_to_roth_401k: NominalCurrency = 0

    # --- Employer Matches (Non-cashflow impacts) ---
    match_to_trad_401k: NominalCurrency = 0
    match_to_hsa: NominalCurrency = 0
    match_to_roth_401k: NominalCurrency = 0

    # --- Mandatory Outflows ---
    to_taxes: NominalCurrency = 0
    to_mortgage: NominalCurrency = 0
    to_lifestyle_spending: NominalCurrency = 0

    # --- Post-Tax Savings (Discretionary) ---
    to_roth_ira: NominalCurrency = 0
    to_brokerage: NominalCurrency = 0
    to_cash_reserve: NominalCurrency = 0

    # --- Withdrawals (Decumulation) ---
    from_traditional_retirement: NominalCurrency = 0
    from_hsa_nonmedical: NominalCurrency = 0
    from_taxable_brokerage_growth: NominalCurrency = 0
    from_taxable_brokerage_basis: NominalCurrency = 0
    from_roth_retirement_basis: NominalCurrency = 0  # Tax-free, penalty-free
    from_roth_conversion_penalized: NominalCurrency = 0  # No tax, 10% penalty
    from_roth_retirement_earnings: NominalCurrency = 0  # Taxable + 10% penalty if < 60
    from_cash_reserve: NominalCurrency = 0

    # --- Conversions ---
    trad_to_roth_conversion: NominalCurrency = 0

    @property
    def to_roth(self) -> NominalCurrency:
        """The amount (no employer match) put into roth accounts"""
        return self.to_roth_ira + self.payroll_to_roth_401k

    @property
    def from_roth_retirement(self) -> NominalCurrency:
        """The total amount pulled from Roth for cash flow balancing."""
        return (
            self.from_roth_retirement_basis
            + self.from_roth_retirement_earnings
            + self.from_roth_conversion_penalized
        )

    @property
    def current_cash_shortfall(self) -> NominalCurrency:
        """If positive, you need to withdraw. If negative, you have a surplus."""
        return self.total_outflows - self.total_inflows

    @property
    def dividends_received(self) -> NominalCurrency:
        return self.ordinary_dividends_received + self.qualified_dividends_received

    @property
    def to_healthcare_spending(self) -> NominalCurrency:
        return self.payroll_to_health_premiums

    @property
    def total_inflows(self) -> NominalCurrency:
        return (
            self.gross_earned_income
            + self.social_security_received
            + self.other_taxable_income
            + self.ordinary_dividends_received
            + self.qualified_dividends_received
            + self.from_traditional_retirement
            + self.from_roth_retirement
            + self.from_taxable_brokerage_basis
            + self.from_taxable_brokerage_growth
            + self.from_hsa_nonmedical
            + self.from_cash_reserve
        )

    @property
    def total_outflows(self) -> NominalCurrency:
        return (
            self.payroll_to_trad_401k
            + self.payroll_to_hsa
            + self.payroll_to_roth_401k
            + self.payroll_to_health_premiums
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


@dataclass(frozen=True)
class YearlyMetrics:
    taxable_income: NominalCurrency
    effective_tax_rate: float


class RegulatoryCalculator(Protocol):
    def __call__(
        self,
        context: "SimulationContext",
        plan: YearlyDecisionsPlan,
    ) -> float:
        """Calculates amount based on the current state and personal info."""
        ...


class RegulatoryEnvironment(Protocol):
    """
    An interface defining all the legal and tax rules
    the simulation must respect.
    """

    get_annual_401k_limit: RegulatoryCalculator
    get_annual_hsa_limit: RegulatoryCalculator
    get_annual_ira_limit: RegulatoryCalculator
    get_taxes_due: RegulatoryCalculator
    get_social_security_benefits: RegulatoryCalculator
    get_taxable_income: RegulatoryCalculator

    # Per our previous discussion, update this to be a Protocol/Callable too
    get_federal_bracket_limit: Callable[["SimulationContext", float], float]


@dataclass(frozen=True)
class SimulationContext:
    world: WorldState
    market: MarketConditions
    personal: PersonalState
    financial: FinancialState
    regulations: RegulatoryEnvironment


class RegulationsFactory(Protocol):
    def __call__(self, world: WorldState) -> RegulatoryEnvironment:
        """Function returns a RegulatoryEnvironment given the current WorldState, to allow you to simulate changing tax laws by year"""
        ...


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


class RothConversionStrategy(YearlyDecisionStrategy):
    """Returns a plan for how much traditional retirement savings to convert into Roth"""

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


class MarketConditionsProvider(Protocol):
    """
    Interface for generating sequences of market conditions for a simulation.
    """

    def __call__(
        self, num_years: int, seed: Optional[int] = None
    ) -> list[MarketConditions]:
        """Outputs a sequence of market conditions for the specified duration."""
        ...
