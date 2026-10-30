"""Selected common assessment; controlled providers, never actual-model claims."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain, ReportBoundaryError, validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_compiled_assay_storage import (
    LiteratureCompiledAssayRepository, compiled_assay_v3_cells_schema,
    compiled_assay_operation_schema, VERSION_V3, NAMESPACE_V3, REQUESTED_V3)
from gene_annotation_episode.literature_compiled_assay_prompt import COMMON_ASSESSMENT_TASK, COMPILED_ASSAY_TASK
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.tools import ToolRegistry
from test_literature_common_assessment_221 import Case, exact


DEFAULT = ['estimate_product_test', 'product_reference_contrast', 'saturation_turnover_reference_contrast',
    'low_substrate_efficiency_reference_contrast', 'occupancy_reference_contrast',
    'post_binding_residual_ratio', 'binding_only_log_residual', 'binding_only_residual_variance']


def binding_for(case, *, profile=None):
    host = SimpleNamespace(store=case.store, run_id=case.context.run_id, tools=ToolRegistry(case.store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, compiled_assay_population=True,
        reference_parent_sources=[case.source], contract_information_profile=profile)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def selected(case, requested=DEFAULT, *, change=None, key='common223'):
    args = case.args(requested)
    if change:
        change(args)
    ctx = replace(case.context, assignment={**plain(case.context.assignment), REQUESTED_V3: list(requested)})
    binding = binding_for(case)
    out = asyncio.run(binding.execute(ctx, 'literature.assay.components.populate', args, key))
    assert out['status'] == 'completed', out
    ctx = replace(ctx, received_record_refs=(*ctx.received_record_refs, *out['record_refs']))
    form = obj({'numbers': compiled_assay_v3_cells_schema()})
    rows = form_with_facts({}, form, binding.facts(ctx, {'committed_record_refs': out['record_refs']}))['numbers']
    binding.validate_report(ctx, {'numbers': rows}, form)
    return binding, ctx, args, out, rows


@pytest.mark.parametrize('index', [1, 2])
def test_selected_actual_native_rows_and_conditional_assertion_components(tmp_path, index):
    case = Case(tmp_path/'state', index)
    try:
        binding, ctx, args, out, rows = selected(case)
        by_name = {r['component']: r for r in rows}
        assert [r['component'] for r in rows] == DEFAULT
        assert by_name['estimate_product_test']['value'] == (92 if index == 1 else 132)
        assert by_name['product_reference_contrast']['value'] == pytest.approx((92 if index == 1 else 132)/206)
        assert by_name['saturation_turnover_reference_contrast']['value'] == pytest.approx((54 if index == 1 else 165)/124)
        assert by_name['post_binding_residual_ratio']['value'] is None
        assert by_name['post_binding_residual_ratio']['conditional_value'] == pytest.approx(.4537857675583336 if index == 1 else .644041721703724)
        assert 'joint_covariance_not_selected' in by_name['binding_only_residual_variance']['implementation_reasons']
        assert by_name['product_reference_contrast']['covariance_provenance'] is None
        repo = LiteratureCompiledAssayRepository(case.store, ctx.run_id).v3_projection()
        saved = repo.read(out['result']['sheet_ref'])
        assert saved['sheet']['host_custody'] == rows[0]['host_custody']
        assert saved['original_implementation']['files']['literature_compiled_assay_inputs.py'] == 'f158d01f14b7b57c60665a1508f729c5e2b04bc2cf3d5a07e560851c287b1ada'
        assert repo.populate(replace(ctx, received_record_refs=ctx.received_record_refs[:-1]), args, 'common223') == out
        assert not case.store.list('assessment') and not case.store.list('observation')
        assert out['result']['record_version'] == VERSION_V3
        assert not any('matrix_exact' in json.dumps(row) or 'component_snapshots' in row for row in rows)
        for version in (1, 2):
            with pytest.raises(ContractError, match='sheet_required'):
                LiteratureCompiledAssayRepository(case.store, ctx.run_id, version).read(out['result']['sheet_ref'])
    finally:
        case.store.close()


def test_exact_parent_selection_empty_default_and_no_discovery_install(tmp_path):
    case = Case(tmp_path/'state')
    try:
        binding = binding_for(case)
        before = case.store.db.total_changes
        names = {r['name'] for r in binding.catalog(case.context)}
        assert 'literature.assay.components.populate' in names
        assert len(compiled_assay_operation_schema()['anyOf']) == 3
        assert REQUESTED_V3 in binding.assignment_schema('literature')['properties']
        assert NAMESPACE_V3 in binding.fact_sources('literature')
        assert not case.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_compiled_assay_operations'").fetchone()
        assert case.store.db.total_changes == before
        out = asyncio.run(binding.execute(case.context, 'literature.assay.components.populate', case.args(['product_reference_contrast']), 'bad223'))
        assert out['status'] == 'invalid' and out['feedback']['code'] == 'common_assessment_requested_subset_mismatch'
        binding, ctx, args, out, rows = selected(case, [])
        assert rows == [] and out['result']['cells'] == []
        assert 'common_assessment_request' not in json.dumps(binding.fact_sources('literature')[NAMESPACE_V3]['report_schema'])
        validate_closed_schema(obj({'numbers': compiled_assay_v3_cells_schema()}))
    finally:
        case.store.close()


def test_assigned_page_checks_new_model_and_upstream_sources(tmp_path):
    case = Case(tmp_path/'state')
    try:
        binding = binding_for(case)
        assignment = {'version': 'page_assignment_v1', 'source_ref': case.source,
            'representation': 'original', 'artifact_ref': case.store.get(case.source)['artifact_ref'],
            'question_context_refs': [], 'prior_delivery_refs': [], REQUESTED_V3: ['product_reference_contrast']}
        ctx = replace(case.context, role='literature_page', path=(('literature_page', case.context.episode_id),), assignment=assignment)
        result = asyncio.run(binding.execute(ctx, 'literature.assay.components.populate',
            case.args(['product_reference_contrast']), 'outside_page223'))
        assert result['status'] == 'invalid'
        assert result['feedback']['code'] == 'literature_reading_outside_assigned_source'
        assert not case.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_compiled_assay_operations'").fetchone()
    finally:
        case.store.close()


def test_unified_object_wrapper_preserves_actual_v1_v2_selected_requests(tmp_path):
    from test_literature_compiled_assay_185 import setup
    from test_literature_compiled_assay_binding_185 import binding_for as old_binding
    from test_literature_compiled_assay_uncertainty_215 import v2, PART
    from gene_annotation_episode.literature_compiled_assay_storage import (
        REQUESTED, REQUESTED_V2, VERSION, VERSION_V2, compiled_assay_cells_schema)
    from gene_annotation_episode.literature_compiled_assay_inputs import compiled_assay_operation_schema as pure_factory
    from gene_annotation_episode.domain import validate_schema
    store, ctx, args, _ = setup(tmp_path/'state')
    try:
        binding = old_binding(store, ctx)
        old = replace(ctx, assignment={**plain(ctx.assignment), REQUESTED: [PART]})
        new, new_args = v2(old, args, requested=(PART,))
        schema = next(row['input_schema'] for row in binding.catalog(ctx) if row['name'] == 'literature.assay.components.populate')
        assert schema['type'] == 'object' and len(schema['anyOf']) == 3
        assert len(pure_factory()['anyOf']) == 2
        for version, context, arguments, expected_version in ((1, old, args, VERSION), (2, new, new_args, VERSION_V2)):
            validate_schema(arguments, schema)
            out = asyncio.run(binding.execute(context, 'literature.assay.components.populate', arguments, 'legacy_wrapper_' + str(version)))
            assert out['status'] == 'completed', out
            assert 'record_version' not in out['result'] and 'scientific_sheet_version' not in out['result']
            assert store.get(out['result']['sheet_ref'])['version'] == expected_version
            validate_schema(out['result']['cells'], compiled_assay_cells_schema(version))
    finally:
        store.close()


def test_custody_exact_admitted_subset_and_changed_values(tmp_path):
    case = Case(tmp_path/'state')
    try:
        binding, ctx, args, out, rows = selected(case, ['product_reference_contrast', 'post_binding_residual_ratio'])
        repo = LiteratureCompiledAssayRepository(case.store, ctx.run_id).v3_projection()
        parent = replace(ctx, episode_id='parent223', role='annotation', path=(('annotation', 'parent223'),),
            assignment={}, received_record_refs=(out['result']['sheet_ref'],))
        repo.receive_cells(parent, rows[:1], 'trusted223')
        assert repo.fact_cells(parent, [out['result']['sheet_ref']], components=[r['component'] for r in rows]) == rows[:1]
        with pytest.raises(ContractError, match='not_received'):
            repo.validate_fact_values(parent, rows[1:])
        changed = deepcopy(rows[:1]); changed[0]['value'] = 999
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_fact_values(parent, changed)
        ref = args['estimates']['product_test']['sheet_ref']
        denied = replace(ctx, received_record_refs=tuple(r for r in ctx.received_record_refs if r != ref))
        attempt = asyncio.run(binding.execute(denied, 'literature.assay.components.populate', args, 'denied223'))
        assert attempt['status'] == 'invalid' and attempt['feedback']['code'] == 'literature_sheet_not_received'
        form = obj({'numbers': compiled_assay_v3_cells_schema()})
        with pytest.raises(ReportBoundaryError, match='subset_mismatch'):
            binding.validate_report(ctx, {'numbers': rows[:1]}, form)
        from gene_annotation_episode.literature_compiled_assay_storage import compiled_assay_cells_schema
        with pytest.raises(ReportBoundaryError, match='projection_version_mismatch'):
            binding.validate_report(ctx, {'numbers': []}, obj({'numbers': compiled_assay_cells_schema()}))
        with pytest.raises(ContractError, match='operation_key_reused'):
            repo.populate(ctx, args, 'common223')
    finally:
        case.store.close()


def test_v3_only_task_and_actual_native_nondetection_meaning(tmp_path, monkeypatch):
    case = Case(tmp_path/'state', 3)
    try:
        binding, ctx, args, out, rows = selected(case, ['estimate_product_test', 'product_reference_contrast'])
        assert rows[0]['value'] == 0 and rows[0]['native_semantics'] == 'reported_nondetection'
        assert rows[1]['value'] is None
        assert not LiteratureCompiledAssayRepository(case.store, ctx.run_id).has_work(ctx)
        # This direct repository fixture has no runtime journal. Its source
        # outcome list is explicitly empty; the separate shared-loop tests use
        # real WorkflowServices and original recorded actions.
        monkeypatch.setattr(binding.services, 'own_outcomes', lambda *a, **k: [])
        state = binding.decision_context(ctx, {})
        state.update(working_state={}, last_local_outcome=out)
        task, steering = render_literature_experimental_prompt(state, 'Evaluate the selected molecular evidence.').split('\n\nSTEERING\n')
        assert COMMON_ASSESSMENT_TASK in task and COMPILED_ASSAY_TASK not in task
        assert 'reported_nondetection' in steering and 'reported_point' not in steering.split('Requested numerical assessment', 1)[1].split('Numerical interpretation', 1)[0]
        assert 'native_nondetection_not_point' in steering
        assert 'source_' not in steering and 'artifact_' not in steering and 'owner_key' not in steering
    finally:
        case.store.close()


def test_covariance_projection_uses_exact_saved_selected_block(tmp_path):
    case = Case(tmp_path/'state')
    try:
        requested = ['product_reference_contrast', 'binding_only_log_residual', 'binding_only_residual_variance']
        args = case.args(requested); data = case.read(args)
        roles = ['product_test', 'product_reference', 'Kd_test', 'Kd_reference']
        first = case.covariance(data, roles, [[1 if i == j else 0 for j in range(4)] for i in range(4)])
        # A larger second block is also sufficient. The first actually selected
        # block's ordering/origin must survive; projection cannot choose anew.
        second_roles = roles[::-1]
        second = case.covariance(data, second_roles, [[1 if i == j else 0 for j in range(4)] for i in range(4)])
        binding, ctx, args, out, rows = selected(case, requested,
            change=lambda a: a.update(covariance_source_refs=[first, second]))
        assert rows[0]['covariance_provenance'] is None
        assert rows[1]['covariance_provenance'] is None
        provenance = rows[2]['covariance_provenance']
        assert provenance['source_ref'] == first and provenance['roles'] == roles
        assert provenance['origin'] == 'synthetic' and provenance['variance_status'] == 'estimated'
        assert 'matrix_exact' not in provenance and rows[2]['conditional_value'] is not None
        assert rows[2]['uncertainty']['covariance_source_ref'] == first
    finally:
        case.store.close()


def test_scoped_context_and_record_aliases_on_all_parent_surfaces(tmp_path):
    case = Case(tmp_path/'state')
    try:
        raw = b'<p>mean5mM; Kd34uM; residual 0.001; 5-fold</p><p>5-methyl-uridine</p>'
        source = case.publish(raw, 'synthetic_scoped_context223')
        case.context = replace(case.context, received_record_refs=(*case.context.received_record_refs, source))
        broad = case.witness(3, raw.index(b'</p>'), source)
        named = case.find('5-methyl-uridine', ref=source)
        def change(args):
            args['assertion']['system'] = broad
            args['assertion']['product_or_ligand'] = named
        binding, ctx, args, out, rows = selected(case, ['product_reference_contrast'], change=change)
        source_hash = hashlib.sha256(case.store.get_artifact(case.store.get(source)['artifact_ref'])).hexdigest()
        assert rows[0]['numerical_scope_implementation_status'] == 'partial_unresolved'
        assert '5-methyl-uridine' in json.dumps(rows[0]['context'])
        assert all(token not in json.dumps(rows[0]['context']) for token in ('mean5mM', 'Kd34uM', '0.001', '5-fold'))
        anchor = {**broad, 'artifact_ref': case.store.get(source)['artifact_ref']}
        anchor.pop('representation')
        alias = {'id': 'reference_synthetic223', 'record_type': 'reference', 'origin': 'tool',
            'reference_type': 'assay', 'source_ref': source, 'label': broad['quote'], 'anchor': anchor}
        base = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'working_state': {'references': [alias]}, 'current_report_basis_refs': [alias['id']]}
        form = {'numbers': rows, 'source_alias': alias['id']}
        history = {'status': 'completed', 'result': {'view': 'records', 'records': [
            {'outcome': out, 'admitted_report': form}]}}
        surfaces = [({**base, 'last_local_outcome': out}, ()),
            ({**base, 'child_reports': [form]}, ()), ({**base, 'current_report_update': form}, ()),
            (base, (history,)), (base, ({'status': 'completed', 'result': form},))]
        for surface_index, (state, lookups) in enumerate(surfaces):
            task, steering = render_literature_experimental_prompt(state, 'Evaluate received functional evidence.', lookup_results=lookups).split('\n\nSTEERING\n')
            assert COMMON_ASSESSMENT_TASK in task
            leaked = [token for token in ('mean5mM', 'Kd34uM', '0.001', '5-fold', alias['id'], source) if token in steering]
            assert not leaked, (surface_index, leaked)
            assert '5-methyl-uridine' in steering
            assert 'unrequested_numerical_scope_unresolved' in steering
        from gene_annotation_episode.literature_reference_parent_prompt import render_reference_evidence_parent_prompt
        state = {**base, 'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'},
            'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': [case.source]}, 'child_reports': [form]}
        prompt = render_reference_evidence_parent_prompt(state, 'Evaluate the reference molecule.')
        assert COMMON_ASSESSMENT_TASK in prompt.split('\n\nSTEERING\n')[0]
        assert '0.001' not in prompt.split('\n\nSTEERING\n')[1]
        assert hashlib.sha256(case.store.get_artifact(case.store.get(source)['artifact_ref'])).hexdigest() == source_hash
    finally:
        case.store.close()


def forbid(*args, **kwargs):
    raise AssertionError('Cold common composition cannot do source/scientific/model/admission work')


def disable_common_science(monkeypatch):
    for module, names in {
        'literature_compiled_assay_inputs': ('read_common_assessment_inputs', '_common_source_estimate', '_common_received_estimate', '_common_covariance'),
        'literature_compiled_assay_calculations': ('populate_common_assessment', '_common_scoped_context'),
        'literature_product_coupling_inputs': ('read_product_coupling_inputs',),
        'literature_product_coupling_calculations': ('populate_product_coupling',),
        'literature_kinetic_inputs': ('read_kinetic_inputs',),
        'literature_kinetic_calculations': ('populate_kinetic_contrast',),
    }.items():
        for name in names:
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbid)
    monkeypatch.setattr(LiteratureCompiledAssayRepository, 'receive_cells', forbid)


def state_hashes(path):
    return {str(f.relative_to(path)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in path.rglob('*') if f.is_file()}


@pytest.mark.parametrize('profile', [None, 'operation_contract_information_v1'], ids=['legacy', 'explicit'])
@pytest.mark.parametrize('alias', [False, True], ids=['literal', 'alias'])
@pytest.mark.parametrize('index', [1, 3], ids=['positive', 'nondetection'])
def test_selected_shared_loop_original_form_and_first_readonly_cold_composition(tmp_path, monkeypatch, profile, alias, index):
    _selected_shared_loop_case(tmp_path, monkeypatch, profile, alias, index)


def _selected_shared_loop_case(tmp_path, monkeypatch, profile, alias, index, *, nested=False):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController, ScriptedProvider
    from test_literature_compiled_assay_185 import readonly
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select
    case = Case(tmp_path/'state', index)
    requested = ['estimate_product_test', 'product_reference_contrast', 'post_binding_residual_ratio', 'binding_only_residual_variance']
    common_args = case.args(requested)
    product_args = {arm: deepcopy(case.product.read(ref)['selection']) for arm, ref in case.product_refs.items()}
    kinetic_args = {kind: deepcopy(case.kinetic.read(ref)['selection']) for kind, ref in case.kin_refs.items()}
    literal = obj({'numbers': compiled_assay_v3_cells_schema(), 'limitation': {'type': 'string', 'enum': ['attribution_unknown']}})
    submitted = obj({'numbers': {'$ref': 'episode-fact:' + NAMESPACE_V3}, 'limitation': {'type': 'string', 'enum': ['attribution_unknown']}}) if alias else literal
    raw_refs = [case.source, case.model_ref]
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': raw_refs,
        REQUESTED_V3: requested, 'requested_product_coupling_components': ['reported_product_activity', 'reported_cofactor_activity'],
        'requested_kinetic_components': ['numerator_parameter', 'denominator_parameter']}
    commission = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
        'goal': 'Determine what the product and binding experiments establish about the studied molecule.',
        'scope': plain(case.context.scope), 'purpose': 'Return requested source comparisons with their conditional and nondetection meanings.',
        'schema_json': json.dumps(submitted), 'initial_report_json': json.dumps({'limitation': 'attribution_unknown'})}, 'report_update': {}}
    if nested:
        commission = deepcopy(commission)
        commission['selection']['assignment'][REQUESTED_V3] = ['product_reference_contrast']
        nested_commission = {'selection': {'kind': 'episode_child', 'role': 'literature_strategy',
            'assignment': {'version': 'strategy_assignment_v1', 'question_context_refs': [], 'prior_search_refs': raw_refs,
                REQUESTED_V3: requested, 'requested_product_coupling_components': ['reported_product_activity', 'reported_cofactor_activity'],
                'requested_kinetic_components': ['numerator_parameter', 'denominator_parameter']},
            'goal': 'Evaluate these experimental endpoint and binding comparisons with their limitations.',
            'scope': plain(case.context.scope), 'purpose': 'Return the selected common numerical components.',
            'schema_json': json.dumps(submitted), 'initial_report_json': json.dumps({'limitation': 'attribution_unknown'})},
            'report_update': {'limitation': 'attribution_unknown'}}
    class FixturePresentedProvider(PresentedProvider):
        async def complete(self, episode_id, *arguments):
            self.active_episode = episode_id
            return await super().complete(episode_id, *arguments)
    provider = FixturePresentedProvider([]) if profile else None
    def receiver_state(inputs):
        return provider.views[provider.active_episode] if profile else inputs
    def response(choice):
        if not profile:
            return choice
        value = deepcopy(choice)
        if value['selection']['kind'] == 'tool':
            value['selection']['arguments'] = json.dumps(value['selection']['arguments'])
        return select(value)
    selected_refs = {}; prompts = []; captured = []
    def work(tool, args, previous=None):
        def choose(inputs):
            inputs = receiver_state(inputs)
            if previous:
                selected_refs[previous] = inputs['last_local_outcome']['result']['sheet_ref']
            prompt = render_literature_experimental_prompt(inputs, 'Evaluate the assigned molecular function evidence.')
            assert COMMON_ASSESSMENT_TASK in prompt.split('\n\nSTEERING\n')[0]
            prompts.append(prompt)
            return response({'selection': {'kind': 'tool', 'tool': tool, 'arguments': args() if callable(args) else args},
                'report_update': {'limitation': 'attribution_unknown'}})
        return choose
    def common():
        args = deepcopy(common_args)
        for arm in ('reference', 'test'):
            for base in ('product', 'reporter'):
                args['estimates'][base + '_' + arm]['sheet_ref'] = selected_refs['product_' + arm]
            for kind in ('kcat', 'Km'):
                args['estimates'][kind + '_' + arm]['sheet_ref'] = selected_refs[kind]
        return args
    def integrate(inputs):
        inputs = receiver_state(inputs)
        form, = inputs['child_reports']; captured.append(deepcopy(form))
        root_nested = nested and len(captured) == 2
        expected = ['product_reference_contrast'] if root_nested else requested
        assert [r['component'] for r in form['numbers']] == expected
        if not root_nested:
            assert form['numbers'][0]['native_semantics'] == ('reported_nondetection' if index == 3 else 'reported_point')
        prompt = render_literature_experimental_prompt(inputs, 'Evaluate returned molecular function evidence.')
        assert COMMON_ASSESSMENT_TASK in prompt.split('\n\nSTEERING\n')[0]
        assert ('reported_nondetection' in prompt.split('\n\nSTEERING\n')[1]) == (index == 3)
        token = b'P450'; start = case.raw.index(token)
        commit = {name: [] for name in case.store.reasoning_schema()['required']}
        commit['source_subjects'] = [{'alias': 'source_molecule223', 'reference_type': 'assay', 'source_ref': case.source, 'label': token.decode(),
            'anchor': {'source_ref': case.source, 'artifact_ref': case.store.get(case.source)['artifact_ref'],
                'start': start, 'end': start + len(token), 'quote': token.decode()}}]
        return response({'selection': {'kind': 'reason', 'commit': commit},
            'report_update': {'limitation': 'attribution_unknown'} if nested and not root_nested else {}})
    script = [response(commission), *([response(nested_commission)] if nested else []),
        work('literature.product_coupling.populate', product_args['reference']),
        work('literature.product_coupling.populate', product_args['test'], 'product_reference'),
        work('literature.kinetic.populate', kinetic_args['kcat'], 'product_test'),
        work('literature.kinetic.populate', kinetic_args['Km'], 'kcat'),
        work('literature.assay.components.populate', common, 'Km'), integrate, *([integrate] if nested else [])]
    if profile:
        provider.script = iter(script)
    else:
        provider = ScriptedProvider(script)
    progress = ScientificFindingProgress(FindingProgressPolicy(1))
    asyncio.run(run_workflow(case.store, ToolRegistry(case.store), provider=provider, run_dir=tmp_path/'run',
        controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 or nested and len(path) == 2 else 5),
        project_credit=progress, initial_known_record_refs=raw_refs,
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, compiled_assay_population=True,
            reference_parent_sources=[case.source], contract_information_profile=profile),),
        binding_definitions={'credit': progress.as_record()},
        **({'decision_protocol': 'decision_exchange_v1'} if profile else {})))
    assert len(captured) == (2 if nested else 1) and len(prompts) == 5
    row = case.store.db.execute('SELECT run_id,episode_id FROM literature_compiled_assay_v3_received').fetchone()
    run_id, episode_id = row
    if nested:
        episode_id, = case.store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=? AND json_array_length(path)=1', (run_id,)).fetchone()
    counts = lambda db: {t: db.execute(f'SELECT count(*) FROM {t} WHERE run_id=?', (run_id,)).fetchone()[0]
                         for t in ('runtime_actions', 'runtime_observations', 'literature_compiled_assay_operations')}
    observations = 9 if nested else 7
    assert counts(case.store.db) == {'runtime_actions': observations, 'runtime_observations': observations, 'literature_compiled_assay_operations': 1}
    original_form = captured[-1]
    descriptors = json.loads(case.store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (run_id,)).fetchone()[0])['episode_bindings']
    ref = original_form['numbers'][0]['sheet_ref']
    repo = LiteratureCompiledAssayRepository(case.store, run_id).v3_projection()
    saved = repo.read(ref)
    allowed = {case.store.get(ref)[name] for name in ('artifact_ref', 'request_ref')}
    receiver = replace(case.context, run_id=run_id, episode_id=episode_id, role='annotation', path=(('annotation', episode_id),),
        assignment={}, received_record_refs=tuple(repo.cell_record_refs(original_form['numbers'])))
    for name, value in [('ORIGINAL_FORM_223.json', original_form), ('ORIGINAL_SCHEMA_223.json', literal),
                        ('ORIGINAL_SHEET_223.json', saved), ('ORIGINAL_DESCRIPTOR_223.json', descriptors)]:
        (tmp_path/name).write_text(json.dumps(value, indent=2) + '\n')
    case.store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); case.store.close()
    before = state_hashes(tmp_path/'state')
    disable_common_science(monkeypatch)
    monkeypatch.setattr(type(provider), 'complete', forbid)
    # The first reopened connection is read-only, before any composer/repository.
    with readonly(tmp_path/'state') as cold:
        original = cold.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'No scientific source/upstream byte access on cold composition'
            return original(reference)
        monkeypatch.setattr(cold, 'get_artifact', saved_only)
        host = SimpleNamespace(store=cold, run_id=run_id, tools=None)
        restored = compose_episode_bindings(WorkflowServices(host), store=cold,
            journal=SimpleNamespace(store=cold, run_id=run_id), execution_backend=None,
            descriptors=descriptors, job_episodes=None, resource_estimator=None, role_credit_bindings={})
        binding, = restored.bindings; host.episode_bindings = EpisodeBindingRegistry(restored.bindings)
        assert binding.received_report_facts(receiver)[NAMESPACE_V3] == original_form['numbers']
        assert binding._compiled_assay_v3_repository().read(ref) == saved
        assert binding._rate_fact_sources()[NAMESPACE_V3]['report_schema'] == literal['properties']['numbers']
        assert counts(cold.db) == {'runtime_actions': observations, 'runtime_observations': observations, 'literature_compiled_assay_operations': 1}
        assert cold.db.total_changes == 0
    assert before == state_hashes(tmp_path/'state')
    (tmp_path/'COLD_PROOF_223.json').write_text(json.dumps({'profile': profile, 'alias': alias, 'index': index, 'nested': nested,
        'original_form_schema_rows_and_descriptor': True, 'read_only_before_composer': True,
        'source_science_model_receive_blocked_before_composer': True, 'changed_rows': 0,
        'ordinary_completed_actions_and_observations': observations, 'selected_common_operations': 1,
        'state_files': before, 'actual_model_execution': False, 'a105_adequacy_claim': False}, indent=2) + '\n')


def test_actual_nested_forwarding_only_returns_intermediate_parents_requested_subset(tmp_path, monkeypatch):
    _selected_shared_loop_case(tmp_path, monkeypatch, None, True, 1, nested=True)


def test_current_data_readers_preserve_actual_original_v1_v2_states(tmp_path, monkeypatch):
    from gene_annotation_episode.episode_bindings import BindingContext
    from test_literature_compiled_assay_185 import readonly
    base = Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001/a105_common_assessment_binding_223'
    original = json.loads((base/'OLD_STATE_BASELINE_001.json').read_text())
    proof = Path(original['proof_directory']); state = proof/'state'
    forms = json.loads((proof/'ORIGINAL_MIXED_FORM_001.json').read_text())
    expected = json.loads((proof/'SAVED_SHEETS_001.json').read_text())
    before = state_hashes(state)
    assert before == original['state_files']
    disable_common_science(monkeypatch)
    from test_literature_compiled_assay_binding_185 import disable_science
    disable_science(monkeypatch)
    with readonly(state) as cold:
        run_id, = cold.db.execute('SELECT run_id FROM runtime_runs').fetchone()
        allowed = {cold.get(forms[name][0]['sheet_ref'])[field]
                   for name in ('old', 'new') for field in ('artifact_ref', 'request_ref')}
        raw = cold.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'Original source/upstream bytes cannot be reread'
            return raw(reference)
        monkeypatch.setattr(cold, 'get_artifact', saved_only)
        actual = []
        for version, name, table in ((1, 'old', 'literature_compiled_assay_received'),
                                     (2, 'new', 'literature_compiled_assay_v2_received')):
            repo = LiteratureCompiledAssayRepository(cold, run_id, version)
            actual.append(repo.read(forms[name][0]['sheet_ref']))
            parent, = cold.db.execute(f'SELECT episode_id FROM {table}').fetchone()
            ctx = BindingContext(run_id, parent, 'annotation', (('annotation', parent),), cold.validate_scope(), {}, {},
                tuple(row['sheet_ref'] for row in forms[name]))
            assert repo.received_cells(ctx) == forms[name]
        assert actual == expected and cold.db.total_changes == 0
        assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
    assert state_hashes(state) == before
    (tmp_path/'OLD_V1_V2_PROOF_223.json').write_text(json.dumps({'original_reader_values_and_forms_unchanged': True,
        'source_science_receive_blocked': True, 'changed_rows': 0, 'state_files_unchanged': True,
        'old_descriptors_not_migrated': True, 'actual_controlled_pre223_state': str(state)}, indent=2) + '\n')


def test_common_dispatch_preserves_legacy_rendering_from_single_pass_iterables():
    from gene_annotation_episode.literature_compiled_assay_render import render_received
    base = Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001/a105_common_assessment_binding_223'
    proof = Path(json.loads((base/'OLD_STATE_BASELINE_001.json').read_text())['proof_directory'])
    rows = json.loads((proof/'ORIGINAL_MIXED_FORM_001.json').read_text())['old']
    def rendered(values):
        parts = []
        render_received(parts, values, section=lambda p, t, c: p.append(t + '\n' + c),
            table=lambda h, r: '\n'.join('|'.join(map(str, row)) for row in r))
        return '\n'.join(parts)
    assert rendered(rows) == rendered(iter(rows))
    assert 'Requested numerical assay sections' in rendered(iter(rows))


@pytest.mark.parametrize('alter', ['request', 'display', 'owner', 'source_metadata'])
def test_saved_tampering_fails_without_repair_calculation(tmp_path, monkeypatch, alter):
    case = Case(tmp_path/'state')
    try:
        binding, ctx, args, out, rows = selected(case, ['product_reference_contrast'])
        repo = LiteratureCompiledAssayRepository(case.store, ctx.run_id).v3_projection()
        ref = out['result']['sheet_ref']; saved = repo.read(ref); original_json = repo._json
        source = case.store.get(ref)
        def corrupted(reference):
            value = deepcopy(original_json(reference))
            if reference == source['request_ref'] and alter == 'request':
                value['components'] = []
            if reference == source['artifact_ref']:
                if alter == 'display': value['sheet']['context'][0]['display_text'] += ' unexpected changed display'
                elif alter == 'owner': value['sheet']['cells'][0]['operand_keys'] = ['changed_owner']
                elif alter == 'source_metadata': value['source_metadata'][args['source_ref']]['version'] = 'changed'
            return value
        # This deliberately controlled decoded-artifact mutation reaches deeper
        # structural checks; real changed bytes fail the outer hash check first.
        monkeypatch.setattr(repo, '_json', corrupted)
        disable_common_science(monkeypatch)
        with pytest.raises(ContractError, match='saved_'):
            repo.read(ref)
    finally:
        case.store.close()


@pytest.mark.parametrize('profile', [None, 'operation_contract_information_v1'])
def test_original_pending_common_alias_uses_frozen_declarations(tmp_path, monkeypatch, profile):
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import Workflow
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime import FixtureController
    from test_runtime_decision_exchanges import select
    case = Case(tmp_path/'state')
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [case.source, case.model_ref], REQUESTED_V3: ['product_reference_contrast']}
    limit = {'type': 'string', 'enum': ['attribution_unknown']}
    literal = obj({'numbers': compiled_assay_v3_cells_schema(), 'limits': limit})
    submitted = obj({'numbers': {'$ref': 'episode-fact:' + NAMESPACE_V3}, 'limits': limit})
    choice = select({'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
        'goal': 'Determine what the selected molecular experiments establish.', 'scope': plain(case.context.scope),
        'purpose': 'Return the requested comparison and scientific limitation.', 'schema_json': json.dumps(submitted),
        'initial_report_json': json.dumps({'limits': 'attribution_unknown'})}, 'report_update': {}})
    provider = PresentedProvider([OSError('Controlled pending223 interruption')])
    workflow = Workflow(case.store, ToolRegistry(case.store), provider, tmp_path/'run', case.context.run_id,
        lambda path, initial: FixtureController(str(path), initial, 2), ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=[case.source, case.model_ref],
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, compiled_assay_population=True,
            reference_parent_sources=[case.source], contract_information_profile=profile),), decision_protocol='decision_exchange_v1')
    root = workflow.build('annotation', 'root', 'Evaluate the experimental reference evidence.', plain(case.context.scope))
    try:
        with pytest.raises(OSError, match='pending223'):
            asyncio.run(root.run_async(workflow.context))
        # Explicitly controlled fixture requests, never actual private provider
        # payloads. Preserve the original declaration through the interruption.
        original = workflow.journal.row('runtime_model_calls', root.source.episode_id, 0)['request']
        monkeypatch.setattr(Workflow, 'report_sources', forbid)
        monkeypatch.setattr(Workflow, 'catalog', forbid)
        monkeypatch.setattr(Workflow, 'action_schema', forbid)
        factory = contracts.registered_schema
        monkeypatch.setattr(contracts, 'registered_schema', forbid)
        schema, declaration = workflow.expanded_contract_form(root.source, choice['response']['selection'], 0, 'literature')
        assert schema == literal
        assert declaration['submitted_schema_json'] == choice['response']['selection']['schema_json']
        assert workflow.journal.row('runtime_model_calls', root.source.episode_id, 0)['request'] == original
        monkeypatch.setattr(contracts, 'registered_schema', factory)
        provider.script = iter([choice]); root.source.calls = 0
        async def choose_only():
            return await root.source.next(SimpleNamespace())
        assert asyncio.run(choose_only()) is not None
        child = json.loads(case.store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0])
        assert child['report_contract']['measurements']['schema'] == literal
        assert case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        case.store.close()
