"""Published evidence-axis investigation instructions and their model view.

This record owns only recurring investigation TASK text. Its evidence rows are
instruction provenance; scoring sheets and the readers that populate them have
separate contracts.
"""
from __future__ import annotations

from .scientific_process_records import _exact, _option_id, _plain, _text


VERSION = 'evidence_axis_instruction_v1'
_FIELDS = 'entry_version id slot name description investigation_instructions evidence'
_SOURCE_FIELDS = 'case_group case_id source_url source_locator observation limit'


def validate_instruction_entry(value) -> dict:
    """Validate the closed instruction record and return detached finite JSON."""
    code = 'evidence_axis_instruction_invalid'
    try:
        value = _plain(value)
        _exact(value, _FIELDS, code)
        if value['entry_version'] != VERSION or value['slot'] != 'evidence_axis':
            raise ValueError(code)
        _option_id(value['id'], value['slot'], code)
        for field in ('name', 'description', 'investigation_instructions'):
            _text(value[field], code)
        if not isinstance(value['evidence'], list) or not value['evidence']:
            raise ValueError(code)
        for row in value['evidence']:
            _exact(row, _SOURCE_FIELDS, code)
            for field in row.values():
                _text(field, code)
        return value
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError(code) from error


def instruction_view(entry) -> dict:
    """Expose the published task text without provenance or host metadata."""
    entry = validate_instruction_entry(entry)
    return {'id': entry['id'], 'name': entry['name'],
        'instruction_status': 'published_investigation_instructions',
        'investigation_instructions': entry['investigation_instructions']}


__all__ = ['VERSION', 'validate_instruction_entry', 'instruction_view']
