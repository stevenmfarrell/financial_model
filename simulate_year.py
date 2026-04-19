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
)


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


def apply_decisions_to_financial_state(
    financial: FinancialState, plan: YearlyDecisionsPlan
) -> FinancialState:
    """
    Applies the transactions from the annual plan to the persistent
    financial state. Handles basis adjustments and balance updates.
    """

    # 1. Update Traditional Retirement Balance
    new_trad_balance = (
        financial.traditional_retirement_balance
        + plan.pretax_to_trad_401k
        + plan.match_to_trad_401k
        - plan.from_traditional_retirement
    )

    # 2. Update Roth Retirement Balance
    new_roth_balance = (
        financial.roth_retirement_balance
        + plan.payroll_to_roth_401k
        + plan.match_to_roth_401k
        + plan.to_roth_ira
        - plan.from_roth_retirement
    )

    # 3. Update HSA Balance
    new_hsa_balance = (
        financial.hsa_balance + plan.pretax_to_hsa + plan.match_to_hsa - plan.from_hsa
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
    max_iterations: int = 15,
    tolerance: float = 1.0,
) -> YearlyDecisionsPlan:
    """
    Iteratively converges on a plan where withdrawals cover both
    spending requirements and the taxes they trigger.
    """
    current_plan = initial_plan
    last_tax_bill = initial_plan.to_taxes

    for i in range(max_iterations):
        # 1. Update withdrawals first (based on current tax estimate)
        current_plan = withdrawal_strat(context, current_plan)

        # 2. Update the tax bill (based on the new withdrawals)
        taxes_due = tax_calculator(context.world, context.personal, current_plan)
        current_plan = replace(current_plan, to_taxes=taxes_due)

        # 3. Check for convergence based on the updated tax bill
        current_tax_bill = current_plan.to_taxes
        if abs(current_tax_bill - last_tax_bill) < tolerance:
            break

        last_tax_bill = current_tax_bill

    return current_plan


def simulate_financial_year(
    world: WorldState,
    financial: FinancialState,
    personal: PersonalState,
    market: MarketConditions,
    regulations_factory: RegulationsFactory,
    config: YearlyDecisionsConfiguration,
) -> Tuple[WorldState, FinancialState, YearlyDecisionsPlan]:
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
    regulations = regulations_factory(world)
    context = SimulationContext(world, personal, financial, regulations)
    decisions = YearlyDecisionsPlan()
    decisions = config.income_strat(context, decisions)
    decisions = config.payroll_strat(context, decisions)
    decisions = config.mortgage_strat(context, decisions)
    decisions = config.lifestyle_spending_strat(context, decisions)

    decisions = solve_withdrawal_and_tax(
        context,
        decisions,
        config.withdrawal_strat,
        regulations.get_taxes_due,
    )
    decisions = config.savings_strat(context, decisions)

    financial = apply_decisions_to_financial_state(financial, decisions)

    # 4. Final Rebalancing
    financial = config.rebalance_strat(
        SimulationContext(world, personal, financial, regulations)
    )
    return world, financial, decisions
