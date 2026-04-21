from dataclasses import replace
from models import RothConversionStrategy, SimulationContext, YearlyDecisionsPlan


class FillTaxBracketConversion(RothConversionStrategy):
    def __init__(self, target_bracket_rate: float):
        self.target_rate = target_bracket_rate

    def __call__(
        self, context: SimulationContext, plan: YearlyDecisionsPlan
    ) -> YearlyDecisionsPlan:
        financial = context.financial
        regs = context.regulations

        # 1. Calculate Tax Headroom (as before)
        current_taxable = regs.get_taxable_income(context, plan)
        bracket_limit = regs.get_federal_bracket_limit(context, self.target_rate)
        tax_headroom = max(0.0, bracket_limit - current_taxable)

        # 2. Calculate Liquidity Headroom
        # We only want to pay taxes using "Safe" buckets (No penalties, no extra income tax)
        safe_assets = (
            financial.cash_balance
            + financial.taxable_brokerage_basis
            + financial.roth_basis
        )

        # Determine how much safe liquidity is already spoken for by the lifestyle shortfall
        # (Shortfall is lifestyle + mortgage - net salary)
        lifestyle_shortfall = max(0.0, plan.current_cash_shortfall)

        # Remaining liquidity available to pay for conversion taxes
        available_tax_budget = max(0.0, safe_assets - lifestyle_shortfall)

        # Estimated conversion cap based on budget: Budget / TaxRate
        # e.g. If I have $2,400 and my rate is 24%, I can afford a $10,000 conversion.
        liquidity_cap = (
            available_tax_budget / self.target_rate if self.target_rate > 0 else 0
        )

        # 3. Final Conversion Amount is the most restrictive of the three limits
        conversion_amt = min(
            tax_headroom,
            liquidity_cap,
            financial.traditional_retirement_balance - plan.from_traditional_retirement,
        )

        return replace(plan, trad_to_roth_conversion=conversion_amt)
