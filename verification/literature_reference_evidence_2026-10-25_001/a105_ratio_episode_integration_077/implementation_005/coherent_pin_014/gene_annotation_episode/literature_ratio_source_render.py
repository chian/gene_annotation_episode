"""Saved-only custody selection and pure display of admitted source-signal rows.

No source/image decoder, scientific reader, calculator, model, receipt or credit
callback is used. Filtering display never changes admitted scientific values.
"""
from collections.abc import Mapping
import re

MEANINGS = ('subject', 'variant', 'reference', 'organism', 'genotype',
    'construct_variant', 'construct_reference', 'preparation_variant',
    'preparation_reference', 'experiment', 'condition', 'endpoint', 'normalization')
MARKERS = {'candidate_basis': 'selected_received_source_representations',
    'uncertainty_evaluation': 'numeric_uncertainty_reader_unimplemented'}
_PERCENT_TOKEN = re.compile(r'[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\s*%')


def is_row(row):
    return isinstance(row, Mapping) and all(row.get(k) == v for k, v in MARKERS.items())


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for rows in report.values():
                if isinstance(rows, (tuple, list)):
                    yield from (row for row in rows if is_row(row))


def _refs(value):
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key.endswith('_ref') and isinstance(child, str):
                yield child
            elif key.endswith('_refs') and isinstance(child, (tuple, list)):
                yield from (ref for ref in child if isinstance(ref, str))
            else:
                yield from _refs(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _refs(child)


def hidden_records(reports, records):
    rows = list(rows_from_reports(reports))
    sources = {row['evidence_source_ref'] for row in rows}
    return {ref for row in rows for ref in _refs(row)} | {
        ref for ref, record in records.items() if record.get('source_ref') in sources}


def _numeric_loci(payload):
    """Every nominated candidate, never just a selected scalar/primary reading."""
    loci, literals = [], set()
    for representation in payload['extraction']['representations']:
        for reading in representation['readings']:
            for role in ('numerator', 'denominator'):
                operand = reading[role]
                if operand is None:
                    continue
                literals.add(operand['literal'])
                locator = operand['locator']
                if locator is None:
                    continue
                if locator['kind'] == 'jats':
                    token = _PERCENT_TOKEN.match(locator['expression'])
                    # Saved native validation already authenticates this finite
                    # expression. Only the percent token is a numeric locus;
                    # K426A in64%(K426A) is not a hidden numerical operand.
                    if token is not None:
                        loci.append({**locator, 'numeric_start': locator['expression_start'],
                            'numeric_end': locator['expression_start'] + token.end()})
                elif locator['kind'] == 'image':
                    loci.append(locator)
    return loci, literals


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _unique_position(text, label):
    start = text.find(label)
    return start if start >= 0 and text.find(label, start + 1) < 0 else None


def _safe_definition(label, witness, loci, literals):
    locator = witness['locator']
    if locator is None or witness['authentication'] == 'unavailable':
        return False
    if locator['kind'] == 'image':
        return not any(locus['kind'] == 'image'
            and locus['original_artifact_ref'] == locator['original_artifact_ref']
            and locus['frame'] == locator['frame']
            and _overlap(locus['region'], locator['region']) for locus in loci)
    if locator['kind'] != 'text_span':
        return False
    offset = _unique_position(locator['quote'], label)
    if offset is None:
        return False
    # Generic witnesses have original UTF8 byte coordinates. JATS expressions
    # have paragraph Unicode-character coordinates. Map only an exact unique
    # retained quote into the retained paragraph; never compare unlike offsets.
    matched = False
    for locus in loci:
        if locus['kind'] != 'jats' or locus['artifact_ref'] != locator['artifact_ref']:
            continue
        position = _unique_position(locus['paragraph_text'], locator['quote'])
        if position is None:
            return False
        matched = True
        start, end = position + offset, position + offset + len(label)
        if start < locus['numeric_end'] and locus['numeric_start'] < end:
            return False
    # A broad copied text definition can duplicate the image's private printed
    # operands on another representation. With no common-coordinate disjointness
    # proof, retain it for scoped access. This is literal custody filtering, not
    # blanket digit masking: K426A/residue bounds/temperature remain intact.
    if not matched and any(re.search(r'(?<!\w)' + re.escape(token) + r'(?!\w)', label)
            for token in literals if token):
        return False
    return True


def admitted_return_meanings(context, repository):
    """Select bounded labels using saved custody for actual admitted rows only."""
    rows = repository.received_cells(context)
    sheets = []
    for reference in dict.fromkeys(row['sheet_ref'] for row in rows):
        payload = repository.read(reference)
        loci, literals = _numeric_loci(payload)
        meanings = []
        for role in MEANINGS:
            meaning = payload['extraction']['comparison'][role]
            known = meaning['status'] == 'known'
            safe = known and any(_safe_definition(meaning['value'], witness, loci, literals)
                for witness in meaning['witnesses'])
            meanings.append({'role': role, 'status': meaning['status'],
                'label': meaning['value'] if safe else None,
                'display_status': ('supplied_definition' if safe else
                    'retained_for_scoped_access' if known else 'unresolved_source_meaning')})
        sheets.append({'sheet_ref': reference, 'roles': meanings})
    return {'version': 'ratio_source_prompt_meanings_v1', 'sheets': sheets}


def _domain(region):
    lower = '−∞' if region['lower_infinite'] else str(region['lower'])
    upper = '+∞' if region['upper_infinite'] else str(region['upper'])
    return ('[' if region['lower_closed'] else '(') + lower + ', ' + upper + (']' if region['upper_closed'] else ')')


def render_received(parts, rows, meanings, *, section, table, values):
    first = rows[0]
    section(parts, 'Admitted requested source signal components', table(
        ('Component', 'Value', 'Unit', 'Status', 'Origin', 'Candidates', 'Reported-estimate domains', 'Unavailable reason'),
        ((row['component'], row['value'], row['unit'], row['status'], row['origin'],
          ', '.join(str(v) for v in row['value_candidates']) or 'none',
          '; '.join(_domain(v) for v in row['reported_domains']) or 'none', row['unavailable_reason']) for row in rows)))
    section(parts, 'Source signal comparison meaning', values({name: first[name] for name in (
        'signal_kind', 'reference_role', 'arrangement', 'signal_use', 'source_origins',
        'representation_reading_states', 'comparison_relation_states', 'signal_scale_states',
        'physical_identity_states', 'reference_identity_states', 'independent_preparation_count',
        'selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict',
        'uncertainty_kind', 'uncertainty_evaluation', 'candidate_basis')}))
    selected = next((sheet['roles'] for sheet in meanings.get('sheets', ())
        if sheet['sheet_ref'] == first['sheet_ref']), ()) if isinstance(meanings, Mapping) else ()
    by_role = {row['role']: row for row in selected}
    section(parts, 'Source signal experimental definitions', table(('Meaning', 'Status', 'Source definition'), (
        (role, first['meaning_statuses'][role], by_role.get(role, {}).get('label') or
         ('source-bound definition retained for scoped access' if first['meaning_statuses'][role] == 'known'
          else first['meaning_statuses'][role])) for role in MEANINGS)))
    section(parts, 'Source signal interpretation limits',
        'Reported signal describes this comparison, not calibrated amount or isolated activity. '
        'Domains retain reported estimates and finite outward rounding, not sampling confidence. '
        'Dependent transforms do not add independent evidence. Numeric uncertainty, calibration, '
        'functional-response and observation-model readers remain unimplemented here.')


def render_own_result(parts, content, *, section, table, values):
    cells = content.get('cells') if isinstance(content, Mapping) else None
    flags = ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict')
    if not isinstance(cells, Mapping) or 'reported_ratio' not in cells or not all(k in content for k in flags):
        return False
    section(parts, 'Selected source signal population', table(
        ('Component', 'Value', 'Unit', 'Status', 'Origin', 'Candidates', 'Reported-estimate domains', 'Unavailable reason'),
        ((name, row['value'], row['unit'], row['status'], row['origin'],
          ', '.join(str(v) for v in row['value_candidates']) or 'none',
          '; '.join(_domain(v) for v in row['reported_domains']) or 'none', row['unavailable_reason'])
         for name, row in cells.items())))
    section(parts, 'Selected source signal roster', values({key: content[key] for key in flags}))
    return True
