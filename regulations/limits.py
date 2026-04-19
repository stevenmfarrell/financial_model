from models import PersonalState, WorldState, YearlyDecisionsPlan


def irs_401k_limit_2026(
    world: WorldState, personal: PersonalState, plan: YearlyDecisionsPlan
) -> float:
    inf = world.cumulative_inflation_index
    base = 23500 * inf
    catch_up = 7500 * inf if personal.age >= 50 else 0
    return base + catch_up


def irs_hsa_limit_2026(
    world: WorldState, personal: PersonalState, plan: YearlyDecisionsPlan
) -> float:
    inf = world.cumulative_inflation_index
    if personal.marital_status == "married":
        base = 8300 * inf  # Family limit
    else:
        base = 4150 * inf  # Single limit

    catch_up = 1000 * inf if personal.age >= 55 else 0
    return base + catch_up


def irs_roth_ira_limit_2026_household(
    world: WorldState, personal: PersonalState, plan: YearlyDecisionsPlan
) -> float:
    """
    Returns the TOTAL household Roth IRA
    contribution limit based on the 2026 objective law.
    """
    # TODO this does not incorporate salary-based phase outs
    inf = world.cumulative_inflation_index
    base_limit = 7000.0 * inf
    catch_up = 1000.0 * inf

    # 1. Calculate the base limit for a single individual
    per_person_limit = base_limit
    if personal.age >= 50:
        per_person_limit += catch_up

    # 2. Apply the household multiplier
    # If married, the household can fund two separate IRAs (spousal IRA logic).
    # Note: This assumes both spouses are in the same age bracket (both <50 or both >=50).
    multiplier = 2 if personal.marital_status == "married" else 1

    return per_person_limit * multiplier
