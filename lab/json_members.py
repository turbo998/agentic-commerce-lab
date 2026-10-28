"""Shared JSON member handling without input-value disclosure."""


def unique_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous JSON without echoing input values."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member; use one value per field.")
        result[key] = value
    return result
