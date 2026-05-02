def calculate_401k_limit(age: int, base_limit: float, catchup_amt: float) -> float:
    """Pure logic: Age-based limit selection."""
    limit = base_limit
    if age >= 50:
        limit += catchup_amt
    return limit


def calculate_hsa_limit(
    age: int,
    is_married: bool,
    nominal_single_limit: float,
    nominal_family_limit: float,
    nominal_catchup_amt: float,
) -> float:
    """
    Pure mathematical logic for HSA limits.
    Agnostic of inflation and simulation state.
    """
    # 1. Select base limit based on filing status
    limit = nominal_family_limit if is_married else nominal_single_limit

    # 2. Add catch-up contribution if age threshold is met
    if age >= 55:
        limit += nominal_catchup_amt

    return limit


def calculate_household_roth_ira_limit(
    age: int,
    is_married: bool,
    nominal_base_limit: float,
    nominal_catchup_amt: float,
) -> float:
    """
    Pure mathematical logic for Roth IRA limits.
    Handles age-based catch-ups and household multipliers.
    """
    # TODO deal with income phase out
    per_person_limit = nominal_base_limit
    if age >= 50:
        per_person_limit += nominal_catchup_amt

    multiplier = 2 if is_married else 1

    return per_person_limit * multiplier


def calculate_uniform_lifetime_divisor(age: int) -> float:
    """
    Approximate divisors from the IRS Uniform Lifetime Table.
    Starts at age 73 per SECURE 2.0.
    """
    # Simplified table for modeling
    table = {
        73: 26.5,
        74: 25.5,
        75: 24.6,
        76: 23.7,
        77: 22.9,
        78: 22.0,
        79: 21.1,
        80: 20.2,
        85: 16.0,
        90: 12.2,
        95: 8.9,
        100: 6.4,
        110: 3.5,
        120: 2.0,
    }
    # Return linear interpolation or the closest lower age value
    if age < 73:
        return 0.0
    sorted_ages = sorted(table.keys())
    for a in sorted_ages:
        if age <= a:
            return table[a]
    return 2.0  # Catch-all for extreme longevity
