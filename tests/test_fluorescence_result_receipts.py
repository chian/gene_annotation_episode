"""Custody/control regression tests; no native measurement claim or producer run.

Root runs these through the bounded verification lifecycle. Full original-job
and Workflow proof is covered separately by its integration tests.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import obj
from gene_annotation_episode.fluorescence_event_contracts import canonical as numerical_canonical
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity
from gene_annotation_episode.fluorescence_result_contracts import OUTPUTS
from gene_annotation_episode.fluorescence_result_receipts import (
    FluorescenceResultReceipts, empty_facts, empty_files, failure, immutable,
    qualified_files, read_control,
)
from gene_annotation_episode.fluorescence_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, FAILURE_SOURCE,
    fluorescence_fact_sources,
)
from gene_annotation_episode.native_fluorescence_results import NativeFluorescenceResults
from gene_annotation_episode.state import Store


def retain(store, value, format_, *, scientific=False):
    raw = (numerical_canonical if scientific else canonical)(value) + b'\n'
    reference = store.artifact(raw, 'application/json')
    return dict(artifact_ref=reference, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), format=format_)


def schema(*sources):
    declarations = fluorescence_fact_sources()
    return obj({str(i): deepcopy(declarations[source]['report_schema']) for i, source in enumerate(sources)})


def receipt_fixture(store, *, mode='native_result', acquired=True, native_outcome='complete'):
    # Synthetic control-only bundle. No parser/calculator is run here.
    selection = dict(requests=[], offset=0, limit=1)
    projection = dict(schema='fluorescence_event_result_view_v1', selection=selection,
        rows=[], total_selected_rows=0, returned_row_count=0, has_more=False, status='calculated', issues=[])
    context = dict(schema='fluorescence_event_context_view_v1', selection=selection,
        context_fields=['samples'], sources=[], samples=[], channels=[], domains=[],
        populations=[], gates=[], control_pairs=[], native_reports=[])
    files = {role: retain(store, projection if role == 'projection' else context if role == 'context' else [],
        format_, scientific=role != 'diagnostics') for role, _, format_ in OUTPUTS}
    selector = dict(version='fluorescence_result_selector_v1', mode=mode, selection=selection,
        context_fields=['samples'], saved_sheet_file=None if mode == 'native_result' else files['sheet'],
        parameters=None if mode == 'native_result' else dict(fraction_requests=[], intensity_requests=[],
            control_requests=[], native_comparison_requests=[]))
    outputs = [dict(declared=dict(relative_path=path, format=format_, state='present',
        sha256=files[role]['sha256'], size_bytes=files[role]['size_bytes']), observed=files[role],
        outcome='verified', failure=None) for role, path, format_ in OUTPUTS]
    return dict(intent=dict(episode_id='result-child', operation_key='run:result-child:0',
            assignment={'selector': selector}, tool_name='execution.results.collect'),
        observation=dict(state='completed', returncode=0, native=dict(terminal=True, quiescent=True)),
        native=dict(original_plan={'identity': {'original': 'one selected population'}}),
        capture=dict(files=[dict(role='manifest', retained={'file': files['sheet']})], failures=[]),
        worker_capture=dict(result=dict(original_events_acquired=acquired if mode == 'native_result' else False,
            native_binding=mode == 'native_result', native_outcome=native_outcome if mode == 'native_result' else 'not_applicable',
            analysis_complete=True, failures=[]), outputs=outputs, failures=[]),
        worker_execution=dict(terminal=True, quiescent=True, failure=None, returncode=0),
        qualified_files=files, projection=projection, context=context, host_failures=[],
        facts=empty_facts(), original_origins=[])


def test_numerical_unicode_identity_is_distinct_from_control_json(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        reader = FluorescenceResultReceipts(SimpleNamespace(store=store))
        value = {'label': 'CD4 μ', 'value': 2}
        numerical = retain(store, value, 'fluorescence_event_result_view_v1', scientific=True)
        control = retain(store, value, 'fluorescence_worker_result_v1')
        assert numerical['sha256'] != control['sha256']
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('Historical metadata validation read scientific bytes'))
        assert reader.file_metadata(numerical, value=value, newline=True, numerical=True) == numerical
        with pytest.raises(ValueError, match='artifact_value_mismatch'):
            reader.file_metadata(numerical, value=value, newline=True)
        with pytest.raises(ValueError, match='file_metadata_mismatch'):
            reader.file_metadata({**numerical, 'size_bytes': numerical['size_bytes'] + 1})


def test_control_record_is_immutable_utf8_plus_lf(tmp_path):
    path = tmp_path / 'staged' / 'receipt.json'
    value = {'selection': 'μ', 'count': 0}
    immutable(path, value)
    assert path.read_bytes() == canonical(value) + b'\n'
    immutable(path, deepcopy(value))
    assert read_control(path) == value
    with pytest.raises(ValueError, match='control_conflict'):
        immutable(path, {**value, 'count': 1})
    malformed = tmp_path / 'duplicate.json'
    malformed.write_bytes(b'{"x":0,"x":1}\n')
    with pytest.raises(ValueError, match='duplicate_key'):
        read_control(malformed)
    wrong_codec = tmp_path / 'wrong-codec.json'
    wrong_codec.write_bytes(numerical_canonical(value) + b'\n')
    with pytest.raises(ValueError, match='noncanonical_control'):
        read_control(wrong_codec)


@pytest.mark.parametrize('missing', ['sheet', 'calculations', 'projection', 'context'])
def test_missing_captured_operand_does_not_publish_dependent_projection(tmp_path, missing):
    with Store(tmp_path / 'store') as store:
        receipt = receipt_fixture(store)
        capture = receipt['worker_capture']
        index = [row[0] for row in OUTPUTS].index(missing)
        capture['outputs'][index].update(observed=None, outcome='unavailable', failure='capture_file_unavailable')
        files = qualified_files(capture, receipt['worker_execution'])
        assert files[missing] is None
        if missing in {'sheet', 'calculations', 'projection'}:
            assert files['projection'] is None and files['context'] is None
        else:
            assert files['projection'] is not None


@pytest.mark.parametrize('patch', [dict(returncode=1), dict(terminal=False), dict(quiescent=False),
    dict(failure={'code': 'resource_failure', 'phase': 'execution', 'diagnostic': '', 'operational': True})])
def test_unsuccessful_worker_publishes_no_numerical_files(tmp_path, patch):
    with Store(tmp_path / 'store') as store:
        receipt = receipt_fixture(store)
        assert qualified_files(receipt['worker_capture'], {**receipt['worker_execution'], **patch}) == empty_files()


@pytest.mark.parametrize('acquired,native_outcome,expected', [(True, 'complete', True), (True, 'partial', True),
    (False, 'unavailable', False)])
def test_original_acquisition_uses_authenticated_extent_once(tmp_path, acquired, native_outcome, expected):
    with Store(tmp_path / 'store') as store:
        receipt = receipt_fixture(store, acquired=acquired, native_outcome=native_outcome)
        reader = FluorescenceResultReceipts(SimpleNamespace(store=store))
        result = reader.acquisition_population(receipt)
        assert bool(result) is expected
        assert reader.acquisition_population(deepcopy(receipt)) == result
        receipt['intent']['tool_name'] = 'execution.results.status'
        assert reader.acquisition_population(receipt) is None
        receipt['intent']['tool_name'] = 'execution.results.collect'
        receipt['intent']['assignment']['selector']['mode'] = 'saved_sheet_recalculation'
        assert reader.acquisition_population(receipt) is None


def test_native_endpoint_requires_whole_original_capture_not_metric_value(tmp_path):
    with Store(tmp_path / 'store') as store:
        receipt = receipt_fixture(store)
        reader = FluorescenceResultReceipts(SimpleNamespace(store=store))
        # A complete empty selected population is eligible; no positive metric gate.
        assert reader.original_acquisition_complete(receipt)
        for mutate in (lambda r: r['observation'].update(returncode=1),
                       lambda r: r['worker_capture']['result'].update(native_outcome='partial'),
                       lambda r: r['capture']['files'][0].update(retained=None)):
            changed = deepcopy(receipt)
            mutate(changed)
            assert not reader.original_acquisition_complete(changed)


def test_publication_is_requested_only_and_keeps_scientific_issues_out_of_failures(tmp_path):
    with Store(tmp_path / 'store') as store:
        receipt = receipt_fixture(store)
        requested = schema(CONTEXT_SOURCE, FAILURE_SOURCE)
        owner = SimpleNamespace(store=store, native_fluorescence_returns=SimpleNamespace(
            context=lambda _: SimpleNamespace(request={'report_contract': {'measurements': {'schema': requested}}})))
        reader = FluorescenceResultReceipts(owner)
        problem = failure('capture_file_unavailable', 'capture', role='manifest')
        receipt['host_failures'] = [problem]
        receipt['capture']['failures'] = [deepcopy(problem)]
        receipt['projection']['issues'] = [{'synthetic': 'scientific qualifications are not Failure records'}]
        facts, complete = reader.publication(receipt)
        assert facts[PROJECTION_SOURCE] == facts[SAVED_SOURCE] == []
        assert facts[CONTEXT_SOURCE] == [receipt['context']]
        assert facts[FAILURE_SOURCE] == [problem]
        assert not complete


def test_saved_assignment_can_finish_from_partial_origin_without_new_acquisition(tmp_path):
    with Store(tmp_path / 'store') as store:
        receipt = receipt_fixture(store, mode='saved_sheet_recalculation')
        requested = schema(PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)
        owner = SimpleNamespace(store=store, native_fluorescence_returns=SimpleNamespace(
            context=lambda _: SimpleNamespace(request={'report_contract': {'measurements': {'schema': requested}}})))
        reader = FluorescenceResultReceipts(owner)
        facts, complete = reader.publication(receipt, originals=[{'delivery_complete': False}])
        assert complete and facts[SAVED_SOURCE] and reader.acquisition_population(receipt) is None
        receipt['context'] = None
        assert not reader.publication(receipt, originals=[{'delivery_complete': False}])[1]


def test_credit_deduplicates_original_population_and_inherited_delivery(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        owner = SimpleNamespace(store=store, acquired_record_unit=3, handoff_unit=7,
            _selection=lambda *_: {'initial_known_record_refs': []})
        host = NativeFluorescenceResults(owner)
        receipt = receipt_fixture(store)
        population = host.receipts.acquisition_population(receipt)
        monkeypatch.setattr(host.receipts, 'completed_receipts', lambda _: [
            {'acquired_population': population}, {'acquired_population': population}, {'acquired_population': None}])
        monkeypatch.setattr(host.receipts, 'baseline_populations', lambda *_: set())
        assert host.credit_view(None, None)['new_acquired_record_count'] == 1
        assert host.credit_view(None, None)['credit'] == 3
        monkeypatch.setattr(host.receipts, 'baseline_populations', lambda *_: {population})
        assert host.credit_view(None, None)['credit'] == 0


def test_saved_contribution_origin_does_not_become_recalculation_owner(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        reader = FluorescenceResultReceipts(SimpleNamespace(store=store))
        context = SimpleNamespace(episode_id='recalculation-child')
        fact = {'synthetic': 'original contribution'}
        receipt = dict(facts={CONTEXT_SOURCE: [fact]},
            intent={'assignment': {'selector': {'mode': 'saved_sheet_recalculation'}}},
            original_origins=[{'episode_id': 'original-child', 'operation_key': 'run:original-child:0'},
                {'episode_id': 'original-child', 'operation_key': 'run:original-child:1'}])
        monkeypatch.setattr(reader, 'completed_receipts', lambda _: [receipt])
        assert reader.contribution_origins(context, CONTEXT_SOURCE, fact) == ('original-child',)
        with pytest.raises(ValueError, match='contribution_origin_missing'):
            reader.contribution_origins(context, CONTEXT_SOURCE, {'synthetic': 'unreturned'})


def test_one_selected_action_lock_reuses_original_staged_control(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        reader = FluorescenceResultReceipts(SimpleNamespace(store=store, directory=tmp_path, run_id='run'))
        context = SimpleNamespace(run_id='run', episode_id='child', assignment={}, scope={})
        intent = dict(episode_id='child', operation_key='run:child:0')
        monkeypatch.setattr(reader, 'intent', lambda *a, **k: deepcopy(intent))
        monkeypatch.setattr(reader, '_selected', lambda *_: {'result': None})
        async def selected():
            async with reader.locked_action(context, target={}, tool_name='execution.results.status',
                    arguments={}, operation_key='run:child:0') as action:
                reader.require_action(action)
                immutable(action.directory / 'retained-selection.json', {'original': True})
                return action.directory
        first = asyncio.run(selected())
        second = asyncio.run(selected())
        assert first == second and read_control(first / 'retained-selection.json') == {'original': True}
        assert not reader._active
