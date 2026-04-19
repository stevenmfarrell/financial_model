def calculate_401k_limit_kernel(
    age: int, base_limit: float, catchup_amt: float
) -> float:
    """Pure logic: Age-based limit selection."""
    limit = base_limit
    if age >= 50:
        limit += catchup_amt
    return limit


def calculate_hsa_limit_kernel(
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


def calculate_household_roth_ira_limit_kernel(
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
