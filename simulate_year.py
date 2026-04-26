from dataclasses import replace
from typing import Tuple

from decisions_config import YearlyDecisionsConfiguration
from models import (
    FinancialState,
    MarketConditions,
    RegulationsFactory,
    SimulationContext,
    RegulatoryCalculator,
    PersonalState,
    WithdrawalStrategy,
    WorldState,
    YearlyDecisionsPlan,
    YearlyMetrics,
)
from strategies.income import CombinedIncome, SocialSecurityIncome


def grow_account(
    balance: float, stock_return: float, bond_return: float, stock_alloc: float
) -> float:
    growth_factor = (stock_alloc * (1 + stock_return)) + (
        (1 - stock_alloc) * (1 + bond_return)
    )
    return balance * growth_factor


def apply_market(financial: FinancialState, market: MarketConditions) -> FinancialState:
    """Applies market growth to all accounts based on their stock/bond allocations, as well as inflation."""

    def market_account_grow(balance: float, stock_alloc: float) -> float:
        return grow_account(
            balance, market.annual_stock_return, market.annual_bond_return, stock_alloc
        )

    return replace(
        financial,
        taxable_brokerage_balance=market_account_grow(
            financial.taxable_brokerage_balance,
            financial.taxable_brokerage_stock_allocation,
        ),
        traditional_retirement_balance=market_account_grow(
            financial.traditional_retirement_balance,
            financial.traditional_retirement_stock_allocation,
        ),
        roth_retirement_balance=market_account_grow(
            financial.roth_retirement_balance,
            financial.roth_retirement_stock_allocation,
        ),
        hsa_balance=market_account_grow(
            financial.hsa_balance, financial.hsa_stock_allocation
        ),
        cash_balance=financial.cash_balance * (1 + market.annual_cash_return),
        primary_residence_value=financial.primary_residence_value
        * (1 + market.annual_home_appreciation_rate),
    )


def perform_roth_maintenance(
    financial: FinancialState, world: WorldState
) -> FinancialState:
    """
    Moves aging Roth conversions from 'recent' to settled basis.
    Called at BOY before any tax or withdrawal calculations.
    """
    settled_basis = financial.roth_basis
    active_recent = []

    for conv_year, amount in financial.roth_conversion_recent:
        # A conversion is settled if it was made 5+ years ago
        if (world.year - conv_year) >= 5:
            settled_basis += amount
        else:
            active_recent.append((conv_year, amount))

    return replace(
        financial,
        roth_basis=settled_basis,
        roth_conversion_recent=tuple(active_recent),
    )


def apply_decisions_to_financial_state(
    world: WorldState, financial: FinancialState, plan: YearlyDecisionsPlan
) -> FinancialState:
    """
    Applies the transactions from the annual plan to the persistent
    financial state. Handles basis adjustments and balance updates.
    """

    # 1. Update Traditional Retirement Balance
    new_trad_balance = (
        financial.traditional_retirement_balance
        + plan.payroll_to_trad_401k
        + plan.match_to_trad_401k
        - plan.from_traditional_retirement
        - plan.trad_to_roth_conversion
    )
    # Update Roth Basis
    new_roth_basis = (
        financial.roth_basis
        + plan.payroll_to_roth_401k
        + plan.to_roth_ira
        - plan.from_roth_retirement_basis
    )

    # Update Conversion Queue (FIFO Withdrawal + New Conversion)
    queue = list(financial.roth_conversion_recent)
    to_remove = plan.from_roth_conversion_penalized
    while to_remove > 0 and queue:
        yr, amt = queue[0]
        if amt <= to_remove:
            to_remove -= amt
            queue.pop(0)
        else:
            queue[0] = (yr, amt - to_remove)
            to_remove = 0

    if plan.trad_to_roth_conversion > 0:
        queue.append((world.year, plan.trad_to_roth_conversion))

    new_roth_conversion_recent = queue

    new_roth_balance = (
        financial.roth_retirement_balance
        + plan.payroll_to_roth_401k
        + plan.match_to_roth_401k  # not basis
        + plan.to_roth_ira
        + plan.trad_to_roth_conversion
        - plan.from_roth_retirement
    )

    # 3. Update HSA Balance
    new_hsa_balance = (
        financial.hsa_balance
        + plan.payroll_to_hsa
        + plan.match_to_hsa
        - plan.from_hsa_nonmedical
    )

    # 4. Update Taxable Brokerage and Basis
    # Contributions add 1:1 to basis.
    # Withdrawals reduce basis proportionally based on the gain ratio.
    new_brokerage_balance = (
        financial.taxable_brokerage_balance
        + plan.to_brokerage
        - plan.from_taxable_brokerage_growth
        - plan.from_taxable_brokerage_basis
    )

    new_brokerage_basis = (
        financial.taxable_brokerage_basis
        + plan.to_brokerage
        - plan.from_taxable_brokerage_basis
    )

    # 5. Update Cash Reserves
    new_cash_balance = (
        financial.cash_balance + plan.to_cash_reserve - plan.from_cash_reserve
    )

    # 6. Update Mortgage Balance
    interest_charge = financial.mortgage_principal * financial.mortgage_interest_rate
    principal_reduction = max(0.0, plan.to_mortgage - interest_charge)
    new_mortgage_principal = max(
        0.0, financial.mortgage_principal - principal_reduction
    )

    return replace(
        financial,
        traditional_retirement_balance=new_trad_balance,
        roth_retirement_balance=new_roth_balance,
        roth_basis=new_roth_basis,
        roth_conversion_recent=new_roth_conversion_recent,
        hsa_balance=new_hsa_balance,
        taxable_brokerage_balance=new_brokerage_balance,
        taxable_brokerage_basis=new_brokerage_basis,
        cash_balance=new_cash_balance,
        mortgage_principal=new_mortgage_principal,
    )


def solve_withdrawal_and_tax(
    context: SimulationContext,
    initial_plan: YearlyDecisionsPlan,
    withdrawal_strat: WithdrawalStrategy,
    tax_calculator: RegulatoryCalculator,
    max_iterations: int = 30,
    tolerance: float = 1.0,
) -> YearlyDecisionsPlan:
    """
    Iteratively converges on a plan where withdrawals cover both
    spending requirements and the taxes they trigger.
    """
    current_plan = initial_plan
    last_tax_bill = initial_plan.to_taxes

    for i in range(max_iterations):
        # current_plan = conversion_strat(context, current_plan)
        current_plan = withdrawal_strat(context, current_plan)
        taxes_due = tax_calculator(context, current_plan)
        current_plan = replace(current_plan, to_taxes=taxes_due)

        # 3. Check for convergence based on the updated tax bill
        current_tax_bill = current_plan.to_taxes
        if abs(current_tax_bill - last_tax_bill) < tolerance:
            break

        last_tax_bill = current_tax_bill

    return current_plan


def get_yearly_metrics(
    context: SimulationContext, plan: YearlyDecisionsPlan
) -> YearlyMetrics:
    taxable_income = context.regulations.get_taxable_income(context, plan)
    total_tax = plan.to_taxes
    metrics = YearlyMetrics(
        taxable_income=taxable_income,
        effective_tax_rate=total_tax / taxable_income if taxable_income > 0 else 0,
    )
    return metrics


def simulate_year(
    world: WorldState,
    financial: FinancialState,
    personal: PersonalState,
    market: MarketConditions,
    regulations_factory: RegulationsFactory,
    config: YearlyDecisionsConfiguration,
) -> Tuple[
    WorldState, FinancialState, PersonalState, YearlyMetrics, YearlyDecisionsPlan
]:
    """
    Simulates a single-year state transition from Beginning of Year (BOY)
    to End of Year (EOY).

    Conceptual Model:
    This function acts as a "Time Box" representing 365 days of financial
    activity. It takes a static 'Snapshot' of wealth on January 1st (BOY)
    and returns a new 'Snapshot' of wealth on December 31st (EOY).

    The BOY/EOY Distinction:
    - Input 'financial': Represents the balances as they exist on Jan 1st.
      The caller is responsible for incrementing the 'year' and the
      'personal.age' before passing them to this function.
    - Output 'FinancialState': Represents the final settled balances after
      market growth, earned income, taxes, spending, and rebalancing have
      occurred throughout the duration of that year.

    Args:
        financial: The account balances and basis at the start of the year.
        personal: The user's demographic state (age, etc.) at the start of the year.
        market: The inflation and growth rates to apply during the simulation.
        ...[strategies]: Modular logic components following the Strategy Pattern.

    Returns:
        A new FinancialState object representing the user's wealth at the
        close of the business year.
    """

    financial = apply_market(financial, market)
    world = replace(
        world,
        cumulative_inflation_index=world.cumulative_inflation_index
        * (1 + market.annual_inflation_rate),
    )

    # Ensure our 'roth_basis' accurately reflects conversions settled for THIS year.
    financial = perform_roth_maintenance(financial, world)

    regulations = regulations_factory(world)
    context = SimulationContext(world, personal, financial, regulations)
    decisions = YearlyDecisionsPlan()
    overall_income_strat = CombinedIncome(config.income_strat, SocialSecurityIncome())
    decisions = overall_income_strat(context, decisions)
    decisions = config.payroll_strat(context, decisions)
    decisions = config.mortgage_strat(context, decisions)
    decisions = config.lifestyle_spending_strat(context, decisions)
    decisions = config.conversion_strat(context, decisions)
    decisions = solve_withdrawal_and_tax(
        context,
        decisions,
        config.withdrawal_strat,
        regulations.get_taxes_due,
    )
    decisions = config.savings_strat(context, decisions)

    financial = apply_decisions_to_financial_state(world, financial, decisions)

    # 4. Final Rebalancing
    financial = config.rebalance_strat(
        SimulationContext(world, personal, financial, regulations)
    )

    # Person will have incremented in age during the year
    personal = replace(
        personal,
        age=personal.age + 1,
        real_earnings_history=personal.real_earnings_history
        + (decisions.gross_earned_income / world.cumulative_inflation_index,),
    )

    metrics = get_yearly_metrics(
        SimulationContext(world, personal, financial, regulations), decisions
    )

    return world, financial, personal, metrics, decisions
