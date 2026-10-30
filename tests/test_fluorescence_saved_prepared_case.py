"""Read original closed check049 records; never construct another Workflow.

The coordinator stages both closed cases after check049 is terminal. These are
synthetic supplied measurements with actual historical native execution. The
full numerical payloads were intentionally withdrawn by the replay test. The
separate calculator test reports that missing proof as a skip, not a pass.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

import pytest

from method_loop.archive import ArchivedRecord
from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.fluorescence_context_views import project_fluorescence_context
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_execution_common import digest as control_digest
from gene_annotation_episode.fluorescence_result_contracts import (
    validate_fluorescence_context, validate_fluorescence_projection,
    validate_fluorescence_selector, validate_fluorescence_worker_plan,
    validate_fluorescence_worker_result,
)
from gene_annotation_episode.fluorescence_result_receipts import (
    FluorescenceResultReceipts, qualified_files,
)
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from gene_annotation_episode.fluorescence_return_views import (
    CONTEXT_SOURCE, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    requested_fluorescence_sources, select_fluorescence_return_facts,
    validate_fluorescence_fact_values,
)


CASES = (
    ('perform_facs_cell_sorting', 'HMMER_NATIVE_ORACLE_FLUORESCENCE_FACS_SAVED_CASE'),
    ('analyze_cytokine_production_in_cd4_tcells',
     'HMMER_NATIVE_ORACLE_FLUORESCENCE_CYTOKINE_SAVED_CASE'),
)
FIELDS = {'measurements': PROJECTION_SOURCE, 'contexts': CONTEXT_SOURCE,
          'saved': SAVED_SOURCE, 'failures': FAILURE_SOURCE}
CONTEXT_FIELDS = ['samples', 'channels', 'domains', 'populations', 'gates']
# Explicit answers to the original declared requests, not another calculator.
EXPECTED_ROWS = (
    ('population', 'retained_event_count', None, None, 2, 'events', 'none'),
    ('population', 'selected_event_count', None, None, 2, 'events', 'none'),
    ('fraction', 'selected_fraction', None, None, 1, 'dimensionless', 'parent'),
    ('fraction', 'selected_percent', None, None, 100, 'percent', 'parent'),
    ('intensity', 'selected_intensity_mean', 'domain-0', 'raw.c0', 130,
     'instrument_units', 'selected_finite'),
    ('intensity', 'selected_intensity_mean', 'scaled', 'scaled.c0', 65,
     'instrument_units', 'selected_finite'),
    ('intensity', 'selected_intensity_mean', 'compensated', 'compensated.c0', 50,
     'instrument_units', 'selected_finite'),
    ('intensity', 'selected_intensity_mean', 'scaled', 'scaled.c2', 1.5,
     'seconds', 'selected_finite'),
    ('native_comparison', 'native_value', None, None, 100, 'percent', 'none'),
    ('native_comparison', 'native_minus_calculated', None, None, 0, 'percent', 'none'),
)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def walk(record):
    yield record
    for unit in record['units']:
        if unit.get('child') is not None:
            yield from walk(unit['child'])


def write_evidence(case, label, value):
    path = case.attempt / 'temporary' / f'SAVED_PREPARED_608_{case.operation}_{label}.json'
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def artifact_path(case, file):
    return case.directory / 'state/artifacts' / file['sha256'][:2] / file['sha256']


def assert_file_metadata(case, file, *, value=None):
    row = case.db.execute('SELECT * FROM artifacts WHERE id=?', (file['artifact_ref'],)).fetchone()
    assert row is not None
    assert row['id'] == 'artifact_' + row['sha256'] == file['artifact_ref']
    assert row['sha256'] == file['sha256'] and row['size'] == file['size_bytes']
    if value is not None:
        raw = core.canonical(value) + b'\n'
        assert hashlib.sha256(raw).hexdigest() == file['sha256']
        assert len(raw) == file['size_bytes']


def assert_equal(actual, expected):
    # This production comparator preserves numerical types and exact facts.
    assert EpisodeReturnRecords._equal(actual, expected)


@pytest.fixture(params=CASES, ids=['facs-prepared', 'cytokine-prepared'])
def closed_prepared_case(request, monkeypatch):
    operation, environment = request.param
    selected = os.environ.get(environment)
    if selected is None:
        pytest.skip('stage the closed original case and set ' + environment)
    attempt = require_bounded_runtime()
    directory = Path(selected).resolve(strict=True)
    assert directory.is_relative_to(attempt / 'source_snapshot')
    saved = read_json(directory / 'CASE.json')
    assert saved['operation'] == operation
    database = directory / 'state/state.sqlite3'
    wal = database.with_name(database.name + '-wal')
    assert not wal.exists() or wal.stat().st_size == 0, 'stage a closed, checkpointed case'
    watched = [database, directory / 'CASE.json', directory / 'fixture-configuration.json',
        directory / 'WITHDRAWAL_AND_REPLAY_INPUTS.json', directory / 'original-native-plan.json',
        *sorted(directory.glob('CLOSED_REPLAY.json')), *sorted(directory.glob('decision-*.json')),
        *sorted((directory / 'run/archive').glob('*.json'))]
    before = {str(p.relative_to(directory)): sha256(p) for p in watched}

    def deny(*args, **kwargs):
        raise AssertionError('saved postconditions must not start work or use the network')

    monkeypatch.setattr('subprocess.Popen', deny)
    monkeypatch.setattr('os.system', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        run_id = saved['archive']['run_id']
        # The shared return-record reader needs only this read-only connection.
        # No Store constructor, Workflow, execution owner, or fake result is made.
        reader = EpisodeReturnRecords(SimpleNamespace(db=db), run_id, failure_prefix='saved_fluorescence_')
        records = list(walk(saved['archive']))
        assert len(records) == 7
        for record in records:
            row = db.execute('SELECT path,request,state,archive FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (run_id, record['episode_id'])).fetchone()
            assert row is not None and row['state'] == 'yielded'
            assert_equal(json.loads(row['request']), record['request'])
            assert_equal(json.loads(row['path']), record['path'])
            descriptor = json.loads(row['archive'])
            assert Path(descriptor['file']).name == descriptor['file']
            archived = ArchivedRecord(directory / 'run/archive' / descriptor['file'],
                descriptor['sha256'], descriptor['index_sha256'])
            assert_equal(archived.load(), record)
        case = SimpleNamespace(attempt=attempt, directory=directory, operation=operation,
            saved=saved, db=db, run_id=run_id, reader=reader, records=records,
            configuration=read_json(directory / 'fixture-configuration.json'),
            withdrawal=read_json(directory / 'WITHDRAWAL_AND_REPLAY_INPUTS.json'),
            plan=read_json(directory / 'original-native-plan.json'))
        try:
            yield case
        finally:
            assert {str(p.relative_to(directory)): sha256(p) for p in watched} == before
            write_evidence(case, 'immutability', dict(database_and_captured_records_unchanged=True,
                original_case=str(directory), input_sha256=before, new_workflow_runs=0,
                new_native_jobs=0, new_actions=0, new_observations=0))


def original_receipts(case):
    rows = list(case.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
        "AND json_extract(result,'$.result.version')='native_fluorescence_acquired_result_v1' ORDER BY rowid",
        (case.run_id,)))
    assert len(rows) == 3
    receipts = [json.loads(row['result'])['result'] for row in rows]
    assert_equal(receipts[0], case.withdrawal['original_receipt'])
    assert_equal(receipts[1], case.withdrawal['partial_receipt'])
    for row, receipt in zip(rows, receipts):
        FluorescenceResultReceipts.match_outcome(row, receipt)
        assert receipt['intent']['episode_id'] == row['episode_id']
        assert receipt['intent']['tool_name'] == json.loads(row['action'])['tool'] == 'execution.results.collect'
        worker = validate_fluorescence_worker_result(receipt['worker_capture']['result'])
        plan = validate_fluorescence_worker_plan(receipt['worker_plan'])
        assert worker['plan_sha256'] == control_digest(plan)
        assert worker['selector'] == plan['selector'] == receipt['intent']['assignment']['selector']
        assert_equal(receipt['qualified_files'], qualified_files(receipt['worker_capture'], receipt['worker_execution']))
        for role, file in receipt['qualified_files'].items():
            if file is not None:
                assert_file_metadata(case, file, value=receipt.get(role) if role in ('projection', 'context') else None)
        for source, values in receipt['facts'].items():
            assert_equal(validate_fluorescence_fact_values(source, values), values)
        assert_equal(receipt['facts'][PROJECTION_SOURCE], [receipt['projection']])
        assert_equal(receipt['facts'][CONTEXT_SOURCE], [receipt['context']])
    return receipts


def assert_original_rows(receipt):
    view = validate_fluorescence_projection(receipt['projection'])
    assert (view['total_selected_rows'], view['returned_row_count'], view['has_more']) == (10, 10, False)
    assert view['status'] == 'calculated' and view['issues'] == []
    assert (view['selection']['offset'], view['selection']['limit']) == (0, 10)
    for row, expected in zip(view['rows'], EXPECTED_ROWS):
        kind, metric, domain, channel, value, unit, denominator = expected
        native = kind == 'native_comparison'
        request = dict(kind=kind, metric=metric, gate_key=None if native else 'gate-0',
            domain_key=domain, channel_key=channel, control_key=None,
            native_report_key='native.report.percent' if native else None,
            denominator='parent' if kind == 'fraction' else 'none')
        assert_equal(row['request'], request)
        assert row['value'] == pytest.approx(value, rel=0, abs=1e-12)
        assert row['state'] == 'present' and row['issues'] == [] and row['unit'] == unit
        assert_equal(row['population'], dict(sample_key=None if native else 'sample-0',
            gate_key=None if native else 'gate-0', domain_key=domain, channel_key=channel,
            denominator=denominator, extent='complete'))
        assert row['operands']


def assert_original_associations(case, receipt):
    job = case.plan['requested_job']['native_fluorescence']
    assert job['operation'] == case.operation and job['version'] == 'native_fluorescence_job_v2'
    assert_equal(receipt['native']['original_plan'], case.plan)
    validate_fluorescence_selector(receipt['intent']['assignment']['selector'], job=job)
    declared = read_json(case.directory / 'decision-1.json')['context']['scientific_process']['assignment']
    assert declared['context']['supplied_sequence'] == 'ACGTACGT'
    assert declared['evidence_refs'] == case.configuration['scope']['subject_refs']
    supplied = declared['context']['supplied_fluorescence_files']
    selected = [r['source']['file'] for r in job['inputs']] + [
        r['file'] for r in (*job['support_inputs'], *job['report_inputs'])]
    assert_equal(supplied, list({r['artifact_ref']: r for r in selected}.values()))
    captures = {r['role']: r for r in receipt['capture']['files']}
    for prefix, files in (('event_input', [r['source']['file'] for r in job['inputs']]),
            ('support_input', [r['file'] for r in job['support_inputs']]),
            ('report_input', [r['file'] for r in job['report_inputs']])):
        for i, file in enumerate(files):
            assert_equal(captures[f'{prefix}:{i}']['retained']['file'], file)
            assert_file_metadata(case, file)
    event, = job['inputs']
    assert_equal(receipt['worker_capture']['result']['input_identities'], [event['source']['file']])
    context = validate_fluorescence_context(receipt['context'])
    assert context['context_fields'] == CONTEXT_FIELDS
    assert context['selection'] == receipt['projection']['selection']
    assert context['sources'] == context['control_pairs'] == context['native_reports'] == []
    assert_equal(context['samples'], [event['sample']])
    assert_equal(context['gates'], job['definitions']['gates'])
    assert_equal(context['populations'], [{k: v for k, v in row.items() if k != 'event_ordinals'}
        for row in job['definitions']['populations']])
    domains = {row['key']: row for row in context['domains']}
    assert set(domains) == {'domain-0', 'scaled', 'compensated'}
    assert_equal(domains['domain-0'], {k: v for k, v in event['domain'].items() if k != 'correspondence'})
    channels = [{**{k: v for k, v in row.items() if k != 'measurement_origin'}, 'domain_key': 'domain-0'}
        for row in event['channels']]
    for index, preparation in enumerate(job['preparations']):
        output, recipe = preparation['output'], preparation['recipe']
        domain = domains[output['key']]
        assert domain['sample_key'] == output['sample_key'] == event['sample']['key']
        assert domain['source_key'] == output['source_key']
        assert domain['comparison_basis'] == output['comparison_basis']
        assert domain['state'] == 'available' and domain['scale_kind'] == 'scaled'
        assert domain['parent_domain_key'] == ('domain-0' if index == 0 else 'scaled')
        kind = 'scaling' if index == 0 else 'compensation'
        assert_equal(domain[kind], dict(state='applied', method=recipe['method'],
            parameters_file=captures[f'preparation_parameters:{index}']['retained']['file']))
        channels.extend({**row, 'domain_key': output['key']} for row in output['channels'])
    selected_channels = {'raw.c0', 'scaled.c0', 'scaled.c2', 'compensated.c0'}
    assert_equal(context['channels'], [row for row in channels if row['key'] in selected_channels])
    report, = job['report_inputs']
    field, = report['fields']
    assert report['profile'] == 'biomni_facs_log_548_v1' and report['source_key'] == 'native.report'
    assert field['key'] == 'native.report.percent'
    assert_equal(field['component_request'], receipt['projection']['rows'][3]['request'])
    assert report['association_file'] in [row['file'] for row in job['support_inputs']]
    assert_file_metadata(case, report['association_file'])
    return job


def test_saved_prepared_complete_return_and_both_parents(closed_prepared_case):
    case = closed_prepared_case
    receipts = original_receipts(case)
    original = receipts[0]
    assert original['delivery_complete'] and original['facts'][FAILURE_SOURCE] == []
    assert_original_rows(original)
    assert_original_associations(case, original)
    reader = case.reader
    root = reader.context(case.saved['archive']['episode_id'])
    science_record, = [row for row in case.records if row['scope_level'] == 'scientific_process']
    science = reader.context(science_record['episode_id'])
    forms = []
    for index, receipt in enumerate(receipts, 1):
        child, form, schema = reader._attempt(science, index)
        assert child.episode_id == receipt['intent']['episode_id']
        assert requested_fluorescence_sources(schema) == set(FIELDS.values())
        assert_equal(validate_form(form, schema, lambda ref, namespace: namespace in (None, 'artifact') and
            case.db.execute('SELECT 1 FROM artifacts WHERE id=?', (ref,)).fetchone() is not None), form)
        assert_equal(form, case.saved['returned'][index - 1])
        assert_equal(form, science_record['units'][index]['child_result']['form'])
        assert form['completed'] is receipt['delivery_complete']
        for field, source in FIELDS.items():
            assert_equal(form[field], receipt['facts'][source])
        forms.append(form)
    assert_equal(forms[0], case.withdrawal['original_return'])
    assert_equal(read_json(case.directory / 'decision-6.json')['context']['child_reports'][-1], forms[0])
    assert_equal(read_json(case.directory / 'decision-8.json')['context']['child_reports'][-1], forms[1])
    expected = {field: [form[field][0] for form in forms] for field in ('measurements', 'contexts')}
    child, forwarded, schema = reader._attempt(root, 0)
    assert child.episode_id == science.episode_id
    assert requested_fluorescence_sources(schema) == {PROJECTION_SOURCE, CONTEXT_SOURCE}
    validate_form(forwarded, schema, lambda *_: False)
    assert_equal(forwarded, expected)
    assert_equal(forwarded, case.saved['forwarded'])
    assert_equal(forwarded, case.saved['archive']['units'][0]['child_result']['form'])
    frozen = case.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
        (case.run_id, science.episode_id)).fetchone()
    assert_equal(select_fluorescence_return_facts(json.loads(frozen['facts']), schema=schema),
        {PROJECTION_SOURCE: expected['measurements'], CONTEXT_SOURCE: expected['contexts']})
    write_evidence(case, 'returns', dict(original_case=str(case.directory),
        original_complete_values=[row['value'] for row in original['projection']['rows']],
        original_complete_rows=original['projection']['rows'],
        exact_original_receipt_forms_and_both_parent_deliveries=True,
        original_declared_source_and_context_associations=True,
        sheet_and_component_membership='separate test; unavailable payloads must not count as passed',
        result_episode_ids=[r['intent']['episode_id'] for r in receipts],
        scientific_episode_id=science.episode_id, annotation_episode_id=root.episode_id))


def test_saved_prepared_complete_sheet_calculator_comparison(closed_prepared_case):
    case = closed_prepared_case
    original = original_receipts(case)[0]
    files = {role: original['qualified_files'][role] for role in ('sheet', 'calculations')}
    missing = {role: file for role, file in files.items() if not artifact_path(case, file).is_file()}
    if missing:
        write_evidence(case, 'calculator', dict(status='unverified_original_payloads_withdrawn',
            missing=missing, original_case=str(case.directory), new_calculation=False,
            reason='Original full sheet/component equality cannot be recovered from projections or digests.'))
        pytest.skip('UNVERIFIED: original complete sheet/components were withdrawn; '
            'exact original payloads are required for calculator and cell-membership comparison')
    values = {}
    for role, file in files.items():
        path = artifact_path(case, file)
        assert sha256(path) == file['sha256'] and path.stat().st_size == file['size_bytes']
        values[role] = read_json(path)
        assert path.read_bytes() == core.canonical(values[role]) + b'\n'
    sheet, components = values['sheet'], values['calculations']
    assert sheet['schema'] == core.SHEET_SCHEMA and components['schema'] == core.COMPONENTS_SCHEMA
    assert components['sheet_sha256'] == core.digest(sheet)
    calculated = calculate_fluorescence_sheet(sheet,
        parameters=case.plan['requested_job']['native_fluorescence']['parameters'])
    assert_equal(calculated, components)
    selector = original['intent']['assignment']['selector']
    assert_equal(project_fluorescence_result(sheet, components, selection=selector['selection']), original['projection'])
    assert_equal(project_fluorescence_context(sheet, components, selection=selector['selection'],
        context_fields=selector['context_fields']), original['context'])
    assert all(row in components['cells'] for row in original['projection']['rows'])
    write_evidence(case, 'calculator', dict(status='verified_from_exact_original_payloads',
        original_case=str(case.directory), files=files, saved_only_recalculation=True,
        returned_rows_equal_shared_components=True))
