"""Selected comparison custody with controlled fixtures; no configured-model claim."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, validate_form, ReportBoundaryError
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_measurement_comparison_storage import (
    LiteratureMeasurementComparisonRepository, measurement_comparison_cells_schema,
    measurement_comparison_operation_schema, COMPONENTS, NAMESPACE, REQUESTED, VIEW, VERSION, OPERATION,
)
from gene_annotation_episode.literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_measurement_comparison_components_258 import source_fixture, original_nfn_fixture


ROOT = Path(__file__).resolve().parents[1]
SELECTED = ['protocol_ratio', 'combined_estimate']


def setup(path, components=SELECTED, *, original=False, optical=False, covariance=None, variance_status='known', values=None, table=False):
    if original:
        selection, docs, _ = original_nfn_fixture()
    else:
        if optical and values is None:
            values = {'left': '20', 'right': '22', 'epsilon_signal': '1.2', 'epsilon_nuisance': '8.6', 'nuisance': '3'}
        selection, docs, _ = source_fixture(values, optical=optical, table=table)
    store = Store(path)
    manifest = path/'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    def source(raw, *, parents=(), provider='explicit_synthetic_comparison268', artifact=None, origin='caller'):
        artifact = artifact or store.artifact(raw)
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None,
            'retrieved_at': None, 'parent_source_refs': list(parents)}, origin=origin)['id']
    mapping = {}
    for (old, representation), data in docs.items():
        assert representation == 'original'
        mapping[old] = source(data['content'], parents=list(mapping.values())[:1],
            provider='retained_parent_converted_nfn268' if original else 'explicit_synthetic_comparison268')
    def remap(value):
        if isinstance(value, dict):
            return {key: remap(child) for key, child in value.items()}
        if isinstance(value, list):
            return [remap(child) for child in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    selection = remap(selection)
    selection['requested_cells'] = list(components)
    sources = list(mapping.values())
    def read(ref, representation):
        record = store.get(ref); artifact = record['artifact_ref'] if representation == 'original' else record['text_ref']
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    if covariance is not None:
        from gene_annotation_episode.literature_measurement_comparison_inputs import read_measurement_comparison_inputs
        extraction = read_measurement_comparison_inputs(selection, read_source=read)
        roles = ['left', 'right']; values_ = [extraction['quantities'][r]['value'] for r in roles]
        document = {'version': 'a105_measurement_comparison_covariance_v1', 'roles': roles,
            'owner_keys': [v['owner_key'] for v in values_], 'units': [v['canonical_unit'] for v in values_],
            'dependency_keys': [v['dependency_keys'] for v in values_], 'covariance': covariance,
            'basis': 'joint_covariance_of_selected_estimates', 'variance_status': variance_status,
            'origin': 'synthetic', 'systematic_coverage': 'included_as_declared', 'derivation': 'synthetic_model'}
        ref = source(json.dumps(document).encode(), parents=[selection['source_ref']]); sources.append(ref)
        selection['covariance_source_refs'] = [ref]
        selection['common_model']['variance_interpretation'] = variance_status+'_joint_estimator_covariance'
    schema = measurement_comparison_operation_schema()['properties']['return_context']['properties']
    context = {role: {name: [] for name in spec['properties']} for role, spec in schema.items()}
    # Context is deliberately selected independently of all numeric tokens.
    for role, quantity in selection['quantities'].items():
        if quantity is not None:
            for name in ('organism', 'molecule', 'construct'):
                witness = quantity['subject'][name]
                if original and witness:
                    context[role]['subject.'+name] = [{'start': witness['start'], 'end': witness['end']}]
            if original and quantity['assay']['direct_endpoint']:
                witness = quantity['assay']['direct_endpoint']
                context[role]['assay.direct_endpoint'] = [{'start': witness['start'], 'end': witness['end']}]
    args = {'version': 'literature_measurement_comparison_population_v2', 'selection': selection, 'return_context': context, 'return_assertion_context': {'molecule': [], 'functional_assertion': []}}
    assignment = {'version': 'literature_assignment_v1', 'source_refs': sources,
        'question_context_refs': [], REQUESTED: list(components)}
    ctx = BindingContext('comparison268', 'child268', 'literature', (('literature', 'child268'),),
        store.validate_scope(), assignment, {}, tuple(sources))
    host = SimpleNamespace(store=store, run_id=ctx.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, reference_parent_sources=sources)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return store, ctx, args, binding, source


def selected(store, ctx, args, binding, key='selected268'):
    outcome = asyncio.run(binding.execute(ctx, OPERATION, args, key))
    assert outcome['status'] == 'completed', outcome
    current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *outcome['record_refs']))
    schema = obj({'numbers': measurement_comparison_cells_schema()})
    form = form_with_facts({}, schema, binding.facts(current, {'committed_record_refs': outcome['record_refs']}))
    binding.validate_report(current, form, schema)
    return current, outcome, form['numbers']


def forbid(*args, **kwargs):
    raise AssertionError('Scientific IO, factory, projection, model or write forbidden')


def block_science(monkeypatch):
    from gene_annotation_episode import literature_measurement_comparison_inputs as inputs
    from gene_annotation_episode import literature_measurement_comparison_calculations as calculations
    from gene_annotation_episode import literature_measurement_comparison_storage as storage
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from gene_annotation_episode import providers
    for module, names in [(inputs, ['read_measurement_comparison_inputs', 'compile_measurement_comparison_inputs',
            'validate_measurement_comparison_extraction', 'validate_measurement_comparison_calculation_inputs',
            'measurement_comparison_selection_schema', 'measurement_comparison_extraction_schema',
            'measurement_comparison_calculation_inputs_schema', 'measurement_comparison_covariance_schema']),
            (calculations, ['populate_measurement_comparison', 'validate_measurement_comparison_sheet',
                'measurement_comparison_sheet_schema', 'measurement_comparison_cell_schema']),
            (storage, ['measurement_comparison_cells_schema', 'measurement_comparison_operation_schema', '_project_once', '_context_projection', '_assertion_projection']),
            (contracts, ['registered_schema']),
            (providers.ModelConnection, ['complete']), (providers._SessionConnection, ['complete']),
            (LiteratureMeasurementComparisonRepository, ['populate', 'receive_cells', '_original_implementation'])]:
        for name in names:
            monkeypatch.setattr(module, name, forbid)


def test_exact_contracts_and_lazy_discovery(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        before = store.db.total_changes
        assert NAMESPACE in binding.fact_sources('literature')
        assert REQUESTED in binding.assignment_schema('literature')['properties']
        assert sum(e['name'] == OPERATION for e in binding.catalog(ctx)) == 1
        assert not binding._measurement_comparison_repository().has_work(ctx)
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_measurement_comparison_operations'").fetchone()
        assert before == store.db.total_changes
        literal = obj({'numbers': measurement_comparison_cells_schema()})
        validate_closed_schema(literal)
        changed = deepcopy(literal)
        changed['properties']['numbers']['minItems'] = 0
        with pytest.raises(ReportBoundaryError):
            validate_closed_schema(changed)
        with pytest.raises(ReportBoundaryError):
            validate_closed_schema(obj({'nested': obj({'numbers': measurement_comparison_cells_schema()})}))
        disabled = LiteratureEpisodes(WorkflowServices(binding.services.workflow))
        assert NAMESPACE not in disabled.fact_sources('literature')
        assert REQUESTED not in disabled.assignment_schema('literature')['properties']
        assert not any(e['name'] == OPERATION for e in disabled.catalog(ctx))
        _, out, rows = selected(store, ctx, args, binding)
        assert [r['component'] for r in rows] == SELECTED
        assert rows[0]['cell']['value'] == pytest.approx(20/22)
        assert rows[1]['cell']['value'] is None
        assert rows[0]['covariance_provenance'] == []
        assert asyncio.run(binding.execute(ctx, OPERATION, args, 'selected268')) == out
    finally:
        store.close()


@pytest.mark.parametrize('components', [[], ['native_left'], ['combined_variance', 'protocol_ratio']])
def test_exact_ordered_request_and_known_covariance(tmp_path, components):
    store, ctx, args, binding, _ = setup(tmp_path/'state', components, covariance=[[4, 1], [1, 9]])
    try:
        _, _, rows = selected(store, ctx, args, binding)
        assert [r['component'] for r in rows] == components
        for row in rows:
            assert 'matrix_exact' not in canonical(row)
            assert not any(key in row for key in ('quantities', 'covariance_blocks', 'native_exact'))
            if row['component'] == 'combined_variance':
                assert row['cell']['value'] == pytest.approx(35/11)
                assert row['covariance_provenance'][0]['variance_status'] == 'known'
    finally:
        store.close()


@pytest.mark.parametrize('failure', ['roster', 'source', 'covariance', 'context_numeric', 'assertion_numeric', 'old_version'])
def test_closed_preflight_and_selected_source_custody(tmp_path, failure):
    store, ctx, args, binding, source = setup(tmp_path/'state')
    try:
        if failure == 'roster':
            args['selection']['requested_cells'].reverse()
        elif failure == 'source':
            args['selection']['source_ref'] = source(b'unreceived source')
        elif failure == 'covariance':
            args['selection']['covariance_source_refs'] = [source(b'unreceived covariance')]
        elif failure in ('context_numeric', 'assertion_numeric'):
            number = args['selection']['quantities']['left']['number']
            witness = deepcopy(number['witness'])
            start = witness['start'] + len(witness['quote'][:number['number_start']].encode())
            end = witness['start'] + len(witness['quote'][:number['number_end']].encode())
            if failure == 'context_numeric':
                args['selection']['quantities']['left']['assay']['conditions'] = witness
                args['return_context']['left']['assay.conditions'] = [{'start': start, 'end': end}]
            else:
                args['selection']['assertion']['functional_assertion'] = witness
                args['return_assertion_context']['functional_assertion'] = [{'start': start, 'end': end}]
        else:
            args['version'] = 'literature_measurement_comparison_population_v1'
        out = asyncio.run(binding.execute(ctx, OPERATION, args, 'invalid268'))
        assert out['status'] == 'invalid' and out['feedback']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_measurement_comparison_operations'").fetchone()
    finally:
        store.close()


def test_nested_covariance_source_must_belong_to_assigned_page(tmp_path):
    store, ctx, args, binding, source = setup(tmp_path/'state')
    try:
        alien = source(b'elsewhere covariance')
        root = args['selection']['source_ref']
        page = {'version': 'page_assignment_v1', 'source_ref': root, 'representation': 'original',
            'artifact_ref': store.get(root)['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': []}
        ctx = replace(ctx, role='literature_page', path=(('literature_page', ctx.episode_id),),
            assignment={**page, REQUESTED: SELECTED}, received_record_refs=(*ctx.received_record_refs, alien))
        args['selection']['covariance_source_refs'] = [alien]
        out = asyncio.run(binding.execute(ctx, OPERATION, args, 'alien268'))
        assert out['status'] == 'invalid'
        assert out['feedback']['code'] == 'literature_reading_outside_assigned_source'
    finally:
        store.close()


@pytest.mark.parametrize('origin', ['caller', 'tool'])
def test_original_input_record_identity_preserves_legitimate_origins_and_rejects_forgery(tmp_path, origin):
    store, ctx, args, binding, source = setup(tmp_path/'state', ['native_left'])
    try:
        old = args['selection']['source_ref']
        if origin == 'tool':
            row = store.get(old)
            new = source(b'', artifact=row['artifact_ref'], provider='legitimate_tool_source268', origin='tool')
            def remap(value):
                if isinstance(value, dict):
                    return {key: remap(child) for key, child in value.items()}
                if isinstance(value, list):
                    return [remap(child) for child in value]
                return new if value == old else value
            args = remap(args)
            ctx = replace(ctx, assignment=remap(plain(ctx.assignment)),
                received_record_refs=tuple(new if ref == old else ref for ref in ctx.received_record_refs))
        ref = args['selection']['source_ref']
        repo = binding._measurement_comparison_repository()
        assert repo._native_source(ctx, ref)['origin'] == origin
        forged = store.get(ref)
        forged['provider'] = 'altered_without_new_identity268'
        store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(forged), ref))
        out = asyncio.run(binding.execute(ctx, OPERATION, args, 'forged268'))
        assert out['status'] == 'invalid'
        assert out['feedback']['code'] == 'measurement_comparison_input_source_identity_mismatch'
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_measurement_comparison_operations'").fetchone()
    finally:
        store.close()


@pytest.mark.parametrize('status,right', [('known', '20'), ('estimated', '22')])
def test_singular_partial_meaning_survives_return(tmp_path, status, right):
    components = ['combined_estimate', 'combined_variance', 'weight_left', 'standardized_difference']
    store, ctx, args, binding, _ = setup(tmp_path/'state', components,
        covariance=[[4, 4], [4, 4]], variance_status=status, values={'left': '20', 'right': right})
    try:
        _, _, rows = selected(store, ctx, args, binding)
        cells = {r['component']: r['cell'] for r in rows}
        assert cells['weight_left']['value'] is None
        assert cells['standardized_difference']['value'] is None
        if status == 'known':
            assert cells['combined_estimate']['value'] == 20
            assert cells['combined_variance']['value'] == 4
        else:
            assert cells['combined_estimate']['value'] is None
            assert 'combined_estimate_not_identified_by_plugin_covariance' in cells['combined_estimate']['reasons']['domain']
    finally:
        store.close()


def test_optical_component_scopes_and_signal_context(tmp_path):
    components = ['spectral_multiplier', 'observed_interference', 'corrected_estimate']
    store, ctx, args, binding, _ = setup(tmp_path/'state', components, optical=True)
    try:
        _, _, rows = selected(store, ctx, args, binding)
        spectral, interference, correction = rows
        assert spectral['model_settings']['optical_observation_equation'] is None
        assert spectral['model_settings']['optical_signal_role'] is None
        assert spectral['model_settings']['optical_nuisance_sign'] is None
        assert {m['role'] for m in spectral['role_meanings']} == {'epsilon_signal', 'epsilon_nuisance'}
        assert {m['role'] for m in interference['role_meanings']} == {'left', 'epsilon_signal', 'epsilon_nuisance', 'nuisance'}
        assert 'left' not in interference['cell']['operand_roles']
        assert 'left' not in {d['role'] for d in interference['dependencies']}
        assert interference['model_settings']['optical_nuisance_sign'] == -1
        assert correction['model_settings']['optical_observation_equation'] == 'y=h+s*alpha*f'
        from gene_annotation_episode.literature_measurement_comparison_render import render_received
        parts = []
        render_received(parts, rows, section=lambda p, t, c: p.extend([t, str(c)]), table=lambda h, r: str((h, list(r))))
        text = '\n'.join(parts)
        assert 'synthetic fixture' in text and 'synthetic' in text
        assert 'y=h+s*alpha*f' in text and 'nuisance sign' in text
    finally:
        store.close()


def test_native_nondetection_meaning_never_becomes_exact_zero(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state', ['native_left', 'protocol_ratio'], values={'left': '0', 'right': '22'})
    try:
        args['selection']['quantities']['left']['semantics']['value'] = 'reported_nondetection'
        _, _, rows = selected(store, ctx, args, binding)
        assert rows[0]['cell']['value'] == 0  # Printed report retained, qualification travels with it.
        assert rows[0]['role_meanings'][0]['semantics'] == 'reported_nondetection'
        assert rows[1]['cell']['value'] is None
        assert 'native_nondetection_not_point' in rows[1]['cell']['reasons']['source']
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'child_reports': [{'numbers': rows}], 'working_state': {}}
        text = render_literature_experimental_prompt(state, 'Assess the received source report.')
        assert 'reported nondetection' in text
    finally:
        store.close()


def test_actual_parent_converted_source_assertion_and_valid_partials(tmp_path):
    components = ['protocol_ratio', 'protocol_difference', 'required_nuisance_equivalent_scenario', 'combined_estimate']
    store, ctx, args, binding, _ = setup(tmp_path/'state', components, original=True)
    try:
        for name, witness in args['selection']['assertion'].items():
            if name != 'question' and witness:
                args['return_assertion_context'][name] = [{'start': witness['start'], 'end': witness['end']}]
        current, _, rows = selected(store, ctx, args, binding)
        assert rows[0]['cell']['value'] == pytest.approx(8/23)
        assert rows[1]['cell']['value'] == -15
        assert rows[2]['cell']['conditional_value'] == pytest.approx(90/43)
        assert rows[3]['cell']['value'] is None
        assert all(row['source_kind'] == 'primary_source' for row in rows)
        assert rows[0]['assertion_context']['molecule']['fragments'][0]['text'] == 'NfnAB'
        assert 'NADH' in rows[0]['assertion_context']['functional_assertion']['fragments'][0]['text']
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'child_reports': [{'numbers': rows}], 'working_state': {}}
        text = render_literature_experimental_prompt(state, 'Assess only delivered results.')
        task, steering = text.split('\n\nSTEERING\n')
        assert MEASUREMENT_COMPARISON_TASK not in task
        assert 'Assess only delivered results.' in task
        assert 'NfnAB' in steering and 'fitted asymptote' in steering
        assert 'stipulated sensitivity' in steering
        assert not any('quote' in loc for row in rows for dep in row['dependencies'] for loc in dep['source_locations'])
    finally:
        store.close()


@pytest.mark.parametrize('missing', [False, True])
def test_discovery_does_not_require_a_known_assertion(tmp_path, missing):
    store, ctx, args, binding, _ = setup(tmp_path/'state', ['native_left'])
    try:
        if missing:
            args['selection']['assertion']['functional_assertion'] = None
        _, _, rows = selected(store, ctx, args, binding)
        assert rows[0]['cell']['value'] == 20
        assert rows[0]['assertion_context']['functional_assertion']['status'] == ('source_unavailable' if missing else 'not_selected')
    finally:
        store.close()


def test_nonowner_requested_intersection_private_receipts_and_history(tmp_path):
    store, ctx, args, binding, source = setup(tmp_path/'state')
    try:
        current, out, rows = selected(store, ctx, args, binding)
        repo = binding._measurement_comparison_repository(); ref = out['result']['sheet_ref']
        parent = replace(current, episode_id='parent268', path=(('literature', 'parent268'),),
            assignment={**plain(ctx.assignment), REQUESTED: SELECTED[:1]})
        schema = obj({'numbers': measurement_comparison_cells_schema()})
        binding.received_form_references(parent, {'numbers': rows[:1]}, schema, 'explicit_controlled_delivery268')
        assert repo.fact_cells(parent, [ref], components=list(reversed(SELECTED))) == rows[:1]
        with pytest.raises(ContractError):
            repo.validate_fact_values(parent, rows)
        record = store.get(ref)
        aliases = [source(b'', artifact=record[name]) for name in ('artifact_ref', 'request_ref')]
        for target in [ref, *aliases]:
            receiver = replace(parent, received_record_refs=(*parent.received_record_refs, target))
            result = asyncio.run(binding.execute(receiver, 'source.read', {'source_ref': target,
                'representation': 'original'}, 'private268'+target))
            assert result['status'] == 'invalid' and result['feedback']['code'] == 'measurement_comparison_receipt_private'
        history = {'status': 'completed', 'result': {'view': 'records', 'records': [{
            'selection': {'kind': 'tool', 'tool': OPERATION, 'arguments': args},
            'outcome': out, 'admitted_report': {'numbers': rows[:1]}}]}}
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'child_reports': [{'numbers': rows[:1]}], 'working_state': {},
            'literature_measurement_comparison_receipt_bindings': repo.receipt_bindings()}
        text = render_literature_experimental_prompt(state, 'Compare received evidence.', lookup_results=[history])
        steering = text.split('\n\nSTEERING\n')[1]
        assert 'protocol ratio' in steering
        assert 'combined estimate' not in steering
        assert 'native_exact' not in steering and 'covariance_blocks' not in steering
        assert 'left NADH rate 20' not in steering
    finally:
        store.close()


def test_full_task_relevance_lookup_failure_and_capability_separation(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'working_state': {}}
        assert MEASUREMENT_COMPARISON_TASK not in render_literature_experimental_prompt(state, 'Read the source.')
        assigned = {**state, 'literature_assignment': plain(ctx.assignment)}
        assert MEASUREMENT_COMPARISON_TASK in render_literature_experimental_prompt(assigned, 'Read the source.')
        lookup = {'status': 'completed', 'result': {'information_kind': 'operation_contract_information_v1',
            'operation': OPERATION, 'meaning': 'Read selected comparisons.', 'text': 'Original closed arguments.'}}
        assert MEASUREMENT_COMPARISON_TASK in render_literature_experimental_prompt(state, 'Read the source.', lookup_results=[lookup])
        failed = {**state, 'last_local_outcome': {'status': 'invalid', 'selected_tool': OPERATION,
            'feedback': {'code': 'source_not_received'}}}
        assert MEASUREMENT_COMPARISON_TASK in render_literature_experimental_prompt(failed, 'Repair the selected source request.')
    finally:
        store.close()


def test_original_report_repair_redelivery_without_repopulation(tmp_path, monkeypatch):
    """One explicit admission fault tests accounting/custody, not source invalidity."""
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
    from gene_annotation_episode.runtime import run_workflow, TypedReportContract
    from test_runtime import FixtureController, ScriptedProvider
    store, ctx, args, _, _ = setup(tmp_path/'state', ['protocol_ratio'])
    original_schema = obj({'numbers': measurement_comparison_cells_schema()})
    repaired = obj({'numbers': measurement_comparison_cells_schema()})
    commission = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(ctx.assignment),
        'goal': 'Read the synthetic comparison.', 'scope': plain(ctx.scope), 'purpose': 'Return selected comparison.',
        'schema_json': json.dumps(original_schema), 'initial_report_json': '{}'}, 'report_update': {}}
    work = {'selection': {'kind': 'tool', 'tool': OPERATION, 'arguments': args}, 'report_update': {}}
    progress = ScientificFindingProgress(FindingProgressPolicy(1))
    options = {'run_dir': tmp_path/'run', 'controller_factory': lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
        'project_credit': progress, 'binding_definitions': {'credit': progress.as_record()},
        'initial_known_record_refs': list(ctx.received_record_refs),
        'episode_binding_factories': (partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=list(ctx.received_record_refs)),)}
    try:
        admit = TypedReportContract.admit
        controlled_failures = []
        def fail_first_comparison_admission(contract, value, *, audit_identifiers):
            if not controlled_failures and value.get('numbers') and contract.schema['properties'].get('numbers', {}).get('x-source') == NAMESPACE:
                controlled_failures.append('explicit_controlled_admission_fault268')
                raise ReportBoundaryError('Explicit controlled first-admission fault.', code='controlled_admission_fault268', field='numbers')
            return admit(contract, value, audit_identifiers=audit_identifiers)
        monkeypatch.setattr(TypedReportContract, 'admit', fail_first_comparison_admission)
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, work, KeyboardInterrupt()]), **options))
        assert len(controlled_failures) == 1
        monkeypatch.setattr(TypedReportContract, 'admit', admit)
        original_operation = store.db.execute('SELECT outcome FROM literature_measurement_comparison_operations').fetchone()[0]
        original_forms = [r[0] for r in store.db.execute('SELECT form FROM runtime_forms')]
        from gene_annotation_episode import literature_measurement_comparison_inputs as inputs
        from gene_annotation_episode import literature_measurement_comparison_calculations as calculations
        monkeypatch.setattr(inputs, 'read_measurement_comparison_inputs', forbid)
        monkeypatch.setattr(inputs, 'compile_measurement_comparison_inputs', forbid)
        monkeypatch.setattr(calculations, 'populate_measurement_comparison', forbid)
        seen = []
        def repair(view):
            assert view['feedback']['reason'] == 'controlled_admission_fault268'
            return {'selection': {'kind': 'redeliver_report', 'delivery_ref': view['feedback']['delivery_ref'],
                'purpose': 'Receive the original saved requested numerical subset.', 'schema_json': json.dumps(repaired)}, 'report_update': {}}
        def integrate(view):
            seen.append(deepcopy(view['child_reports'][0]))
            assert [r['component'] for r in seen[0]['numbers']] == ['protocol_ratio']
            commit = {key: [] for key in store.reasoning_schema()['required']}
            witness = args['selection']['quantities']['left']['subject']['molecule']
            commit['source_subjects'] = [{'alias': 'received_molecule268', 'reference_type': 'assay',
                'source_ref': witness['source_ref'], 'label': witness['quote'], 'anchor': {
                    'source_ref': witness['source_ref'], 'artifact_ref': store.get(witness['source_ref'])['artifact_ref'],
                    'start': witness['start'], 'end': witness['end'], 'quote': witness['quote']}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        asyncio.run(run_workflow(store, ToolRegistry(store), resume=True, provider=ScriptedProvider([repair, integrate]), **options))
        assert len(seen) == 1
        assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 2
        assert store.db.execute('SELECT count(*) FROM literature_measurement_comparison_received').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_measurement_comparison_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT outcome FROM literature_measurement_comparison_operations').fetchone()[0] == original_operation
        assert [r[0] for r in store.db.execute('SELECT form FROM runtime_forms')] == original_forms
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
    finally:
        store.close()


@pytest.mark.parametrize('profile,alias,nested,original', [
    (None, False, False, False), (None, True, False, True),
    ('operation_contract_information_v1', True, False, False), (None, True, True, False),
])
def test_selected_shared_loop_return_and_first_cold_reconstruction(tmp_path, monkeypatch, profile, alias, nested, original):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController, ScriptedProvider
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select as action
    from test_literature_compiled_assay_185 import readonly
    import gene_annotation_episode.communication as communication
    requested = (['protocol_ratio', 'protocol_difference', 'required_nuisance_equivalent_scenario', 'combined_estimate'] if original
        else ['protocol_ratio', 'protocol_difference', 'combined_estimate'] if nested else SELECTED)
    store, ctx, args, _, _ = setup(tmp_path/'state', requested, original=original)
    if original:
        for name in ('molecule', 'functional_assertion'):
            witness = args['selection']['assertion'][name]
            args['return_assertion_context'][name] = [{'start': witness['start'], 'end': witness['end']}]
    sources = list(ctx.received_record_refs)
    literal = obj({'numbers': measurement_comparison_cells_schema(),
        'limit': {'type': 'string', 'enum': ['source_qualifications_retained']}})
    submitted = obj({'numbers': {'$ref': 'episode-fact:'+NAMESPACE}, 'limit': literal['properties']['limit']}) if alias else literal
    captured = []
    outer_components = list(reversed(requested[:2])) if nested else requested
    def response(value):
        if not profile:
            return value
        value = deepcopy(value)
        if value['selection']['kind'] == 'tool':
            value['selection']['arguments'] = json.dumps(value['selection']['arguments'])
        return action(value)
    def commission(role, assignment):
        return response({'selection': {'kind': 'episode_child', 'role': role, 'assignment': assignment,
            'goal': 'Evaluate the selected source measurements with their functional and protocol qualifications.',
            'scope': plain(ctx.scope), 'purpose': 'Return only requested comparison cells and necessary limits.',
            'schema_json': json.dumps(submitted), 'initial_report_json': json.dumps({'limit': 'source_qualifications_retained'})},
            'report_update': {}})
    def work(inputs):
        view = provider.views[provider.active_episode] if profile else inputs
        task, _ = render_literature_experimental_prompt(view, 'Read the selected comparison.').split('\n\nSTEERING\n')
        assert MEASUREMENT_COMPARISON_TASK in task
        return response({'selection': {'kind': 'tool', 'tool': OPERATION, 'arguments': args},
            'report_update': {'limit': 'source_qualifications_retained'}})
    def integrate(inputs):
        view = provider.views[provider.active_episode] if profile else inputs
        form, = view['child_reports']; captured.append(deepcopy(form))
        wanted = outer_components if nested and len(captured) == 2 else requested
        assert [r['component'] for r in form['numbers']] == wanted
        prompt = render_literature_experimental_prompt(view, 'Assess only received comparison evidence.')
        task, steering = prompt.split('\n\nSTEERING\n')
        if nested and len(captured) == 1:
            # This literature parent owns an explicit comparison request.
            assert MEASUREMENT_COMPARISON_TASK in task
        else:
            # The annotation parent receives the child's numbers as STEERING.
            assert MEASUREMENT_COMPARISON_TASK not in task
        assert 'protocol ratio' in steering
        assert 'matrix_exact' not in steering
        commit = {key: [] for key in store.reasoning_schema()['required']}
        witness = args['selection']['quantities']['left']['subject']['molecule']
        artifact = store.get(witness['source_ref'])['artifact_ref']
        commit['source_subjects'] = [{'alias': 'studied_molecule268', 'reference_type': 'assay',
            'source_ref': witness['source_ref'], 'label': witness['quote'], 'anchor': {
                'source_ref': witness['source_ref'], 'artifact_ref': artifact,
                'start': witness['start'], 'end': witness['end'], 'quote': witness['quote']}}]
        return response({'selection': {'kind': 'reason', 'commit': commit},
            'report_update': {'limit': 'source_qualifications_retained'} if nested and len(captured) == 1 else {}})
    outer = {**plain(ctx.assignment), REQUESTED: outer_components}
    script = [commission('literature', outer)]
    if nested:
        script.append(commission('literature_strategy', {'version': 'strategy_assignment_v1',
            'question_context_refs': [], 'prior_search_refs': sources, REQUESTED: requested}))
    script += [work, integrate, *([integrate] if nested else [])]
    class ControlledPresented(PresentedProvider):
        async def complete(self, episode_id, *args):
            self.active_episode = episode_id
            return await super().complete(episode_id, *args)
    provider = ControlledPresented(script) if profile else ScriptedProvider(script)
    progress = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial,
                2 if len(path) == 1 or nested and len(path) == 2 else 1),
            project_credit=progress, binding_definitions={'credit': progress.as_record()}, initial_known_record_refs=sources,
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=sources, contract_information_profile=profile),),
            **({'decision_protocol': 'decision_exchange_v1'} if profile else {})))
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == (5 if nested else 3)
        assert store.db.execute('SELECT count(*) FROM literature_measurement_comparison_operations').fetchone()[0] == 1
        run_id, parent = store.db.execute('SELECT run_id,episode_id FROM literature_measurement_comparison_received ORDER BY rowid DESC LIMIT 1').fetchone()
        original_form = captured[-1]; ref = original_form['numbers'][0]['sheet_ref']
        repo = LiteratureMeasurementComparisonRepository(store, run_id); saved = repo.read(ref)
        descriptors = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
        assert saved['original_implementation']['bound_descriptor'] == descriptors[0]
        allowed = {store.get(ref)[k] for k in ('artifact_ref', 'request_ref')}
        receiver = replace(ctx, run_id=run_id, episode_id=parent, role='annotation', path=(('annotation', parent),),
            assignment={}, received_record_refs=tuple(repo.cell_record_refs(original_form['numbers'])))
        for name, value in [('ORIGINAL_FORM_268.json', original_form), ('ORIGINAL_SCHEMA_268.json', literal),
                ('ORIGINAL_SHEET_268.json', saved), ('ORIGINAL_DESCRIPTOR_268.json', descriptors),
                ('ORIGINAL_RECEIVER_268.json', receiver.as_record()), ('ORIGINAL_ARTIFACTS_268.json', sorted(allowed))]:
            (tmp_path/name).write_text(json.dumps(value, indent=2)+'\n')
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
        before = {str(p.relative_to(tmp_path/'state')): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (tmp_path/'state').rglob('*') if p.is_file()}
        block_science(monkeypatch); monkeypatch.setattr(type(provider), 'complete', forbid)
        communication._compiled_schema_content.cache_clear()
        with readonly(tmp_path/'state') as cold:
            get = cold.get_artifact
            def saved_only(reference):
                assert reference in allowed, 'Original scientific bytes forbidden'
                return get(reference)
            monkeypatch.setattr(cold, 'get_artifact', saved_only)
            host = SimpleNamespace(store=cold, run_id=run_id, tools=None)
            restored = compose_episode_bindings(WorkflowServices(host), store=cold,
                journal=SimpleNamespace(store=cold, run_id=run_id), execution_backend=None,
                descriptors=descriptors, job_episodes=None, resource_estimator=None, role_credit_bindings={})
            host.episode_bindings = EpisodeBindingRegistry(restored.bindings); binding, = restored.bindings
            assert binding.as_record() == descriptors[0]
            assert binding.received_report_facts(receiver)[NAMESPACE] == original_form['numbers']
            assert binding._measurement_comparison_repository().read(ref) == saved
            validate_form(original_form, literal, lambda ref, namespace: True)
            assert cold.db.total_changes == 0
        after = {str(p.relative_to(tmp_path/'state')): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (tmp_path/'state').rglob('*') if p.is_file()}
        assert before == after
        if original:
            completed = subprocess.run([sys.executable, '-B', str(ROOT/'verification/a105_measurement_comparison_binding_268/first_cold_process_001.py'),
                str(tmp_path)], cwd=ROOT, text=True, capture_output=True)
            (tmp_path/'FRESH_COLD_PROCESS_STDOUT_268.txt').write_text(completed.stdout)
            (tmp_path/'FRESH_COLD_PROCESS_STDERR_268.txt').write_text(completed.stderr)
            assert completed.returncode == 0, completed.stderr
            probe = json.loads((tmp_path/'FRESH_COLD_PROCESS_268.json').read_text())
            assert probe['fresh_process'] and probe['state_byte_hashes_unchanged']
            assert probe['only_original_two_receipt_artifacts_read'] and probe['sqlite_changes'] == 0
    finally:
        try:
            store.close()
        except Exception:
            pass
