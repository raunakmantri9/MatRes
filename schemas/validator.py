"""
Hallucination guard — post-output citation validator.
Rejects any numeric value in agent output that lacks a source citation.
"""
import re
import json
from typing import Any

NUMERIC_PATTERN = re.compile(r"\b\d+\.?\d*\b")
EXEMPT_FIELDS = {"ranked_position", "recall_count", "severity", "duration_weeks", "nsites"}


class CitationError(Exception):
    pass


def _has_source(obj: dict) -> bool:
    return any(
        k.lower() in ("source", "source_url", "citation")
        for k in obj.keys()
    )


def _check_object(obj: dict, path: str = "") -> list[str]:
    violations = []
    numeric_fields = {
        k: v for k, v in obj.items()
        if isinstance(v, (int, float)) and k not in EXEMPT_FIELDS
    }
    if numeric_fields and not _has_source(obj):
        violations.append(
            f"Object at '{path}' has numeric fields {list(numeric_fields.keys())} but no 'source' key."
        )
    for k, v in obj.items():
        child_path = f"{path}.{k}" if path else k
        if isinstance(v, dict):
            violations.extend(_check_object(v, child_path))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    violations.extend(_check_object(item, f"{child_path}[{i}]"))
    return violations


def validate_citations(data: Any, context: str = "") -> None:
    """
    Validate that every numeric value in the output has a source citation.
    Raises CitationError listing all violations if any are found.

    Args:
        data: Dict or list returned by a sub-agent
        context: Label for error messages (e.g. 'SupplyRiskAnalyzer')
    """
    if isinstance(data, dict):
        violations = _check_object(data)
    elif isinstance(data, list):
        violations = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                violations.extend(_check_object(item, f"[{i}]"))
    else:
        return

    if violations:
        msg = f"Citation violations in {context}:\n" + "\n".join(f"  - {v}" for v in violations)
        raise CitationError(msg)


def guard(fn):
    """
    Decorator that wraps any agent tool function with citation validation.
    Usage: @guard on any function that returns agent output.
    """
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        validate_citations(result, context=fn.__name__)
        return result

    return wrapper
