"""Decision text values from already-admitted alignment returns.

Only presentation changes. Stored identifiers, typed facts, action operands and
custody are not rewritten, and no source or scoring sheet is opened here.
"""
from collections.abc import Mapping
from copy import deepcopy
import re

from .bvbrc_alignment_bundle_contracts import decode_reference


_OPAQUE = re.compile(r"(?:artifact_|source_|[a-z_]*document_)?[0-9a-f]{24,64}(?:\b|_)")
_PREFIXES = ('bvbrc_alignment_', 'bvbrc_genome_alignment_')


def _decode(reference):
    if reference.startswith('bvbrc_genome_alignment_'):
        from .bvbrc_genome_alignment_bundle_contracts import decode_reference as genome_reference
        return genome_reference(reference)
    return decode_reference(reference)


def alignment_report_presentation(report):
    """Project exact typed alignment fields; leave other report values intact."""
    if not isinstance(report, Mapping):
        return deepcopy(report)
    publications = []

    def is_field(row):
        return (isinstance(row, Mapping) and set(row) == {'source_ref', 'field', 'value'}
            and isinstance(row['field'], str)
            and row['field'].startswith(tuple(prefix + 'field:' for prefix in _PREFIXES)))

    for values in report.values():
        if isinstance(values, list):
            for row in values:
                if is_field(row) and row['source_ref'] not in publications:
                    publications.append(row['source_ref'])
    if not publications:
        return deepcopy(report)

    aliases = {}

    def label(reference):
        kind, analysis, identity = _decode(reference)
        # Preserve readable original meanings. Hash-derived identities only
        # express association here; labels retain distinctions within a return.
        if _OPAQUE.search(identity):
            if reference not in aliases:
                number = 1 + sum(_decode(k)[0] == kind for k in aliases)
                aliases[reference] = f'{kind} {number}'
            return aliases[reference]
        return identity if analysis == '@requirements' else analysis + ' / ' + identity

    def value(item):
        if isinstance(item, Mapping):
            result = {}
            for key, child in item.items():
                if isinstance(child, str) and child.startswith(_PREFIXES):
                    result[key.removesuffix('_ref')] = label(child)
                elif key.endswith('_refs') and isinstance(child, list) and all(
                        isinstance(ref, str) and ref.startswith(_PREFIXES) for ref in child):
                    result[key.removesuffix('_refs') + 's'] = [label(ref) for ref in child]
                else:
                    result[key] = value(child)
            return result
        if isinstance(item, list):
            return [value(child) for child in item]
        return deepcopy(item)

    projected = {}
    for name, items in report.items():
        if name == 'references' and isinstance(items, list):
            remaining = [ref for ref in items if ref not in publications]
            if remaining:
                projected[name] = deepcopy(remaining)
        elif isinstance(items, list):
            rows = []
            for row in items:
                if not is_field(row):
                    rows.append(deepcopy(row))
                    continue
                _, analysis, field = _decode(row['field'])
                displayed = {'selected_field': field, 'value': value(row['value'])}
                if analysis != '@requirements':
                    displayed['analysis'] = analysis
                if len(publications) > 1:
                    displayed['result'] = 'result ' + str(publications.index(row['source_ref']) + 1)
                rows.append(displayed)
            projected[name] = rows
        else:
            projected[name] = deepcopy(items)
    return projected


__all__ = ['alignment_report_presentation']
