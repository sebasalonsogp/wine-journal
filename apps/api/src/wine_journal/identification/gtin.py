"""GTIN syntax/check digits only; a valid package code is not a wine identity."""


def canonical_gtin(value: object) -> str:
    """Keep digits as text and normalize verified GTINs to 14 characters.

    Callers must distinguish GTIN-8/EAN-8 from compressed UPC-E before calling.
    No punctuation stripping, missing-digit repair or UPC-E expansion is implied.
    """
    if not isinstance(value, str) or len(value) not in (8, 12, 13, 14):
        raise ValueError("INVALID_GTIN_LENGTH")
    if not value.isascii() or not value.isdecimal() or not value.strip("0"):
        raise ValueError("INVALID_GTIN_DIGITS")
    weighted = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(value[:-1]))
    )
    if (weighted + int(value[-1])) % 10:
        raise ValueError("INVALID_GTIN_CHECK_DIGIT")
    return value.zfill(14)
