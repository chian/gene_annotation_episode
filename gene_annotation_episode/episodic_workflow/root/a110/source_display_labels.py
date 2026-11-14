"""Display labels for anchored source literals; original values remain evidence."""
from .domain import LABEL


def source_literal_label(value):
    """Preserve valid historical labels, formatting only inadmissible previews.

    Publication retains the complete value and exact source anchor separately.
    Whitespace formatting or a truncated preview supplies no new identity.
    """
    maximum = LABEL["maxLength"]
    if len(value) <= maximum and "\n" not in value and "\r" not in value:
        return value
    preview = " ".join(value.split()) or "[source witness]"
    return preview if len(preview) <= maximum else preview[:maximum - 1] + "…"
