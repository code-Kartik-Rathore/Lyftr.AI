"""Helper / utility functions."""

from typing import Dict, Optional, Tuple


def parse_failure_header(header_value: Optional[str]) -> Dict[str, int]:
    """Parse the X-Simulate-Failure header into a dict of key_id -> status_code.

    Format: comma-separated `<key_id>=<status>` pairs.
    `*` as key_id means every key.
    Returns {} on None or empty.
    """
    if not header_value:
        return {}
    failures: Dict[str, int] = {}
    for part in header_value.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key_id, status_str = part.split("=", 1)
        key_id = key_id.strip()
        try:
            status = int(status_str.strip())
        except ValueError:
            continue
        failures[key_id] = status
    return failures


def should_simulate_failure(key_id: str, failures: Dict[str, int]) -> Optional[int]:
    """Return the simulated status code for a key, or None if no simulation."""
    if key_id in failures:
        return failures[key_id]
    if "*" in failures:
        return failures["*"]
    return None
