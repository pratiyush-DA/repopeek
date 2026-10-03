"""Billing validation logic."""

import os


def validate_invoice(raw: bytes) -> bool:
    """Validate raw invoice payload against configured limit."""
    limit = int(os.environ.get("MAX_INVOICE_LIMIT", "10000"))
    if len(raw) == 0:
        return False
    return len(raw) <= limit
