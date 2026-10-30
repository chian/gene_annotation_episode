"""Source-bound recovery sections, scoped delivery and controlled reconstruction."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain, validate_closed_schema
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_calibration_recovery_prompt import CALIBRATION_RECOVERY_TASK
from gene_annotation_episode.literature_calibration_recovery_storage import (
    COMPONENTS, NAMESPACE, REQUESTED, LiteratureCalibrationRecoveryRepository,
    calibration_recovery_cells_schema,
)
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_calibration_recovery_169 import Source

REQUEST = ['recovery', 'percent_bias', 'measured_cv', 'reported_recovery',
           'displayed_minus_reported_recovery', 'correction_for_other_measurement', 'recovery_variance']
FORM = obj({'calibration': calibration_recovery_cells_schema()})


def rebind(value, original, reference):
    if isinstance(value, dict):
        return {k: rebind(v, original, reference) for k, v in value.items()}
    if isinstance(value, list):
        return [rebind(v, original, reference) for v in value]
    return reference if value == original else value


def setup(path, *, requested=REQUEST, source_kind='synthetic_fixture'):
    source = Source()
    store = Store(path)
    manifest = store.path / 'empty-inputs.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    artifact = store.artifact(source.content, 'application/xml')
    record = store.put('source', {'provider': 'synthetic_recovery_fixture', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
        'version': None, 'retrieved_at': None}, origin='caller')
    args = rebind(source.args(), source.reference, record['id']); args['source_kind'] = source_kind
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [record['id']], REQUESTED: list(requested)}
    context = BindingContext('recovery-173', 'source-child', 'literature', (('literature', 'source-child'),),
        store.validate_scope(), assignment, {}, (record['id'],))
    return store, context, args


def binding_for(store, context, *, parent=False):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    services = WorkflowServices(host)
    binding = LiteratureEpisodes(services, rate_population=True,
        reference_parent_sources=[context.received_record_refs[0]] if parent else None)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return services, binding


def populate(store, context, args, key='selected'):
    repository = LiteratureCalibrationRecoveryRepository(store, context.run_id)
    outcome = repository.populate(context, args, key)
    current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    return repository, outcome, current


@pytest.mark.parametrize('source_kind,origin', [('synthetic_fixture', 'synthetic'), ('primary_source', 'reported'), ('retained_extraction', 'derived')])
def test_selected_source_pair_keeps_origins_shared_operands_and_unknowns(tmp_path, source_kind, origin):
    store, context, args = setup(tmp_path, source_kind=source_kind)
    try:
        repo, out, current = populate(store, context, args)
        rows = {row['component']: row for row in out['result']['cells']}
        assert rows['recovery']['value'] == .98 and rows['percent_bias']['value'] == -2
        assert rows['measured_cv']['value'] == pytest.approx(1/49)
        assert rows['recovery']['input_measurement_keys'] == rows['percent_bias']['input_measurement_keys']
        assert all(row['input_origins'] == [origin] for row in rows.values())
        assert rows['correction_for_other_measurement']['value'] is None
        assert rows['recovery_variance']['unavailable_reason'] == 'denominator_uncertainty_and_covariance_not_supplied'
        assert repo.populate(context, args, 'selected') == out
        assert repo.fact_cells(current, out['record_refs'], components=REQUEST) == out['result']['cells']
        assert store.targets() == []
    finally:
        store.close()


@pytest.mark.parametrize('kind', ['SEM', 'unspecified', 'unknown'])
def test_spread_interpretation_survives_typed_return_without_becoming_sd(tmp_path, kind):
    store, context, args = setup(tmp_path)
    try:
        args['spread_kind'] = {'value': kind, 'witnesses': [] if kind == 'unknown' else [args['spread_kind']['witnesses'][0]]}
        _, out, _ = populate(store, context, args)
        row = next(row for row in out['result']['cells'] if row['component'] == 'measured_cv')
        assert row['value'] is None and row['spread_kind'] == kind and row['unavailable_reason'] == 'spread_kind_not_SD'
    finally:
        store.close()


def test_selected_operation_exact_scope_subsets_and_genuine_empty(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        services, binding = binding_for(store, context)
        binding.validate_report(context, {'calibration': []}, FORM)
        missing = asyncio.run(binding.execute(replace(context, received_record_refs=()),
            'literature.calibration.recovery.populate', args, 'not-received'))
        assert missing['feedback']['code'] == 'literature_source_not_received'
        bad = deepcopy(args); bad['nominal_value'] = 10
        assert asyncio.run(binding.execute(context, 'literature.calibration.recovery.populate', bad, 'invented'))['status'] == 'invalid'
        out = asyncio.run(binding.execute(context, 'literature.calibration.recovery.populate', args, 'selected'))
        assert out['status'] == 'completed', out
        # Publication alone has not delivered an output into the old context.
        binding.validate_report(context, {'calibration': []}, FORM)
        current = replace(context, received_record_refs=(*context.received_record_refs, *out['record_refs']))
        form = form_with_facts({}, FORM, binding.facts(current, {'committed_record_refs': out['record_refs']}))
        binding.validate_report(current, form, FORM)
        for changed in ({'calibration': []}, {'calibration': form['calibration'][:-1]}):
            with pytest.raises(ReportBoundaryError, match='requested_subset_mismatch'):
                binding.validate_report(current, changed, FORM)
        altered = deepcopy(form); altered['calibration'][0]['value'] = 3
        with pytest.raises(ReportBoundaryError, match='differs_from_saved'):
            binding.validate_report(current, altered, FORM)
        without_request = replace(current, assignment={k: v for k, v in current.assignment.items() if k != REQUESTED})
        assert binding.facts(without_request, {'committed_record_refs': out['record_refs']})[NAMESPACE] == []
        with pytest.raises(ReportBoundaryError, match='unrequested'):
            binding.validate_report(without_request, form, FORM)
        with pytest.raises(ContractError, match='component_selection_invalid'):
            services.literature_calibration_recovery_repository().project_cells([], permitted_record_refs=(), components=[{}])
        changed_schema = deepcopy(FORM); changed_schema['properties']['calibration']['items']['properties']['source_kind'] = {'type': 'string'}
        with pytest.raises(ReportBoundaryError, match='registered source'):
            validate_closed_schema(changed_schema)
    finally:
        store.close()


def test_every_witness_source_requires_received_scoped_custody(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        source = store.get(args['source_ref'])
        alias = store.put('source', {'provider': 'synthetic_alias', 'accession': None, 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': None, 'request_ref': None, 'version': None,
            'retrieved_at': None}, origin='caller')['id']
        args['matrix']['source_ref'] = alias
        repo = LiteratureCalibrationRecoveryRepository(store, context.run_id)
        with pytest.raises(ContractError, match='source_not_received'):
            repo.populate(context, args, 'unreceived-witness')
        current = replace(context, received_record_refs=(*context.received_record_refs, alias))
        out = repo.populate(current, args, 'received-witness')
        assert alias in repo.read(out['result']['sheet_ref'])['direct_input_source_refs']
        with pytest.raises(ContractError, match='source_not_received'):
            repo.populate(context, args, 'received-witness')
    finally:
        store.close()


def test_parent_can_forward_only_admitted_subset_and_keeps_own_task(tmp_path):
    store, context, args = setup(tmp_path, requested=['recovery'])
    try:
        repo, out, current = populate(store, context, args)
        parent = replace(current, episode_id='parent', role='annotation', path=(('annotation', 'parent'),), assignment={})
        repo.receive_cells(parent, out['result']['cells'], 'trusted-manual')
        assert repo.fact_cells(parent, out['record_refs'], components=COMPONENTS) == out['result']['cells']
        expanded = repo.project_cells(out['record_refs'], permitted_record_refs=parent.received_record_refs, components=['nominal'])
        with pytest.raises(ContractError, match='cell_not_received'):
            repo.validate_fact_values(parent, expanded)
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'},
            'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]},
            'goal': {'objective': 'Evaluate the reference molecule assay evidence.'}, 'working_state': {},
            'child_reports': [{'calibration': out['result']['cells']}]}
        task, steering = render_literature_experimental_prompt(state, 'Retain the original parent question.').split('\n\nSTEERING\n')
        assert REFERENCE_PARENT_TASK in task and CALIBRATION_RECOVERY_TASK not in task
        assert 'Requested recovery numerical components' in steering and 'reporter_standard' in steering
        assert '| nominal |' not in steering and '| measured |' not in steering
        assert out['result']['sheet_ref'] not in steering
        assert all(key not in steering for key in out['result']['cells'][0]['input_measurement_keys'])
    finally:
        store.close()


def test_task_is_full_after_delta_lookup_and_cold_transport(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
    state = snapshot(); state['literature_assignment'][REQUESTED] = REQUEST
    state['goal']['objective'] = 'Evaluate the selected recovery control for the reference assay.'
    lookup_result = {'status': 'completed', 'text': 'Synthetic source: expected stock uncertainty remains unknown.'}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'decision_index': 1,
        'exchange_index': 1, 'result': lookup_result}
    restored = state_frame(state); restored.update(restored_pending_decision_index=1,
        restored_public_exchanges=[{'lookup_result': lookup_result}])
    wire, cold = LiteratureWire(tmp_path / 'wire'), LiteratureWire(tmp_path / 'cold')
    async def exercise():
        await complete(wire, state_frame(state)); await complete(wire, lookup); await complete(cold, restored)
    asyncio.run(exercise())
    tasks = []
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)
        assert task.count(CALIBRATION_RECOVERY_TASK) == 1 and CALIBRATION_RECOVERY_TASK not in steering
        tasks.append(task)
    assert all(task == tasks[0] for task in tasks)
    unrelated = deepcopy(state); unrelated['literature_assignment'].pop(REQUESTED)
    assert CALIBRATION_RECOVERY_TASK not in render_literature_experimental_prompt(unrelated, 'Another scoped assay question.').split('\n\nSTEERING\n')[0]


ORIGINAL = Path(__file__).resolve().parents[1] / 'research/experimental_scoring_review_2026-10-23/a105_calibration_primary_case_167/source/PMC6454709.xml'
ORIGINAL_SHA256 = '86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698'


class OriginalRecoverySelection:
    """Exact selectors into retained original XML; no entered measurement values."""
    def __init__(self, reference, content):
        self.reference = reference; self.content = content; self.text = content.decode('utf-8')
        assert hashlib.sha256(content).hexdigest() == ORIGINAL_SHA256

    def fragment(self, tag, identifier):
        import re
        match = re.search(r'<' + tag + r'\b[^>]*\bid="' + re.escape(identifier) + r'"[^>]*>.*?</' + tag + '>', self.text, re.S)
        assert match is not None, identifier
        return match.group()

    def witness(self, token, container, *, occurrence=0):
        start = -1
        for _ in range(occurrence+1):
            start = container.index(token, start+1)
        absolute = self.text.index(container) + start
        return {'source_ref': self.reference, 'representation': 'original',
            'start': len(self.text[:absolute].encode('utf-8')),
            'end': len(self.text[:absolute+len(token)].encode('utf-8')), 'quote': token}

    def number(self, token, row):
        return {'witness': self.witness(row, row), 'number_start': row.index(token), 'number_end': row.index(token)+len(token)}

    def interpretation(self, value, *witnesses):
        return {'value': value, 'witnesses': list(witnesses)}

    def arguments(self, kind):
        import re
        table = self.fragment('table-wrap', 'Tab2' if kind == 'buffer' else 'Tab4')
        rows = re.findall(r'<tr(?:\s[^>]*)?>.*?</tr>', table, re.S)
        args = {'source_ref': self.reference, 'source_kind': 'primary_source',
            'applicability': self.interpretation('unknown')}
        if kind == 'buffer':
            row, = [row for row in rows if '>8.6</td>' in row]
            methods = self.fragment('p', 'Par31'); repetition = self.fragment('p', 'Par32')
            args.update(experiment=self.witness('Accuracy and precision for measurement of NAD(P)H by colorimetric WST-8 and UV spectrophotometry methods', table),
                analyte=self.witness('NADPH', table), matrix=self.witness('Tris-HCl', methods),
                endpoint=self.witness('formazan absorbance', methods), blank_treatment=None,
                expected_quantity_basis=self.witness('known NAD(P)H amounts', repetition),
                control_kind=self.interpretation('reporter_standard', self.witness(methods, methods)),
                nominal=self.number('8.6', row), measured=self.number('8.72', row), measured_spread=None,
                shared_unit=self.witness('nmole', table), spread_kind=self.interpretation('unknown'),
                reported_recovery=None, reported_recovery_unit=None)
        else:
            row, = [row for row in rows if '>G6PD</td>' in row]
            methods = self.fragment('p', 'Par37'); statistics = self.fragment('p', 'Par43')
            args.update(experiment=self.witness('Spike recoveries of GDH and G6PD in FBS using colorimetric WST-8 assay', table),
                analyte=self.witness('G6PD', row), matrix=self.witness('fetal bovine serum (FBS)', methods),
                endpoint=self.witness('rate of NAD(P)H production', methods),
                blank_treatment=self.witness('The rate of NAD(P)H production measured from the spiked samples was subtracted with that from the FBS.', methods),
                expected_quantity_basis=self.witness('Expected', table),
                control_kind=self.interpretation('enzyme_activity_spike', self.witness(methods, methods)),
                nominal=self.number('1.024', row), measured=self.number('1.235', row), measured_spread=self.number('0.004', row),
                shared_unit=self.witness('nmole/min', table), spread_kind=self.interpretation('SD', self.witness('standard deviation', statistics)),
                reported_recovery=self.number('120.57', row),
                reported_recovery_unit={'value': 'percent', 'witness': self.witness('%', methods, occurrence=1)})
        return args


def original_setup(path):
    store = Store(path)
    manifest = store.path / 'empty-inputs.json'; manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    content = ORIGINAL.read_bytes()
    assert hashlib.sha256(content).hexdigest() == ORIGINAL_SHA256
    artifact = store.artifact(content, 'application/xml')
    source = store.put('source', {'provider': 'retained_original_PMC6454709', 'accession': 'PMC6454709',
        'uri': 'https://doi.org/10.1186/s12858-019-0108-1', 'artifact_ref': artifact,
        'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source['id']], REQUESTED: REQUEST}
    context = BindingContext('original-recovery-173', 'source-child', 'literature', (('literature','source-child'),),
        store.validate_scope(), assignment, {}, (source['id'],))
    selection = OriginalRecoverySelection(source['id'], content)
    return store, context, selection


def test_original_source_controls_preserve_distinct_scope_and_conflict(tmp_path):
    from fractions import Fraction
    store, context, selection = original_setup(tmp_path)
    try:
        repo, buffer, current = populate(store, context, selection.arguments('buffer'), 'buffer-standard')
        _, serum, current = populate(store, current, selection.arguments('serum'), 'serum-enzyme')
        a, b = ({row['component']: row for row in out['result']['cells']} for out in (buffer, serum))
        assert a['recovery']['value'] == float(Fraction('8.72')/Fraction('8.6'))
        assert a['recovery']['control_kind'] == 'reporter_standard' and a['recovery']['source_meanings']['analyte'] == 'NADPH'
        assert a['measured_cv']['value'] is None and a['measured_cv']['unavailable_reason'] == 'measured_spread_not_supplied'
        assert b['recovery']['value'] == float(Fraction('1.235')/Fraction('1.024'))
        assert b['recovery']['control_kind'] == 'enzyme_activity_spike' and b['recovery']['source_meanings']['analyte'] == 'G6PD'
        assert b['reported_recovery']['value'] == 1.2057
        assert b['displayed_minus_reported_recovery']['value'] == float(Fraction('1.235')/Fraction('1.024')-Fraction('1.2057'))
        assert b['measured_cv']['value'] == float(Fraction('.004')/Fraction('1.235'))
        assert repo.read(buffer['result']['sheet_ref'])['sheet']['extraction']['shared_unit']['raw_unit'] == 'nmole'
        assert repo.read(serum['result']['sheet_ref'])['sheet']['extraction']['shared_unit']['raw_unit'] == 'nmole/min'
        assert all(row['value'] is None for row in (a['correction_for_other_measurement'], b['correction_for_other_measurement']))
    finally:
        store.close()


def test_original_source_shared_loop_typed_return_and_readonly_factory(tmp_path, monkeypatch):
    import os
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController, ScriptedProvider
    base = Path(os.environ.get('CALIBRATION_RECOVERY_PROOF_DIR', str(tmp_path)))
    base.mkdir(parents=True, exist_ok=True)
    store, context, selection = original_setup(base / 'state')
    source_ref = selection.reference
    args = [selection.arguments(kind) for kind in ('buffer', 'serum')]
    captured = []; controllers = []; child_tasks = []; parent_prompts = []
    limitations = {'serum_expected_rate_derivation': 'not_established_by_selected_evidence',
        'independent_validation_stocks': 'not_established_by_selected_evidence',
        'quantitative_product_attribution': 'not_established_by_selected_evidence'}
    original_form = obj({'calibration': calibration_recovery_cells_schema(), 'limitations': obj({
        name: {'type': 'string', 'enum': ['not_established_by_selected_evidence']} for name in limitations})})
    child = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(context.assignment),
        'goal': 'Evaluate buffer NADPH detection recovery and G6PD enzyme-activity recovery in FBS, preserving their different meanings.',
        'scope': plain(context.scope), 'purpose': 'Return requested recovery components and scoped unresolved relationships.',
        'schema_json': json.dumps(original_form), 'initial_report_json': json.dumps({'limitations': limitations})}, 'report_update': {}}
    def selected(index):
        def work(inputs):
            prompt = render_literature_experimental_prompt(inputs, 'Evaluate the assigned source recovery controls.')
            task, steering = prompt.split('\n\nSTEERING\n'); child_tasks.append(task)
            assert CALIBRATION_RECOVERY_TASK in task and CALIBRATION_RECOVERY_TASK not in steering, inputs.get('feedback')
            return {'selection': {'kind': 'tool', 'tool': 'literature.calibration.recovery.populate', 'arguments': args[index]}, 'report_update': {}}
        return work
    def integrate(inputs):
        form, = inputs['child_reports']; captured.append(form)
        prompt = render_literature_experimental_prompt(inputs, 'Evaluate what the reference assay controls substantiate.')
        parent_prompts.append(prompt); task, steering = prompt.split('\n\nSTEERING\n')
        assert REFERENCE_PARENT_TASK in task and CALIBRATION_RECOVERY_TASK not in task
        assert 'reporter_standard' in steering and 'enzyme_activity_spike' in steering
        assert form['limitations'] == limitations
        assert len(form['calibration']) == 2*len(REQUEST)
        assert {row['control_kind'] for row in form['calibration']} == {'reporter_standard','enzyme_activity_spike'}
        commit = {field: [] for field in store.reasoning_schema()['required']}
        quote = 'human G6PD enzyme'; start = selection.text.index(quote)
        witness = {'source_ref': source_ref, 'artifact_ref': store.get(source_ref)['artifact_ref'],
            'start': len(selection.text[:start].encode('utf-8')), 'end': len(selection.text[:start+len(quote)].encode('utf-8')), 'quote': quote}
        commit['source_subjects'] = [{'alias': 'studied_reference_molecule', 'reference_type': 'assay',
            'source_ref': source_ref, 'label': quote, 'anchor': witness}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2)
        controllers.append(result); return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        provider = ScriptedProvider([child, selected(0), selected(1), integrate])
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=base / 'run',
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=[source_ref],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=[source_ref]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(captured) == 1 and store.targets() == [] and summary['credit'] == 0
        assert all(CALIBRATION_RECOVERY_TASK in task for task in child_tasks)
        assert [c.scores for c in controllers] == [[0,0],[0,0]]
        observations = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        assert observations == 4
        row, = store.db.execute('SELECT run_id,episode_id,cells FROM literature_calibration_recovery_received').fetchall()
        run_id, parent_id = row['run_id'], row['episode_id']
        exact_rows = json.loads(row['cells']); assert exact_rows == captured[0]['calibration']
        assert store.db.execute('SELECT count(*) FROM literature_calibration_recovery_operations').fetchone()[0] == 2
        host = SimpleNamespace(store=store, run_id=run_id, tools=ToolRegistry(store))
        services = WorkflowServices(host); binding = LiteratureEpisodes(services, rate_population=True, reference_parent_sources=[source_ref])
        descriptor = binding.as_record()
        sheet_refs = list(dict.fromkeys(row['sheet_ref'] for row in exact_rows))
        receiver = BindingContext(run_id, parent_id, 'annotation', (('annotation', parent_id),), context.scope,
            {}, {}, (source_ref, *sheet_refs))
        (base / 'ORIGINAL_ADMITTED_FORM_001.json').write_text(json.dumps(captured[0], indent=2)+'\n')
        (base / 'BINDING_DESCRIPTOR_001.json').write_text(json.dumps(descriptor, indent=2)+'\n')
        saved_sheets = {ref: services.literature_calibration_recovery_repository().read(ref) for ref in sheet_refs}
        (base / 'SAVED_SHEETS_001.json').write_text(json.dumps(saved_sheets, indent=2)+'\n')
        (base / 'CHILD_TASKS_001.json').write_text(json.dumps(child_tasks, indent=2)+'\n')
        (base / 'PARENT_PROMPTS_001.json').write_text(json.dumps(parent_prompts, indent=2)+'\n')
        # Complete/checkpoint/close the controlled writer before immutable RO.
        checkpoint = tuple(store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone())
        assert checkpoint == (0,0,0)
        state_path = store.path; store.close(); store = None
        wal = state_path / 'state.sqlite3-wal'
        assert not wal.exists() or wal.stat().st_size == 0
        before = {str(p.relative_to(state_path)): p.read_bytes() for p in state_path.rglob('*') if p.is_file()}
        readonly = Store.__new__(Store); readonly.path = state_path; readonly._savepoint = 0
        readonly.db = sqlite3.connect((state_path/'state.sqlite3').as_uri()+'?mode=ro&immutable=1', uri=True, isolation_level=None)
        readonly.db.row_factory = sqlite3.Row
        readonly.db.create_function('library_scope_record', 2, readonly._scope_filter_record)
        readonly.db.execute('PRAGMA query_only=ON')
        original_artifact = readonly.get(source_ref)['artifact_ref']; original_get = readonly.get_artifact
        def guarded(reference):
            assert reference != original_artifact, 'scientific source blocked before factory'
            return original_get(reference)
        def forbidden(*_args, **_kwargs):
            raise AssertionError('scientific parsing/calculation/interpretation blocked before factory')
        monkeypatch.setattr(readonly, 'get_artifact', guarded)
        for module, names in {
            'literature_calibration_recovery_inputs': ('read_calibration_recovery_inputs', '_read_number', '_read_unit'),
            'literature_calibration_recovery_calculations': ('populate_calibration_recovery','_validate'),
            'literature_partner_source_fields': ('read_source_number',),
        }.items():
            for name in names:
                monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name, forbidden)
        cold_host = SimpleNamespace(store=readonly, run_id=run_id, tools=SimpleNamespace())
        cold_services = WorkflowServices(cold_host); monkeypatch.setattr(cold_services, 'execute_tool', forbidden)
        changes = readonly.db.total_changes
        restored, = compose_episode_bindings(cold_services, store=readonly,
            journal=SimpleNamespace(store=readonly, run_id=run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        cold_host.episode_bindings = EpisodeBindingRegistry((restored,))
        repository = cold_services.literature_calibration_recovery_repository()
        assert restored.as_record() == descriptor
        assert repository.received_cells(receiver) == exact_rows
        assert repository.fact_cells(receiver, sheet_refs, components=COMPONENTS) == exact_rows
        assert readonly.db.total_changes == changes == 0
        assert {str(p.relative_to(state_path)): p.read_bytes() for p in state_path.rglob('*') if p.is_file()} == before
        proof = {'source_sha256': ORIGINAL_SHA256, 'source_controls': ['reporter_standard', 'enzyme_activity_spike'],
            'targets': 0, 'source_operations': 2, 'runtime_observations': observations,
            'original_typed_admission': True, 'nonempty_parent_reasoning': 'original human G6PD enzyme source anchor',
            'source_and_parsers_and_calculators_disabled_before_factory': True,
            'reconstructed_exact_original_rows': True, 'sqlite_uri_mode': 'ro', 'immutable': True, 'query_only': True,
            'writer_checkpoint_before_readonly_open': checkpoint, 'restoration_total_changes': changes,
            'byte_preservation': True, 'actual_model_execution': False, 'a105_adequacy_claim': False}
        (base / 'PROOF_RESULT_001.json').write_text(json.dumps(proof, indent=2)+'\n')
        readonly.close()
    finally:
        if store is not None:
            store.close()


def test_page_scope_applies_to_every_received_witness_source(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        source = store.get(args['source_ref'])
        alias = store.put('source', {'provider': 'synthetic_unrelated_source', 'accession': None, 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': None, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='caller')['id']
        page = {'version': 'page_assignment_v1', 'source_ref': args['source_ref'], 'representation': 'original',
            'artifact_ref': source['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': [], REQUESTED: REQUEST}
        scoped = replace(context, role='literature_page', path=(('literature_page', context.episode_id),), assignment=page,
            received_record_refs=(*context.received_record_refs, alias))
        args['matrix']['source_ref'] = alias
        _, binding = binding_for(store, scoped)
        out = asyncio.run(binding.execute(scoped, 'literature.calibration.recovery.populate', args, 'outside-assigned-paper'))
        assert out['status'] == 'invalid' and out['feedback']['code'] == 'literature_reading_outside_assigned_source'
    finally:
        store.close()
