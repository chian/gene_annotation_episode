"""Present current saved literature results without replaying historical forms.

These are read-only views of already possessed records and saved sheets. Sheet
identity, scientific ownership and distinct claims are never inferred from a
matching value, label or physical measurement. No score or credit is computed.
"""
from collections.abc import Mapping
from copy import deepcopy

from .domain import canonical


def current_scoring_view(sheets):
    """Keep every current main identity and each associated saved grade once."""
    selected = {}
    for main in sheets:
        for kind, saved in [('Main evidence scoring sheet', main),
                *(('Subscoring sheet', grade) for grade in main.get('subscoring_sheets', ()) )]:
            key = (main['axis'], kind, saved['sheet_ref'])
            if key not in selected:
                selected[key] = {**deepcopy(saved), 'axis': main['axis'],
                    'kind': kind, 'main_sheet_refs': [], 'cells': []}
                # Associated grades are represented separately, once by their
                # exact identity, with all original main-to-grade links below.
                selected[key].pop('subscoring_sheets', None)
            view = selected[key]
            if main['sheet_ref'] not in view['main_sheet_refs']:
                view['main_sheet_refs'].append(main['sheet_ref'])
            known = {canonical(cell) for cell in view['cells']}
            for cell in saved.get('cells', ()):
                if canonical(cell) not in known:
                    view['cells'].append(deepcopy(cell))
                    known.add(canonical(cell))
    return list(selected.values())


def current_findings_view(records, revision_status=()):
    """Retain exact received findings and their explicit correction links.

    A current record revision is not a scientific validity judgment. A finding
    can replace one with a different record lineage; only its supplied links
    establish that relationship for this presentation.
    """
    rows = records.values() if isinstance(records, Mapping) else records
    rows = [row for row in rows if row.get('record_type') == 'assessment'
            and isinstance(row.get('investigation_finding'), Mapping)]
    revisions = {row['record_ref']: row['is_current_revision'] for row in revision_status}
    replaced = {}
    for row in rows:
        for ref in row['investigation_finding'].get('replaces_refs', ()):
            replaced.setdefault(ref, []).append(row['id'])
    return [{**deepcopy(row), 'received_revision_status': revisions.get(row['id']),
             'replaced_by_refs': list(replaced.get(row['id'], ())) }
            for row in rows]


# These identities authenticate saved derivations but are not additional
# scientific observations. The exact referenced sheet retains them for access.
_CELL_CUSTODY = frozenset({'sheet_ref', 'measurement_keys', 'contribution_key',
    'dependency_keys', 'curve_keys', 'primitive_measurement_keys'})
_COLUMNS = ('component', 'value', 'unit', 'status')


def current_interpretation_view(report, schema, sheets):
    """Show custom interpretation fields without repeating host-bound facts."""
    if not isinstance(report, Mapping) or not isinstance(schema, Mapping):
        return report
    inventory = {'committed_record_refs', 'changed_record_refs',
                 'last_outcome_refs', 'interpretation_basis_refs'}
    cells = {canonical(cell) for sheet in current_scoring_view(sheets) for cell in sheet['cells']}
    result = {}
    for name, value in report.items():
        source = schema.get('properties', {}).get(name, {}).get('x-source')
        if source in inventory:
            continue
        if (isinstance(source, str) and source.startswith('literature_')
                and source.endswith('_cells') and isinstance(value, (list, tuple))
                and all(canonical(cell) in cells for cell in value)):
            continue
        result[name] = value
    return result


def render_current_scoring_results(sheets, *, table, display):
    parts = []
    selected = current_scoring_view(sheets)
    definitions = {}
    definition_fields = ('formula', 'meaning', 'dimension', 'conditions')
    for sheet in selected:
        for cell in sheet['cells']:
            definition = {key: cell[key] for key in definition_fields if key in cell}
            scope = (sheet['axis'], sheet['kind'], cell.get('assay_type'),
                     cell.get('quantity_kind'), cell['component'])
            item = definitions.setdefault((scope, canonical(definition)),
                                          (scope, definition, []))
            if sheet['sheet_ref'] not in item[2]:
                item[2].append(sheet['sheet_ref'])
    if definitions:
        parts.extend(['Saved component definitions', table(
            ('Evidence axis and sheet', 'Assay type', 'Quantity kind', 'Component',
             'Saved meaning, formula and conditions', 'Saved sheets using this definition'),
            [(scope[0] + ' ' + scope[1], scope[2], scope[3],
              scope[4].replace('_', ' '), display.inline(definition), '; '.join(references))
             for scope, definition, references in definitions.values()])])
    for sheet in selected:
        cells = sheet['cells']
        parts.extend(['', sheet['axis'] + ' ' + sheet['kind'],
                      'Saved sheet: ' + sheet['sheet_ref']])
        if sheet['kind'] == 'Subscoring sheet':
            parts.append('Used by main sheets: ' + '; '.join(sheet['main_sheet_refs']))
        context = {name: sheet[name] for name in
            ('assertion_ref', 'status', 'missing_inputs') if name in sheet}
        if context:
            parts.append(display.inline(context))
        if not cells:
            parts.append('No current numerical cells are supplied for this sheet.')
            continue
        separate = {*definition_fields, 'interpretations'}
        common = {key: deepcopy(value) for key, value in cells[0].items()
            if key not in _CELL_CUSTODY and key not in _COLUMNS
            and key not in separate
            and all(key in cell and cell[key] == value for cell in cells)}
        if common:
            parts.append('Shared saved context: ' + display.inline(common))
        criteria = {}
        for cell in cells:
            for name, saved in cell.get('interpretations', {}).items():
                key = (name, canonical(saved))
                if key not in criteria:
                    criteria[key] = {'name': name, 'saved': saved, 'components': []}
                criteria[key]['components'].append(cell['component'].replace('_', ' '))
        if criteria:
            parts.append(table(('Saved criterion', 'Saved criterion result', 'Components using it'),
                [(criterion['name'].replace('_', ' '), display.inline(criterion['saved']),
                  '; '.join(criterion['components'])) for criterion in criteria.values()]))
        rows = []
        for cell in cells:
            detail = {key: value for key, value in cell.items()
                if key not in _CELL_CUSTODY and key not in _COLUMNS and key not in common
                and key not in separate}
            value = cell.get('value')
            rows.append((cell['component'].replace('_', ' '),
                value if value is not None else 'Unavailable', cell.get('unit'),
                cell.get('status'), display.inline(detail)))
        parts.append(table(('Saved component', 'Saved value', 'Unit', 'Status',
                            'Saved meaning, conditions and missing inputs'), rows))
    return '\n'.join(parts) if parts else None


def render_current_findings(records, *, revision_status=(), table, display):
    rows = []
    for record in current_findings_view(records, revision_status):
        finding = record['investigation_finding']
        claim = finding['source_claim']
        source_claim = '; '.join(display.ref(ref) for ref in claim['subject_refs'])
        source_claim += ' — ' + claim['predicate'].replace('_', ' ') + ': ' + display.atom(claim['value'])
        if claim.get('context_refs'):
            source_claim += '; source contexts: ' + display.inline(claim['context_refs'])
        qualification = display.inline(finding['qualification'])
        links = {name: finding[name] for name in
                 ('status', 'withdrawal_reason', 'replaces_refs', 'same_source_claim_as_ref')
                 if name in finding}
        links.update(received_revision_status=record['received_revision_status'],
                     received_revision=record.get('revision'),
                     replaced_by_refs=record['replaced_by_refs'])
        # Correction links use actual handles beside the claim they qualify;
        # expanding each linked assessment would recursively repeat the claim.
        def link_text(value):
            if isinstance(value, (list, tuple)):
                return '; '.join(map(str, value)) or 'none supplied'
            return 'unknown' if value is None else str(value)
        relation = {name: record[name] for name in
            ('relation', 'applicability', 'condition_refs', 'assumption_refs', 'extent_basis')
            if name in record}
        rows.append((record['id'], display.ref(record['hypothesis_ref']),
            source_claim, display.ref(record['observation_ref']), display.inline(relation),
            qualification, '; '.join(name.replace('_', ' ') + ': ' + link_text(value)
                                      for name, value in links.items())))
    return table(('Saved finding', 'Target question', 'Actual source claim',
        'Source result', 'Saved relationship and applicability', 'Saved qualification',
        'Saved status and explicit correction links'), rows) if rows else None
