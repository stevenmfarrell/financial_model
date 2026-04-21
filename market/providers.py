import random
from typing import Optional, Sequence

from market.data_loader import load_market_conditions_from_csv, loaded_data_to_list
from models import MarketConditions, MarketConditionsProvider


class ConstantMarketProvider(MarketConditionsProvider):
    """
    A provider that returns the exact same market conditions for every year.
    Useful for baselining, debugging, and unit testing.
    """

    def __init__(self, conditions: MarketConditions):
        """
        Initialize with a specific set of MarketConditions.
        """
        self.conditions = conditions

    def __call__(
        self, num_years: int, seed: Optional[int] = None
    ) -> list[MarketConditions]:
        """
        Returns a list of length 'num_years' containing the fixed conditions.
        The seed is accepted for interface compatibility but is ignored.
        """
        return [self.conditions] * num_years


class RandomHistoricalMarketProvider(MarketConditionsProvider):
    """
    A provider that samples 'blocks' of consecutive historical years.
    This preserves local autocorrelation (e.g., a multi-year bear market)
    while still providing stochastic variety for Monte Carlo simulations.
    Use block_size = 1 for standard random bootstrap sampling
    """

    def __init__(
        self,
        block_size: int = 5,
        historical_data: Sequence[MarketConditions] | None = None,
    ):
        if historical_data is None:
            data_dict = load_market_conditions_from_csv()
            historical_data = loaded_data_to_list(data_dict)

        self.historical_data = list(historical_data)
        self.block_size = block_size

        if not self.historical_data:
            raise ValueError("Historical data is empty.")
        if self.block_size < 1:
            raise ValueError("Block size must be at least 1.")

    def __call__(
        self, num_years: int, seed: Optional[int] = None
    ) -> list[MarketConditions]:
        """
        Generates a sequence by picking random starting points and
        taking 'block_size' consecutive years from each.
        """
        rng = random.Random(seed)
        data_len = len(self.historical_data)
        sequence: list[MarketConditions] = []

        while len(sequence) < num_years:
            # Pick a random starting index for the next block
            start_idx = rng.randint(0, data_len - 1)

            # Determine how many years to take for this block
            # (either the full block_size or just enough to finish the sequence)
            years_needed = num_years - len(sequence)
            current_block_length = min(self.block_size, years_needed)

            for i in range(current_block_length):
                # Use modulo to wrap around if the block exceeds the data end
                # consistent with the Sequential provider logic
                idx = (start_idx + i) % data_len
                sequence.append(self.historical_data[idx])

        return sequence


class SequentialHistoricalMarketProvider(MarketConditionsProvider):
    """
    Provides market conditions in chronological order starting from a specific year.
    If it reaches the end of the history, it wraps back to the beginning.
    """

    def __init__(
        self,
        historical_data: Sequence[MarketConditions] | None = None,
        start_index: Optional[int] = None,
    ):
        if historical_data is None:
            data_dict = load_market_conditions_from_csv()
            historical_data = loaded_data_to_list(data_dict)

        self.historical_data = list(historical_data)
        self.start_index = start_index

    def __call__(
        self, num_years: int, seed: Optional[int] = None
    ) -> list[MarketConditions]:
        """
        Returns a sequence of years in order.
        If self.start_index is set, it always starts there.
        Otherwise, it picks a random start index based on the seed.
        """
        data_len = len(self.historical_data)
        if data_len == 0:
            raise ValueError("Historical data is empty.")

        # Determine where to start
        if self.start_index is not None:
            actual_start = self.start_index % data_len
        else:
            rng = random.Random(seed)
            actual_start = rng.randint(0, data_len - 1)

        # Generate the sequence by 'cycling' using modulo
        sequence = []
        for i in range(num_years):
            idx = (actual_start + i) % data_len
            sequence.append(self.historical_data[idx])

        return sequence
