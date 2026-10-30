"""Exact old/current field acceptance; history is read without scientific IO."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.chromatin_interaction_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, FAILURE_SOURCE, SAVED_SOURCE,
    chromatin_fact_sources, chromatin_fact_schema_alternatives, select_chromatin_return_facts,
)
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, validate_closed_schema, validate_form
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.state import Store
from tests.test_chromatin_interaction_returns import RuntimeFixture, files, references


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'verification/tool_graders_chromatin_hic_contract_2026-10-27_452/schema002'
WORKED = ROOT / 'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json'


def legacy(source):
    return json.loads((BASELINE / (source + '.actual_schema.json')).read_bytes())


def form(*trees):
    props = {'chosen_' + str(i): deepcopy(tree) for i, tree in enumerate(trees)}
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def failure():
    rows = json.loads(WORKED.read_bytes())['records']
    return deepcopy(next(row['record'] for row in rows if row['schema_definition'] == 'Failure'))


@pytest.mark.parametrize('source', FACT_SOURCES)
def test_exact_retained_schema_alternatives_and_saved_identity(source):
    current = chromatin_fact_sources()[source]['report_schema']
    old = legacy(source)
    choices = chromatin_fact_schema_alternatives(source)
    assert choices[0] == current
    assert old in choices
    assert len(choices) == (1 if source == SAVED_SOURCE else 2)
    if source == SAVED_SOURCE:
        assert canonical(old).encode() == canonical(current).encode()
    else:
        assert old['$id'] != current['$id']
    validate_closed_schema(form(old, current))
    choices[0]['$defs'].clear()
    assert chromatin_fact_schema_alternatives(source)[0]['$defs']


@pytest.mark.parametrize('source', [PROJECTION_SOURCE, FAILURE_SOURCE])
@pytest.mark.parametrize('addition', ['code', 'bytes', 'vector'])
def test_old_field_rejects_new_values_and_current_accepts(source, addition):
    problem = failure()
    if addition == 'code':
        problem['code'] = 'hic_matrix_absent'
    elif addition == 'bytes':
        problem['locator'] = {'kind': 'hic_bytes', 'value': {'offset': 0, 'size_bytes': 10, 'section': 'header'}}
    else:
        problem['locator'] = {'kind': 'hic_vector', 'value': {'normalization_type': 'VC',
            'chromosome_index': 1, 'unit': 'BP', 'resolution_bp': 10, 'bin_index': None}}
    if source == PROJECTION_SOURCE:
        rows = json.loads(WORKED.read_bytes())['records']
        projection = deepcopy(next(row['record'] for row in rows if row['schema_definition'] == 'RequestedProjection'))
        projection['failures'] = [problem]
        values = [projection]
    else:
        values = [problem]
    current = chromatin_fact_sources()[source]['report_schema']
    validate_form({'chosen_0': values}, form(current), lambda *_: True)
    with pytest.raises(ReportBoundaryError):
        validate_form({'chosen_0': values}, form(legacy(source)), lambda *_: True)
    for trees in ((current, legacy(source)), (legacy(source), current)):
        with pytest.raises(ValueError, match='field_value_incompatible'):
            select_chromatin_return_facts({source: values}, schema=form(*trees))


def test_original_hic_block_locator_was_already_supported():
    problem = failure()
    problem['locator'] = {'kind': 'hic_block', 'value': {'chromosome1_index': 1, 'chromosome2_index': 1,
        'resolution_bp': 10, 'block_id': 0, 'record_ordinal': 3}}
    validate_form({'chosen_0': [problem]}, form(legacy(FAILURE_SOURCE)), lambda *_: True)


@pytest.mark.parametrize('change', ['id', 'enum', 'type', 'additional', 'reference', 'defs'])
def test_matching_id_never_authorizes_a_changed_tree(change):
    source = SAVED_SOURCE if change == 'reference' else FAILURE_SOURCE
    node = legacy(source)
    if change == 'id': node['$id'] = chromatin_fact_sources()[source]['report_schema']['$id']
    elif change == 'enum': node['$defs']['Failure']['properties']['code']['enum'].append('hic_matrix_absent')
    elif change == 'type': node['$defs']['Failure']['properties']['input_key'] = {'type': 'string'}
    elif change == 'additional': node['$defs']['Failure']['additionalProperties'] = True
    elif change == 'reference': node['$defs']['NativeFileIdentity']['properties']['artifact_ref'].pop('format')
    else: node['$defs'].pop('Locator')
    with pytest.raises(ReportBoundaryError, match='schema must match'):
        validate_closed_schema(form(node))
    with pytest.raises(ValueError, match='unregistered_field_schema'):
        select_chromatin_return_facts({source: []}, schema=form(node))


def test_exact_legacy_forms_replay_original_prefix_and_bundle_authority(tmp_path, monkeypatch):
    store = Store(tmp_path / 'history')
    try:
        f = RuntimeFixture(store)
        schema = form(*(legacy(source) for source in FACT_SOURCES))
        science = f.child(f.root, schema, role='scientific_process')
        child = f.child(science, schema)
        _, origin = f.own(child)
        child_form = f.returned(science, child)
        parent_form = f.returned(f.root, science)
        original_schema = canonical(schema)
        before = f.snapshot()
        from gene_annotation_episode.native_file_capture import retained_native_file
        paths = {retained_native_file(store, file) for file in files(f.bundle)}
        for path in paths:
            path.unlink()
        original_read = Path.read_bytes
        def no_science(path):
            if 'artifacts' in path.parts:
                pytest.fail('historical delivery reopened scientific bytes')
            return original_read(path)
        monkeypatch.setattr(Path, 'read_bytes', no_science)
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('historical artifact read'))
        assert f.boundary.facts(f.root, schema)[SAVED_SOURCE] == [f.bundle]
        f.boundary.validate_received_report(child, child_form, schema)
        f.boundary.validate_received_report(science, parent_form, schema)
        assert f.boundary.facts_for_closure(science, schema) == json.loads(f.journal.row('runtime_forms', science.episode_id)['facts'])
        assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)
        assert f.boundary.record_admission(f.root, parent_form, schema, f.operation(f.root)) == references(f.bundle)
        assert canonical(schema) == original_schema and f.snapshot() == before
        assert f.host.calls and not any(verify for _, verify in f.host.calls[-4:])
    finally:
        store.close()


def test_legacy_cooler_form_through_actual_host_receipts_and_production_returns(tmp_path, monkeypatch):
    """Native producer/worker and manual Journal harness; no Workflow claim."""
    from tests import test_chromatin_interaction_result_receipts as receipts
    from gene_annotation_episode import native_chromatin_interaction_driver as driver
    from gene_annotation_episode.native_chromatin_interaction_preparation import freeze_chromatin_software_binding
    from gene_annotation_episode.chromatin_interaction_returns import ChromatinInteractionReturns
    from gene_annotation_episode.communication import plain
    attempt = Path(os.environ['HIC456_ATTEMPT'])
    software = freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(attempt / 'legacy_native_software'), python_executable=os.sys.executable)
    descriptors = chromatin_fact_sources()
    for source in FACT_SOURCES:
        descriptors[source]['report_schema'] = legacy(source)
    monkeypatch.setattr(receipts, 'chromatin_fact_sources', lambda: deepcopy(descriptors))
    case = receipts.Harness(tmp_path / 'legacy_actual', software)
    try:
        child = case.result_context()
        original = case.collect(child)
        schema = plain(child.request)['report_contract']['measurements']['schema']
        assert all(schema['properties'][source] == legacy(source) for source in FACT_SOURCES)
        assert original['delivery_complete']
        bundle, = original['facts'][SAVED_SOURCE]
        production = ChromatinInteractionReturns(case)
        monkeypatch.setattr(case, 'native_chromatin_interaction_returns', production)
        before = list(case.store.db.iterdump())
        before_credit, before_completion = case.host.credit_view(child, None), case.host.completion(child)
        # Existing retained control records contain custody; all scientific
        # artifacts can disappear without rewriting an old received form.
        for path in (case.store.path / 'artifacts').glob('*/*'):
            path.unlink()
        monkeypatch.setattr('gene_annotation_episode.native_file_capture.retained_native_file', receipts.deny)
        monkeypatch.setattr(type(case.job_progress_provider.targets), 'observe_target', receipts.deny)
        assert production.facts(case.root, schema) == original['facts']
        assert production.authenticate_received_saved_bundle(case.root, bundle) == ({
            'episode_id': child.episode_id, 'operation_key': original['intent']['operation_key']},)
        assert case.host.own_fact_groups(child, verify_artifacts=False) == original['facts']
        assert case.host.credit_view(child, None) == before_credit
        assert case.host.completion(child) == before_completion
        assert list(case.store.db.iterdump()) == before
    finally:
        case.store.close()
