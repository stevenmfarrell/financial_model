from collections import namedtuple
from dataclasses import dataclass


LTCG_BRACKETS_MFJ_2026 = [(98900.0, 0.0), (613700.0, 0.15), (float("inf"), 0.20)]
NIIT_THRESHOLD_MFJ = 250000.0


@dataclass
class IncomeSources:
    wages: float  # W-2 Income (Subject to FICA)
    # business_income: float  # not currently dealing with self employment
    interest_and_dividends: float  # Ordinary income, BUT is NII
    short_term_gains: float  # Ordinary income, BUT is NII
    long_term_gains: float  # Special brackets, AND is NII


def calculate_fica_taxable_wages(
    income: IncomeSources,
    health_insurance_premiums: float,
    payroll_to_hsa: float,
) -> float:
    """
    Calculates wages subject to FICA (W-2 Box 3 and Box 5).
    """
    cafeteria_deductions = health_insurance_premiums + payroll_to_hsa

    # FICA strictly applies to W-2 wages, not business/investment income
    fica_wages = income.wages - cafeteria_deductions
    return max(0.0, fica_wages)


def calculate_federal_taxable_wages(
    fica_taxable_wages: float,
    payroll_to_trad_401k: float,
    match_to_roth_401k: float,
) -> float:
    """
    Calculates wages subject to Federal Income Tax.
    Matches W-2 Box 1.

    This builds upon FICA wages by subtracting traditional 401(k)
    contributions and adding taxable employer Roth matches.
    """
    federal_wages = fica_taxable_wages - payroll_to_trad_401k + match_to_roth_401k
    return max(0.0, federal_wages)


def calculate_ordinary_adjusted_gross_income(
    federal_taxable_wages: float,
    income: IncomeSources,  # Added the dataclass here
    traditional_withdrawals: float,
    roth_earnings_withdrawals: float,
    hsa_non_medical_withdrawals: float,
    trad_to_roth_conversion: float,
    age: float,
    ss_received: float,
    ss_base_threshold: float,
    ss_upper_threshold: float,
    ss_middle_tier_cap: float,
) -> float:
    """
    Calculates base ordinary income and handles Social Security inclusion.
    """
    taxable_roth = roth_earnings_withdrawals if age < 59.5 else 0.0

    # Merge W-2 wages with all other ordinary income sources
    base_taxable = (
        federal_taxable_wages
        # + income.business_income
        + income.interest_and_dividends
        + income.short_term_gains
        + traditional_withdrawals
        + taxable_roth
        + hsa_non_medical_withdrawals
        + trad_to_roth_conversion
    )

    if ss_received <= 0:
        return base_taxable

    # Social Security Provisional Income Calculation
    provisional_income = base_taxable + (0.5 * ss_received)

    if provisional_income <= ss_base_threshold:
        taxable_ss = 0.0
    elif provisional_income <= ss_upper_threshold:
        taxable_ss = min(
            0.5 * ss_received, 0.5 * (provisional_income - ss_base_threshold)
        )
    else:
        tier_2_amount = 0.85 * (provisional_income - ss_upper_threshold)
        taxable_ss = min(0.85 * ss_received, tier_2_amount + ss_middle_tier_cap)

    return base_taxable + taxable_ss


TaxableIncomeBreakdown = namedtuple(
    "TaxableIncomeBreakdown", ["ordinary_taxable", "taxable_ltcg", "total_taxable"]
)


def calculate_taxable_segments(
    ordinary_agi: float, income: IncomeSources, standard_deduction: float
) -> TaxableIncomeBreakdown:
    """
    Splits AGI into Ordinary Taxable and LTCG Taxable using the standard deduction.
    """
    ordinary_taxable = max(0.0, ordinary_agi - standard_deduction)
    unused_deduction = max(0.0, standard_deduction - ordinary_agi)

    # Pull long-term gains directly from the dataclass
    taxable_ltcg = max(0.0, income.long_term_gains - unused_deduction)

    return TaxableIncomeBreakdown(
        ordinary_taxable=ordinary_taxable,
        taxable_ltcg=taxable_ltcg,
        total_taxable=ordinary_taxable + taxable_ltcg,
    )


def calculate_state_flat_tax(total_taxable_income: float, state_rate: float) -> float:
    """
    Calculates a flat state income tax.

    Assumes the state treats ordinary income and capital gains equally,
    which is standard for most flat-tax states.

    Args:
        total_taxable_income: The combined total of ordinary income and capital gains.
        state_rate: The state's flat tax rate (e.g., 0.0455).
    """
    if total_taxable_income <= 0.0:
        return 0.0

    return total_taxable_income * state_rate


def get_net_investment_income(income: IncomeSources, taxable_ltcg: float) -> float:
    """
    Combines NII sources. We use the calculated `taxable_ltcg` from our
    segments function to ensure we don't tax gains that were absorbed
    by the standard deduction.
    """
    return income.interest_and_dividends + income.short_term_gains + taxable_ltcg


def calculate_capital_gains_tax(
    ordinary_taxable_income: float,
    taxable_ltcg: float,
    ltcg_brackets: list[tuple[float, float]],
) -> float:
    """
    Calculates Long-Term Capital Gains (LTCG) tax.

    LTCG brackets stack ON TOP of ordinary income. This function determines
    how much of the LTCG falls into the 0%, 15%, and 20% brackets based on
    where the ordinary income left off.

    Args:
        ordinary_taxable_income: Post-deduction ordinary income (the "floor").
        taxable_ltcg: The total long-term capital gains to be taxed.
        ltcg_brackets: A list of tuples [(limit, rate), ...].
                       Use float('inf') for the final bracket limit.
    """
    if taxable_ltcg <= 0.0:
        return 0.0

    total_tax = 0.0
    remaining_ltcg = taxable_ltcg

    # This acts as our "elevation tracker" as we stack gains
    current_income_level = ordinary_taxable_income

    for limit, rate in ltcg_brackets:
        # Optimization: break early if we've taxed all the gains
        if remaining_ltcg <= 0.0:
            break

        # If our ordinary income already completely filled this bracket,
        # we skip it and move to the next one.
        if current_income_level >= limit:
            continue

        # Calculate how much room is left in this specific bracket
        space_in_bracket = limit - current_income_level

        # We can only tax what fits in the bracket, or whatever gains we have left
        ltcg_in_bracket = min(remaining_ltcg, space_in_bracket)

        # Tax the chunk
        total_tax += ltcg_in_bracket * rate

        # Update our trackers for the next loop iteration
        remaining_ltcg -= ltcg_in_bracket
        current_income_level += ltcg_in_bracket

    return total_tax


def calculate_net_investment_income_tax(
    magi: float,
    net_investment_income: float,
    filing_status_threshold: float,
    rate: float = 0.038,
) -> float:
    """
    Calculates the 3.8% Net Investment Income Tax (NIIT).

    The NIIT is applied to the LESSER of:
    1. Net Investment Income (NII)
    2. The amount by which MAGI exceeds the statutory threshold.

    Args:
        magi: Modified Adjusted Gross Income (often just AGI for most taxpayers).
        net_investment_income: Total investment income (capital gains, dividends, interest, etc.).
        filing_status_threshold: The MAGI threshold based on filing status.
    """
    # 1. Calculate how much MAGI exceeds the threshold
    magi_excess = max(0.0, magi - filing_status_threshold)

    # 2. Guard clause: if MAGI is under the threshold, or there's no investment income, no tax
    if magi_excess <= 0.0 or net_investment_income <= 0.0:
        return 0.0

    # 3. The tax base is strictly the LESSER of the two amounts
    taxable_base = min(magi_excess, net_investment_income)

    # 4. Apply the flat rate
    return taxable_base * rate


def calculate_fica_tax(
    fica_taxable_wages: float,
    ss_wage_base: float,
    addl_med_threshold: float,
    fica_rates: tuple[float, float, float],
) -> float:
    """
    Calculates total FICA taxes (Social Security, Medicare, and Additional Medicare).

    Args:
        fica_taxable_wages: Wages subject to FICA (typically gross minus cafeteria plans).
        ss_wage_base: The annual cap for Social Security taxes.
        addl_med_threshold: The wage threshold where the Additional Medicare Tax kicks in.
        fica_rates: A tuple containing (ss_rate, med_rate, addl_med_rate).
    """
    ss_rate, med_rate, addl_med_rate = fica_rates

    ss_tax = min(fica_taxable_wages, ss_wage_base) * ss_rate
    med_tax = fica_taxable_wages * med_rate

    # Additional Medicare only applies to wages over the threshold
    addl_med_tax = max(0.0, fica_taxable_wages - addl_med_threshold) * addl_med_rate

    return ss_tax + med_tax + addl_med_tax


def calculate_ordinary_income_tax(
    ordinary_taxable_income: float,
    tax_brackets: list[tuple[float, float]],
) -> float:
    """
    Calculates progressive federal income tax on ordinary taxable income.

    Args:
        ordinary_taxable_income: The gross income MINUS the standard or itemized deduction.
                                 (Line 15 on Form 1040).
        tax_brackets: A list of tuples defining the progressive brackets [(limit, rate), ...].
                      Use float('inf') for the final bracket limit.
    """
    # Guard clause for zero or negative taxable income
    if ordinary_taxable_income <= 0.0:
        return 0.0

    income_tax = 0.0
    prev_limit = 0.0

    for limit, rate in tax_brackets:
        # Determine how much of the income falls specifically within this bracket's chunk
        taxable_in_bracket = min(ordinary_taxable_income, limit) - prev_limit

        if taxable_in_bracket > 0:
            income_tax += taxable_in_bracket * rate

        prev_limit = limit

        # Optimization: break early if we've consumed all taxable income
        if ordinary_taxable_income <= limit:
            break

    return income_tax


def calculate_early_withdrawal_penalty(
    traditional_withdrawals: float,
    hsa_non_medical_withdrawals: float,
    roth_earnings_withdrawals: float,
    age: float,
) -> float:
    # 10% penalty on Traditional distributions before 59.5
    trad_penalty = traditional_withdrawals * 0.10 if age < 59.5 else 0.0

    # 10% penalty on Roth earnings if withdrawn early
    roth_penalty = roth_earnings_withdrawals * 0.10 if age < 59.5 else 0.0

    # 20% penalty on HSA distributions for non-medical use before 65
    hsa_penalty = hsa_non_medical_withdrawals * 0.20 if age < 65 else 0.0

    return trad_penalty + roth_penalty + hsa_penalty


def get_tax_bracket_limit(
    target_rate: float,
    brackets: list[tuple[float, float]],
    standard_deduction: float,
) -> float:
    """
    Finds the maximum gross taxable income allowed before spilling into the next bracket.
    """
    for limit, rate in brackets:
        if rate == target_rate:
            if limit == float("inf"):
                return float("inf")
            # Return the taxable base limit PLUS the standard deduction
            return limit + standard_deduction

    raise ValueError(f"Target tax rate {target_rate} not found in brackets.")
