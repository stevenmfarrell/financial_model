from models import RegulatoryEnvironment, WorldState
from regulations.limits import (
    InflationTracking401kLimit,
    InflationTrackingHSALimit,
    InflationTrackingHouseholdRothIRALimit,
)
from regulations.social_security import InflationTrackingSocialSecurityPayout
from regulations.tax import (
    CombinedTaxCalculator,
    FlatStateIncomeTaxStrategy,
    InflationTrackingFederalTaxCalculator,
    InflationTrackingTaxableIncomeCalculator,
)


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
