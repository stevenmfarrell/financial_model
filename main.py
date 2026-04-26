from decisions_config import YearlyDecisionsConfiguration
from market.providers import ConstantMarketProvider
from models import (
    FinancialState,
    WorldState,
    PersonalState,
    MarketConditions,
    RegulatoryEnvironment,
)
from regulations.limits import (
    InflationTracking401kLimit,
    InflationTrackingHSALimit,
    InflationTrackingHouseholdRothIRALimit,
)
from regulations.social_security import InflationTrackingSocialSecurityPayout
from simulation_runner import run_simulation

from output import create_history_dataframe
from regulations.tax import (
    CombinedTaxCalculator,
    FlatStateIncomeTaxStrategy,
    InflationTrackingFederalTaxCalculator,
    InflationTrackingTaxableIncomeCalculator,
)
from strategies.conversion import FillTaxBracketConversion
from strategies.mortgage import FixedMortgage
from strategies.payroll import MaximizeContributionsPayroll
from strategies.rebalance import GlidePathRebalance
from strategies.savings import WaterfallSavings
from strategies.spending import InflationAdjustedSpending
from strategies.income import BaristaRetirementWages
from strategies.withdrawal import SequentialWithdrawal


federal_taxes_calc = InflationTrackingFederalTaxCalculator(
    # --- Standard Deductions ---
    std_deduction_single=16100.0,
    std_deduction_married=32200.0,
    # --- Ordinary Income Tax Brackets ---
    # Format: [(top_of_bracket, marginal_rate), ...]
    brackets_single=[
        (12400.0, 0.10),
        (50400.0, 0.12),
        (105700.0, 0.22),
        (201775.0, 0.24),
        (256225.0, 0.32),
        (640600.0, 0.35),
        (float("inf"), 0.37),
    ],
    brackets_married=[
        (24800.0, 0.10),
        (100800.0, 0.12),
        (211400.0, 0.22),
        (403550.0, 0.24),
        (512450.0, 0.32),
        (768700.0, 0.35),
        (float("inf"), 0.37),
    ],
    # --- FICA & Medicare ---
    ss_wage_base=184500.0,  # 2026 Social Security wage cap
    fica_rates=(0.062, 0.0145, 0.009),  # SS, Med, Addl Med
    med_threshold_single=200000.0,  # Statutory threshold for 0.9% Additional Medicare Tax
    med_threshold_married=250000.0,
    # --- Social Security Taxation Thresholds ---
    # The statutory thresholds where SS benefits become up to 50% or 85% taxable
    ss_base_threshold_single=25000.0,
    ss_upper_threshold_single=34000.0,
    ss_middle_tier_cap_single=4500.0,  # 50% of the difference between 34k and 25k
    ss_base_threshold_married=32000.0,
    ss_upper_threshold_married=44000.0,
    ss_middle_tier_cap_married=6000.0,  # 50% of the difference between 44k and 32k
    # --- Long-Term Capital Gains (LTCG) Brackets ---
    ltcg_brackets_single=[
        (49450.0, 0.0),
        (545500.0, 0.15),
        (float("inf"), 0.20),
    ],
    ltcg_brackets_married=[
        (98900.0, 0.0),
        (613700.0, 0.15),
        (float("inf"), 0.20),
    ],
    # --- Net Investment Income Tax (NIIT) ---
    # Statutory MAGI thresholds where the 3.8% surcharge kicks in
    niit_threshold_single=200000.0,
    niit_threshold_married=250000.0,
)


class StandardUSRegulations(RegulatoryEnvironment):
    get_annual_401k_limit = InflationTracking401kLimit(
        base_limit=23500.0, catchup_amt=7500.0
    )
    get_annual_hsa_limit = InflationTrackingHSALimit(
        single_limit=4150.0, family_limit=8300.0, catchup_amt=1000.0
    )
    get_annual_ira_limit = InflationTrackingHouseholdRothIRALimit(
        base_limit=7000.0, catchup_amt=1000.0
    )
    get_taxes_due = CombinedTaxCalculator(
        federal_taxes_calc,
        FlatStateIncomeTaxStrategy(0.0455),
    )
    get_social_security_benefits = InflationTrackingSocialSecurityPayout(
        b1=1200.0, b2=7200.0
    )
    get_taxable_income = InflationTrackingTaxableIncomeCalculator(
        ss_base_threshold=32000.0,
        ss_upper_threshold=44000.0,
        ss_middle_tier_cap=6000.0,
    )
    get_federal_bracket_limit = federal_taxes_calc.get_bracket_limit


def regulations_factory(world: WorldState):
    return StandardUSRegulations()


def main():
    # 1. Initialize the user's starting states
    initial_world = WorldState(year=2026)
    initial_personal = PersonalState(
        age=34,
        marital_status="married",
        real_earnings_history=(
            60000,
            70000,
            80000,
            90000,
            100000,
            110000,
            120000,
            13000,
            140000,
        ),
    )
    initial_financial = FinancialState(
        taxable_brokerage_balance=287000.0,
        taxable_brokerage_basis=150000.0,
        taxable_brokerage_stock_allocation=0.8,
        cash_balance=20000.0,
        traditional_retirement_balance=455000.0 * 0.65,
        traditional_retirement_stock_allocation=0.9,
        roth_retirement_balance=(185000.0 + 455000.0 * 0.35),
        roth_basis=(185000.0 + 455000.0 * 0.35) * 0.5,
        roth_retirement_stock_allocation=1.0,
        hsa_balance=40000.0,
        hsa_stock_allocation=1.0,
        primary_residence_value=430000.0,
        mortgage_principal=155000.0,
        mortgage_interest_rate=0.03,
        mortgage_annual_payment=24000.0,
    )

    market = ConstantMarketProvider(
        MarketConditions(
            annual_inflation_rate=0.02,
            annual_stock_return=0.07,
            annual_bond_return=0.04,
            annual_cash_return=0.01,
            annual_home_appreciation_rate=0.02,
        )
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
        conversion_strat=FillTaxBracketConversion(0.12),
        savings_strat=WaterfallSavings(target_cash_reserve=20000),
        withdrawal_strat=SequentialWithdrawal(),
        rebalance_strat=GlidePathRebalance(),
    )
    history_tuples = run_simulation(
        years=60,
        initial_world=initial_world,
        initial_financial=initial_financial,
        initial_personal=initial_personal,
        market_conditions_provider=market,
        regulations_factory=regulations_factory,
        config=decisions_config,
        random_seed=25,
    )

    df = create_history_dataframe(history_tuples)
    df.to_csv("simulation_results.csv", float_format="%.2f")
    print("Simulation successful. Results saved to simulation_results.csv")


if __name__ == "__main__":
    main()
