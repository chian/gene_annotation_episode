"""Host-issued A104 native measurements with automatic immutable grading."""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .domain import canonical
from .a104_hpc import native_body, require
from .a104_scoring import VERSION, PROFILE, digest
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


PROVIDER = 'native.a104.measurement'
KINDS = {'a104_placement_v1': 'placement', 'a104_history_comparison_v1': 'history_comparison',
         'a104_clade_composition_v1': 'clade_composition', 'a104_robustness_v1': 'robustness'}


def install(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS a104_publications (
        source_ref TEXT PRIMARY KEY, target_ref TEXT NOT NULL, kind TEXT NOT NULL,
        body TEXT NOT NULL, grading_artifact_ref TEXT NOT NULL)''')


def native_grade(body):
    require(body['schema'] in KINDS and body['version'] == VERSION, 'a104_native_metric_schema_not_bound')
    value = body['raw_value']
    require(value is None or type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1,
            'a104_native_value_outside_unit_interval')
    return {'schema': 'a104_native_sheet_v1', 'version': VERSION, 'profile': PROFILE,
        'kind': KINDS[body['schema']], 'producer_operation': body['producer_operation'],
        'target_ref': body['target_ref'], 'raw_value': value, 'native_measurement_sha256': digest(body),
        'attribution': 'this_native_tree_test_and_original_target_region',
        'interpretation': 'native_investigation_progress; function_interpretation_is_separate'}


def publish(store, body):
    install(store)
    body = deepcopy(body)
    native = native_body(store, body['native_phylogeny_ref'])
    require(native is not None and native['target_ref'] == body['target_ref']
            and native['result_sha256'] == body['result_sha256'], 'a104_actual_native_measurement_basis_required')
    # Numerical arguments cannot be supplied through a model assessment.
    # Producer entry points calculate the body from these exact native operands.
    from .a104_scoring import placement, history_comparison
    known = {body['native_phylogeny_ref']}
    if body['schema'] == 'a104_placement_v1':
        expected = placement(store, body['native_phylogeny_ref'], body['analysis'], body['split_index'], known)
    elif body['schema'] == 'a104_history_comparison_v1':
        expected = history_comparison(store, body['native_phylogeny_ref'], body['family_analysis'],
                                      body['organismal_analysis'], body['selected_tip_ids'], known)
    else:
        from .a104_interpretation import recompute_measurement
        expected = recompute_measurement(store, body)
    require(canonical(expected) == canonical(body), 'a104_native_measurement_not_reproducible')
    grade = native_grade(body)
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        grading = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=artifact,
            grading={'grader': VERSION, 'failure': None, 'sheet': grade})
        reference = store.put('source', {'provider': PROVIDER, 'accession': digest(body), 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
            'retrieved_at': None, 'operand_refs': [body['target_ref']],
            'auxiliary_artifact_refs': [grading]}, origin='tool')['id']
        store.db.execute('INSERT OR IGNORE INTO a104_publications VALUES(?,?,?,?,?)',
            (reference, body['target_ref'], grade['kind'], canonical(body), grading))
    return reference


def received_measurement(store, reference):
    source = store.get(reference)
    if source['record_type'] != 'source' or source.get('provider') != PROVIDER:
        return None
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a104_publications'").fetchone()
    row = store.db.execute('SELECT * FROM a104_publications WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(row is not None and source['origin'] == 'tool' and source.get('version') == VERSION,
            'a104_native_scoring_grant_required')
    body = json.loads(row['body'])
    entries = source_tool_grading_entries(store, reference)
    require(json.loads(store.get_artifact(source['artifact_ref'])) == body and len(entries) == 1
            and entries[0]['artifact_ref'] == row['grading_artifact_ref']
            and entries[0]['grading'] == {'grader': VERSION, 'failure': None, 'sheet': native_grade(body)},
            'a104_native_grade_custody_conflict')
    return {'source_ref': reference, 'body': body, 'grade': entries[0]['grading']['sheet'],
            'grading_artifact_ref': row['grading_artifact_ref']}


def native_observation(store, reference):
    """Publish the tool's measured facts for later explicit scientific claims.

    This is a native observation, not a model transcription of a JSON source.
    No function hypothesis, assessment, annotation or extra credit is created.
    """
    measured = received_measurement(store, reference)
    require(measured is not None, 'a104_observation_requires_host_native_measurement')
    body, values = measured['body'], {}
    if body['schema'] == 'a104_placement_v1':
        values = {'bootstrap_split_matches': body['bootstrap_population']['matches'],
            'bootstrap_split_denominator': body['bootstrap_population']['denominator'],
            'bootstrap_split_frequency': body['raw_value']}
    elif body['schema'] == 'a104_history_comparison_v1':
        values = {'unrooted_robinson_foulds_distance': body['comparison']['rf']['value'],
                  'matched_taxon_count': len(body['taxon_join'])}
    elif body['schema'] == 'a104_clade_composition_v1':
        values = {'native_reference_member_count': len(body['characterization_subject_refs'])}
    elif body['schema'] == 'a104_robustness_v1':
        values = {'placement_membership_intersection': body['stability_numerator'],
                  'placement_membership_union': body['stability_denominator'],
                  'placement_membership_stability': body['stability_fraction']}
    subjects = sorted({part['subject_ref'] for member in body.get('clade_members', [])
                       for part in member['parts'] if part['subject_ref'] != body['target_ref']})
    record = store.put('observation', {'subject_refs': [body['target_ref']], 'source_subject_refs': subjects,
        'source_ref': reference, 'kind': 'comparison', 'anchor': None,
        'dependencies': [body['native_phylogeny_ref']],
        'operand_intervals': [{'subject_ref': body['target_ref'], 'role': 'query', 'start': start, 'end': end,
                              'unit': store.subject_unit(body['target_ref'])} for start, end in body['target_regions']],
        'measurements': [{'name': name, 'value': {'type': 'number', 'value': value, 'unit_ref': None}}
                         for name, value in values.items() if value is not None]}, origin='tool')
    return record['id']
