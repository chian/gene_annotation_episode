from __future__ import annotations
import re

def blast_record_identity(*, source_ref: str, pointer: str, record_locator: dict | None) -> tuple[str, str, str | int]:
    """Validate a closed address without changing its supplied source identity."""
    if not isinstance(source_ref, str) or not source_ref:
        raise ValueError('blast_record_source_invalid')
    if not isinstance(pointer, str) or not (pointer == '' or pointer.startswith('/')) or re.search('~(?![01])', pointer) is not None:
        raise ValueError('blast_record_pointer_invalid')
    if record_locator is None:
        return (source_ref, 'pointer', pointer)
    if not isinstance(record_locator, dict) or set(record_locator) != {'kind', 'record_ordinal'} or record_locator['kind'] != 'fasta_record' or (type(record_locator['record_ordinal']) is not int) or (record_locator['record_ordinal'] < 0):
        raise ValueError('blast_record_locator_invalid')
    if pointer != '':
        raise ValueError('record_locator_pointer_conflict')
    return (source_ref, 'fasta_record', record_locator['record_ordinal'])
