from typing import (
    Annotated,
    Any,
    ClassVar,
    Dict,
    Protocol,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)
from dataclasses import fields, replace


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]]


T = TypeVar("T", bound=DataclassInstance)


def is_currency_type(annotation: Any) -> bool:
    """Helper to check if a type hint is Annotated with 'is_currency'."""
    # Unwrap the 3.12 Type Alias if present
    if type(annotation).__name__ == "TypeAliasType":
        annotation = annotation.__value__

    # Proceed with standard Annotated check
    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        return "is_currency" in args

    return False


def to_real_dollars(obj: T, cumulative_inflation_index: float) -> T:
    """
    Takes a dataclass instance and returns a new instance where all fields
    annotated with 'is_currency' are divided by the inflation index.
    """
    cls = type(obj)

    # get_type_hints with include_extras=True is required to see the Annotated metadata
    hints = get_type_hints(cls, include_extras=True)

    updates = {}
    for f in fields(obj):
        hint = hints.get(f.name)
        val = getattr(obj, f.name)

        # 1. Standard flat fields (e.g., taxable_brokerage_balance: Currency)
        if is_currency_type(hint) and isinstance(val, (int, float)):
            updates[f.name] = val / cumulative_inflation_index

        # 2. Handle nested generic types explicitly
        # (e.g., roth_conversion_recent: Tuple[Tuple[int, Currency], ...])
        # Inspecting deeply nested Annotated types dynamically requires complex recursion,
        # so catching this specific field name is safer and faster.
        elif f.name == "roth_conversion_recent" and isinstance(val, tuple):
            updates[f.name] = tuple(
                (year, amount / cumulative_inflation_index) for year, amount in val
            )

    # Return a new instance with the deflated currency values applied
    return replace(obj, **updates)
