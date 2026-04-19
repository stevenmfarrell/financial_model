def calculate_taxable_income_2026_kernel(
    taxable_wages: float,
    traditional_withdrawals: float,
    ss_received: float,
    ss_base_threshold: float,
    ss_upper_threshold: float,
    ss_middle_tier_cap: float,
) -> float:
    """
    Pure mathematical logic for calculating taxable income including
    Social Security inclusion.
    """
    # 1. Base Ordinary Income
    base_taxable = taxable_wages + traditional_withdrawals

    if ss_received <= 0:
        return base_taxable

    # 2. Social Security Provisional Income Calculation
    provisional_income = base_taxable + (0.5 * ss_received)

    if provisional_income <= ss_base_threshold:
        taxable_ss = 0.0
    elif provisional_income <= ss_upper_threshold:
        taxable_ss = min(
            0.5 * ss_received, 0.5 * (provisional_income - ss_base_threshold)
        )
    else:
        # 85% Tier
        tier_2_amount = 0.85 * (provisional_income - ss_upper_threshold)
        taxable_ss = min(0.85 * ss_received, tier_2_amount + ss_middle_tier_cap)

    return base_taxable + taxable_ss


def calculate_flat_tax_kernel(
    taxable_base_ordinary: float, brokerage_growth: float, rate: float
) -> float:
    """
    Pure mathematical logic for a flat tax applied to
    ordinary income and capital gains.
    """
    return (taxable_base_ordinary + brokerage_growth) * rate


def calculate_capital_gains_tax_kernel(growth_amount: float, rate: float) -> float:
    """
    Pure mathematical logic for capital gains tax.
    Currently assumes a flat rate, but can be expanded to
    handle tiered brackets in the future.
    """
    # TODO this is overly simplistic
    return growth_amount * rate


def calculate_federal_tax_2026_kernel(
    taxable_income: float,
    wages: float,
    adj_standard_deduction: float,
    adj_brackets: list[tuple[float, float]],
    adj_ss_wage_base: float,
    adj_addl_med_threshold: float,
    fica_rates: tuple[float, float, float],  # (ss, med, addl_med)
) -> float:
    """
    Pure mathematical logic for FICA, Progressive Income Tax, and Penalties.
    """
    ss_rate, med_rate, addl_med_rate = fica_rates

    # 1. FICA Calculation
    ss_tax = min(wages, adj_ss_wage_base) * ss_rate
    med_tax = wages * med_rate
    addl_med_tax = max(0, wages - adj_addl_med_threshold) * addl_med_rate
    fica_total = ss_tax + med_tax + addl_med_tax

    # 2. Progressive Income Tax
    taxable_base = max(0.0, taxable_income - adj_standard_deduction)
    income_tax = 0.0
    prev_limit = 0.0

    for limit, rate in adj_brackets:
        taxable_in_bracket = min(taxable_base, limit) - prev_limit
        if taxable_in_bracket > 0:
            income_tax += taxable_in_bracket * rate
        prev_limit = limit
        if taxable_base <= limit:
            break

    return fica_total + income_tax


def calculate_early_withdrawal_penalty_kernel(
    traditional_withdrawals: float,
    hsa_withdrawals: float,
    age: int,
) -> float:
    """
    Pure mathematical logic for early withdrawal penalties.
    """
    # 10% penalty on Traditional distributions before age 59.5
    # (Using 60 as the integer threshold in the model)
    trad_penalty = traditional_withdrawals * 0.10 if age < 60 else 0.0

    # 20% penalty on HSA distributions for non-medical use before age 65
    hsa_penalty = hsa_withdrawals * 0.20 if age < 65 else 0.0

    return trad_penalty + hsa_penalty
