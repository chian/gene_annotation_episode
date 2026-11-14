"""Literal, explicitly mapped raw rate tables, separate from summary tables.

Sampling-unit and observation IDs are supplied experimental meanings, not
independence inferred from row position. The entire input is retained so a
detached record can be checked without reacquiring its source.
"""
from __future__ import annotations
GROUP_FIELDS = ('arm', 'condition', 'endpoint', 'normalization')
