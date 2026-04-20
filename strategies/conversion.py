from dataclasses import replace
from models import RothConversionStrategy, SimulationContext, YearlyDecisionsPlan


class FillTaxBracketConversion(RothConversionStrategy):
    """
    Converts Traditional funds to Roth up to the limit of a target tax bracket.
    """

    def __init__(self, target_bracket_rate: float):
        self.target_rate = target_bracket_rate

    def __call__(
        self, context: SimulationContext, plan: YearlyDecisionsPlan
    ) -> YearlyDecisionsPlan:
        financial = context.financial
        regs = context.regulations

        # 1. What is our taxable income BEFORE the conversion?
        # This includes wages and SS, but currently 0 conversions.
        current_taxable = regs.get_taxable_income(context, plan)

        # 2. Find the dollar limit for the top of our target bracket
        # e.g., for 'married', the 12% bracket might end at $100,800 * inflation
        bracket_limit = regs.get_federal_bracket_limit(
            self.target_rate, context.personal.marital_status
        )

        # 3. Calculate headroom
        headroom = max(0.0, bracket_limit - current_taxable)

        # 4. Limit by available traditional balance
        conversion_amt = min(headroom, financial.traditional_retirement_balance)

        return replace(plan, trad_to_roth_conversion=conversion_amt)
