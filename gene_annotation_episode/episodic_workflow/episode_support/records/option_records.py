"""Closed record checks for the frozen A105 library's option entries and references.

An option reference names one evidence-axis or thought-pattern entry of one
frozen library by its content digest. These checks admit finite JSON records
only; they select nothing and carry no evidence or credit.
"""
from __future__ import annotations

import json
import re

from method_loop.jsonvalue import canonical, content_digest

OPTION_REF_VERSION = 'experimental_activity_evidence_option_ref_v1'
SLOTS = ('evidence_axis', 'thought_pattern')
_PREFIXES = {'evidence_axis': 'A', 'thought_pattern': 'P'}
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def scientific_digest(value) -> str:
    """SHA-256 of the durable finite-JSON canonical representation."""
    return content_digest(value)


def _plain(value):
    try:
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError('experimental_activity_evidence_json_invalid') from error


def _exact(value, fields, code):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(code)


def _text(value, code):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)


def _sha256(value, code):
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(code)


def _option_id(value, slot, code):
    if (not isinstance(slot, str) or slot not in _PREFIXES or not isinstance(value, str)
            or re.fullmatch(_PREFIXES[slot] + r'[0-9]+', value) is None):
        raise ValueError(code)


def validate_option_ref(value) -> dict:
    value = _plain(value)
    code = 'experimental_activity_evidence_option_ref_invalid'
    _exact(value, 'version library_id slot option_id entry_sha256', code)
    if value['version'] != OPTION_REF_VERSION:
        raise ValueError(code)
    _sha256(value['library_id'], code)
    _sha256(value['entry_sha256'], code)
    _option_id(value['option_id'], value['slot'], code)
    return value


__all__ = ['OPTION_REF_VERSION', 'SLOTS', 'scientific_digest', 'validate_option_ref']
