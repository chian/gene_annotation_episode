"""Standalone mechanical worksheet demonstration; no selected episode or paper IO."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.episode_contract_information import expand_fact_form
from gene_annotation_episode.literature_a105_worksheet import (
    a105_worksheet_template, validate_a105_worksheet_links, VERSION, NATIVE, SUMMARY,
)
from gene_annotation_episode.literature_a105_worksheet_render import render_a105_worksheet


def main():
    packet = Path(__file__).resolve().parent
    original = packet.parent / 'a105_common_section_assembly_261'
    form = json.loads((packet / 'RETAINED_JOINT_NUMERICAL_ROWS_001.json').read_text())
    public = json.loads((packet / 'RETAINED_PUBLIC_REFERENCES_001.json').read_text())
    requests = [{'field': field, 'source': source, 'components': [r['component'] for r in form[field]]}
        for field, source in (('native_parameter', NATIVE), ('precision', SUMMARY))]
    template = a105_worksheet_template(requests)
    # The complete original schemas are engineering metadata, not source papers.
    originals_path = original / 'SEVEN_FAMILY_ORIGINAL_SCHEMA_FORMATS_002.json'
    formats = json.loads(originals_path.read_text())
    expanded = expand_fact_form(json.dumps(template['submitted_form']), child_role='experimental',
        permitted_child_roles=['experimental'], facts_by_role={'experimental': {
            source: {'type': 'array', 'meaning': 'Existing original numerical return format.',
                'report_schema': formats[source]} for source in (NATIVE, SUMMARY)}})
    schema = expanded['expanded_schema']
    context = {'version': VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}
    form['assessment_context'] = context

    def selector(field, component, quantity='cell_value'):
        row = next(r for r in form[field] if r['component'] == component)
        return {'field': field, 'sheet_ref': row['sheet_ref'], 'component': component, 'quantity': quantity}

    for relation, component, quantity in (
        ('same_reported_parameter', 'source_reported_parameter', 'cell_value'),
        ('same_reported_spread', 'source_reported_sd', 'reported_spread'),
        ('same_count_report', 'source_independent_preparation_count', 'reported_count'),
    ):
        context['quantity_links'].append({'left': selector('native_parameter', 'numerator_parameter', quantity),
            'right': selector('precision', component), 'relation': relation, 'support_record_refs': []})
    for report in ('source_reported_sd', 'source_independent_preparation_count'):
        context['quantity_links'].append({'left': selector('precision', report),
            'right': selector('precision', 'scenario_mean_variance'),
            'relation': 'conditional_precision_of_report', 'support_record_refs': []})

    state_path = original / 'joint_existing_boundary_001/state/state.sqlite3'
    state_before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    connection = sqlite3.connect('file:' + str(state_path) + '?mode=ro', uri=True)

    def resolver(reference, namespace):
        # Existence/type only. This standalone demonstration is not a new child
        # commission or claim that original episode possession was reexecuted.
        row = connection.execute('SELECT record_type FROM records WHERE id=?', (reference,)).fetchone()
        if row:
            return namespace is None or row[0] == namespace
        return namespace in (None, 'artifact') and connection.execute(
            'SELECT 1 FROM artifacts WHERE id=?', (reference,)).fetchone() is not None

    before = deepcopy(form)
    validate_form(form, schema, resolver)
    validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=public.get)
    connection.close()
    assert form == before
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == state_before
    parts = []

    def section(parts, title, content):
        parts.extend(['## ' + title, '', content, ''])

    def table(headers, rows):
        def cell(value):
            return str(value).replace('|', '\\|').replace('\n', ' ')
        return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |',
            '| ' + ' | '.join('---' for _ in headers) + ' |',
            *['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows]])

    render_a105_worksheet(parts, form, section=section, table=table, public_records=public)
    for name, value in (('CONSTRUCTED_TEMPLATE_001.json', template), ('CONSTRUCTED_SCHEMA_001.json', schema),
            ('CONSTRUCTED_FORM_001.json', form), ('ORIGINAL_ALIAS_DECLARATION_001.json', expanded['declaration'])):
        (packet / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    (packet / 'RENDERED_RETAINED_EXAMPLE_001.md').write_text('\n'.join(parts))
    result = {'method': 'standalone validation/rendering of original controlled261 admitted numerical rows',
        'numerical_rows': sum(len(form[field]) for field in ('native_parameter', 'precision')),
        'quantity_links': len(context['quantity_links']), 'public_reference_records': len(public),
        'original_state_sha256': state_before, 'original_state_unchanged': True,
        'new_selected_episode': False, 'new_model_call': False, 'paper_or_private_sheet_read': False,
        'scientific_calculation': False, 'observation_added': False,
        'reference_check_scope': 'original-state existence/type; original261 custody is separate historical evidence',
        'original_numerical_formats_sha256': hashlib.sha256(originals_path.read_bytes()).hexdigest()}
    (packet / 'STANDALONE_DEMONSTRATION_001.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
