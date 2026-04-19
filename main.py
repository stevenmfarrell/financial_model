from decisions_config import YearlyDecisionsConfiguration
from models import (
    FinancialState,
    WorldState,
    PersonalState,
    MarketConditions,
    RegulatoryEnvironment,
)
from regulations.limits import (
    irs_401k_limit_2026,
    irs_hsa_limit_2026,
    irs_roth_ira_limit_2026_household,
)
from simulation_runner import run_simulation

from output import create_history_dataframe
from regulations.tax import (
    BrokerageCapitalGainsTax,
    CombinedTaxCalculator,
    FlatStateIncomeTaxStrategy,
    USFederalIncomeTax2026,
)
from strategies.mortgage import FixedMortgage
from strategies.payroll import MaximizeContributionsPayroll
from strategies.rebalance import GlidePathRebalance
from strategies.savings import WaterfallSavings
from strategies.spending import InflationAdjustedSpending
from strategies.wages import BaristaRetirementWages
from strategies.withdrawal import SequentialWithdrawal


def regulations_factory(world: WorldState):
    regulations = RegulatoryEnvironment(
        get_annual_401k_limit=irs_401k_limit_2026,
        get_annual_hsa_limit=irs_hsa_limit_2026,
        get_annual_ira_limit=irs_roth_ira_limit_2026_household,
        get_taxes_due=CombinedTaxCalculator(
            USFederalIncomeTax2026(),
            FlatStateIncomeTaxStrategy(0.0466),
            BrokerageCapitalGainsTax(),
        ),
    )
    return regulations


def main():
    # 1. Initialize the user's starting states
    initial_world = WorldState(year=2026)
    initial_personal = PersonalState(age=34, marital_status="married")
    initial_financial = FinancialState(
        taxable_brokerage_balance=287000.0,
        taxable_brokerage_basis=150000.0,
        taxable_brokerage_stock_allocation=0.8,
        cash_balance=20000.0,
        traditional_retirement_balance=455000.0 * 0.65,
        traditional_retirement_stock_allocation=0.9,
        roth_retirement_balance=185000.0 + 455000.0 * 0.35,
        roth_retirement_stock_allocation=1.0,
        hsa_balance=40000.0,
        hsa_stock_allocation=1.0,
        primary_residence_value=430000.0,
        mortgage_principal=155000.0,
        mortgage_interest_rate=0.03,
        mortgage_annual_payment=24000.0,
    )

    # 2. Define fixed market conditions
    market = MarketConditions(
        annual_inflation_rate=0.02,
        annual_stock_return=0.07,
        annual_bond_return=0.04,
        annual_cash_return=0.01,
        annual_home_appreciation_rate=0.02,
    )

    # 3. Instantiate the strategies
    decisions_config = YearlyDecisionsConfiguration(
        income_strat=BaristaRetirementWages(
            initial_salary=150000.0,
            barista_salary=10000,
            barista_retirement_age=40,
            full_retirement_age=50,
        ),
        payroll_strat=MaximizeContributionsPayroll(
            match_401k_cap_percent=0.04,
            match_hsa_amount=1250,
        ),
        lifestyle_spending_strat=InflationAdjustedSpending(
            base_spending_today_dollars=60000.0
        ),
        mortgage_strat=FixedMortgage(),
        savings_strat=WaterfallSavings(target_cash_reserve=20000),
        withdrawal_strat=SequentialWithdrawal(),
        rebalance_strat=GlidePathRebalance(),
    )
    history_tuples = run_simulation(
        years=60,
        initial_world=initial_world,
        initial_financial=initial_financial,
        initial_personal=initial_personal,
        market_input=market,
        regulations_factory=regulations_factory,
        config=decisions_config,
    )

    df = create_history_dataframe(history_tuples)
    df.to_csv("simulation_results.csv", float_format="%.2f")
    print("Simulation successful. Results saved to simulation_results.csv")


if __name__ == "__main__":
    main()
