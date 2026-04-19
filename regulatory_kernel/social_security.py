def calculate_social_security_payout_kernel(
    indexed_earnings_history: tuple[float, ...],
    current_age: int,
    claiming_age: int,
    b1: float,
    b2: float,
    fra: int = 67,
) -> float:
    """
    Pure mathematical logic for calculating the Social Security benefit (PIA).
    """
    # 1. Eligibility Check
    if current_age < claiming_age:
        return 0.0

    # Check for 40 credits (approx 10 years of work)
    qualifying_years = len([e for e in indexed_earnings_history if e > 0])
    if qualifying_years < 10:
        return 0.0

    # 2. Calculate AIME (Average Indexed Monthly Earnings)
    top_earnings = sorted(indexed_earnings_history, reverse=True)[:35]
    if not top_earnings:
        return 0.0

    aime = sum(top_earnings) / (35 * 12)

    pia = 0.0
    # 90% of first bracket
    pia += min(aime, b1) * 0.90
    # 32% of second bracket
    if aime > b1:
        pia += (min(aime, b2) - b1) * 0.32
    # 15% of remainder
    if aime > b2:
        pia += (aime - b2) * 0.15

    # 4. Apply Claiming Age Adjustments
    adjustment_factor = 1.0
    years_diff = claiming_age - fra

    if years_diff < 0:
        # Reduction for early claiming
        reduction_years = abs(years_diff)
        for y in range(1, reduction_years + 1):
            adjustment_factor -= 0.0667 if y <= 3 else 0.05
    elif years_diff > 0:
        # Delayed retirement credits (up to age 70)
        delayed_years = min(years_diff, 70 - fra)
        adjustment_factor += delayed_years * 0.08

    return max(0.0, pia * 12 * adjustment_factor)
