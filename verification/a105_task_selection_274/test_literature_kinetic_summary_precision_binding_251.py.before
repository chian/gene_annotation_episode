"""Selected synthetic choices and cold custody; no model-backed scientific run."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, validate_form, ReportBoundaryError
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_summary_precision_storage import (
    LiteratureKineticSummaryPrecisionRepository, summary_precision_cells_schema,
    kinetic_operation_schema, COMPONENTS, NAMESPACE, REQUESTED, VIEW, VERSION)
from gene_annotation_episode.literature_kinetic_summary_precision_prompt import KINETIC_SUMMARY_PRECISION_TASK
from gene_annotation_episode.literature_kinetic_model_prompt import KINETIC_MODEL_TASK
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_kinetic_summary_precision_components_248 import synthetic, nonsd_source

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_binding_251'
SELECTED = ['source_mean_standard_error', 'source_reported_sd']


def setup(path, components=SELECTED, case='fully_units_known', nonsd=None, actual_source=False):
    if actual_source:
        pure = OWN.parent/'a105_summary_precision_components_248'
        selection = json.loads((pure/'ACTUAL_SOURCE_SELECTION_PROPOSAL_002.json').read_text())
        pinned = pure/'pin_006/research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242/sources'
        raw = (pinned/'elife-06181-v2.pdf').read_bytes()
        source_text = (pinned/'elife-06181-v2.txt').read_bytes()
        manifest_rows = json.loads((pure/'PIN_MANIFEST_006.json').read_text())['files']
        for name, data in [('elife-06181-v2.pdf', raw), ('elife-06181-v2.txt', source_text)]:
            frozen = next(r for r in manifest_rows if r['path'].endswith('/'+name))
            assert hashlib.sha256(data).hexdigest() == frozen['sha256']
    else:
        selection, read = nonsd_source(nonsd) if nonsd else synthetic(case)
        raw = read('@synthetic248', 'text')['content']
        source_text = raw
    store = Store(path)
    manifest = path/'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    def source(raw, provider, *, artifact=None, parents=(), text=None):
        artifact = artifact or store.artifact(raw)
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': store.artifact(text) if text is not None else artifact, 'request_ref': None, 'version': None,
            'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')['id']
    reference = source(raw, 'retained_public_original248' if actual_source else 'explicit_synthetic_summary251', text=source_text)
    def refs(value):
        if isinstance(value, dict):
            return {k: refs(v) for k, v in value.items()}
        if isinstance(value, list):
            return [refs(v) for v in value]
        return reference if value in ('@synthetic248', '@elife2015AP') else value
    selection = refs(selection)
    context = {name: [] for name in ('organism', 'genotype', 'molecule', 'construct', 'substrate',
        'preparation', 'experiment', 'experimental_system', 'conditions', 'endpoint', 'normalization')}
    args = {'version': 'literature_kinetic_summary_precision_population_v1', 'selection': selection,
        'requested_cells': list(components), 'return_context': context}
    assignment = {'version': 'literature_assignment_v1', 'source_refs': [reference],
        'question_context_refs': [], REQUESTED: list(components)}
    ctx = BindingContext('summary251', 'child251', 'literature', (('literature', 'child251'),),
        store.validate_scope(), assignment, {}, (reference,))
    host = SimpleNamespace(store=store, run_id=ctx.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, reference_parent_sources=[reference])
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return store, ctx, args, binding, source


def selected(store, ctx, args, binding, key='selected251'):
    outcome = asyncio.run(binding.execute(ctx, 'literature.kinetic.populate', args, key))
    assert outcome['status'] == 'completed', outcome
    current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *outcome['record_refs']))
    schema = obj({'numbers': summary_precision_cells_schema()})
    form = form_with_facts({}, schema, binding.facts(current, {'committed_record_refs': outcome['record_refs']}))
    binding.validate_report(current, form, schema)
    return current, outcome, form['numbers']


def forbid(*a, **kw):
    raise AssertionError('Scientific IO/factory/current attestation/receive/write forbidden')


def block_science(monkeypatch):
    from gene_annotation_episode import literature_kinetic_summary_precision_inputs as inputs
    from gene_annotation_episode import literature_kinetic_summary_precision_calculations as calculations
    from gene_annotation_episode import literature_kinetic_summary_precision_storage as storage
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from gene_annotation_episode import literature_kinetic_inputs as legacy
    for module, names in [(inputs, ['read_kinetic_summary_precision_inputs', 'validate_kinetic_summary_precision_extraction',
        'summary_precision_arguments_schema', 'summary_precision_extraction_schema', '_validate_input_relationships']),
        (calculations, ['populate_kinetic_summary_precision', 'validate_kinetic_summary_precision_inputs',
            'summary_precision_inputs_schema', 'summary_precision_sheet_schema']),
        (storage, ['summary_precision_cells_schema', 'summary_precision_operation_schema', '_project_once', '_context_projection']),
        (contracts, ['registered_schema']), (legacy, ['read_kinetic_inputs']),
        (LiteratureKineticSummaryPrecisionRepository, ['populate', 'receive_cells', '_original_implementation'])]:
        for name in names:
            monkeypatch.setattr(module, name, forbid)


def test_exact_reviewed_contracts_and_no_discovery_state(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        before = store.db.total_changes
        assert summary_precision_cells_schema() == json.loads((OWN/'RETURN_ROWS_SCHEMA_001.json').read_text())
        assert kinetic_operation_schema() == json.loads((OWN/'OPERATION_UNION_SCHEMA_002.json').read_text())
        assert REQUESTED in binding.assignment_schema('literature')['properties']
        assert NAMESPACE in binding.fact_sources('literature')
        assert next(r for r in binding.catalog(ctx) if r['name'] == 'literature.kinetic.populate')['input_schema'] == kinetic_operation_schema()
        assert not binding._summary_precision_repository().has_work(ctx)
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_kinetic_summary_precision_operations'").fetchone()
        assert before == store.db.total_changes
        current, out, rows = selected(store, ctx, args, binding)
        assert [r['component'] for r in rows] == SELECTED
        assert rows[0]['cell']['value'] == 6
        assert rows[1]['cell']['value'] == 12
        assert rows[0]['cell']['unit'] == 'per_min'
        assert asyncio.run(binding.execute(ctx, 'literature.kinetic.populate', args, 'selected251')) == out
        saved = binding._summary_precision_repository().read(out['result']['sheet_ref'])
        assert saved['extraction']['selection'] == args['selection']
        assert saved['sheet']['inputs'] == saved['calculation_inputs'] == saved['extraction']['calculation_inputs']
        original_request = json.loads(store.get_artifact(store.get(out['result']['sheet_ref'])['request_ref']))
        assert original_request['arguments'] == args
        assert original_request['components'] == SELECTED
        assert saved['row_templates'] == [{k: v for k, v in r.items() if k != 'sheet_ref'} for r in rows]
    finally:
        store.close()


@pytest.mark.parametrize('components', [[], ['source_mean_interval_confidence_level'], list(reversed(SELECTED))])
def test_exact_empty_and_ordered_roster(tmp_path, components):
    store, ctx, args, binding, _ = setup(tmp_path/'state', components)
    try:
        _, _, rows = selected(store, ctx, args, binding)
        assert [r['component'] for r in rows] == components
        assert all('parameter_native_exact' not in r and 'source_count' not in r for r in rows)
    finally:
        store.close()


def test_explicit_all_thirty_cells_keep_source_scenario_and_component_identities(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state', list(COMPONENTS))
    try:
        args['selection']['scenario'] = {'version': 'a105_summary_precision_scenario_v1',
            'count_rule': 'source_statistical_count', 'stipulated_assumptions': []}
        _, _, rows = selected(store, ctx, args, binding)
        assert [r['component'] for r in rows] == list(COMPONENTS)
        assert len(rows) == 30
        for row in rows:
            assert row['component'] == row['population'].removesuffix('_cells')+'_'+row['cell_name']
            assert row['cell']['formula_code'] == 'summary_precision_'+row['cell_name']
        bad = deepcopy(rows[:1]); bad[0]['population'] = 'scenario_cells'
        with pytest.raises(ContractError): validate_schema(bad, summary_precision_cells_schema())
    finally:
        store.close()


@pytest.mark.parametrize('failure', ['roster', 'source', 'witness', 'field', 'scenario'])
def test_source_roster_and_closed_failure_preflight(tmp_path, failure):
    store, ctx, args, binding, source = setup(tmp_path/'state')
    try:
        if failure == 'roster':
            args['requested_cells'].reverse()
        elif failure == 'source':
            args['selection']['kinetic_selection']['source_ref'] = source(b'alien', 'controlled_unreceived251')
        elif failure == 'witness':
            args['selection']['interpretation']['row_footnote_applicability']['witnesses'][0]['source_ref'] = source(b'alien', 'controlled_unreceived251')
        elif failure == 'field':
            args['made_up'] = True
        else:
            args['selection']['scenario'] = None
            args['requested_cells'] = ['scenario_mean_standard_error']
            ctx = replace(ctx, assignment={**plain(ctx.assignment), REQUESTED: args['requested_cells']})
        out = asyncio.run(binding.execute(ctx, 'literature.kinetic.populate', args, 'invalid251'))
        assert out['status'] == 'invalid' and out['feedback']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_kinetic_summary_precision_operations'").fetchone()
    finally:
        store.close()


@pytest.mark.parametrize('case', ['missing_central_value', 'missing_parameter_unit', 'both_units_missing', 'different_native_time_units'])
def test_partial_source_units_preserve_correct_sd_se_and_count(tmp_path, case):
    components = ['source_reported_parameter', 'source_reported_sd', 'source_mean_variance',
        'source_mean_standard_error', 'source_independent_preparation_count', 'source_statistical_estimator_count']
    store, ctx, args, binding, _ = setup(tmp_path/'state', components, case)
    try:
        _, _, rows = selected(store, ctx, args, binding)
        by_name = {r['cell_name']: r['cell'] for r in rows}
        assert by_name['independent_preparation_count']['value'] == by_name['statistical_estimator_count']['value'] == 4
        if case == 'both_units_missing':
            assert by_name['mean_standard_error']['value'] is None
            assert by_name['mean_standard_error']['unavailable_reason'] == 'source_uncertainty_unit_unavailable'
        else:
            assert by_name['reported_sd']['value'] == 12
            assert by_name['mean_variance']['value'] == 36
            assert by_name['mean_standard_error']['value'] == 6
    finally:
        store.close()


@pytest.mark.parametrize('statistic', ['sem', 'ci'])
def test_non_sd_complete_original_retention_without_inversion(tmp_path, statistic):
    store, ctx, args, binding, _ = setup(tmp_path/'state', ['source_mean_standard_error'], nonsd=statistic)
    try:
        _, out, rows = selected(store, ctx, args, binding)
        assert rows[0]['cell']['unavailable_reason'] == 'reported_statistic_not_sd'
        saved = binding._summary_precision_repository().read(out['result']['sheet_ref'])
        unc = saved['extraction']['kinetic_extraction']['operands']['numerator']['uncertainty']
        assert unc['canonical']['statistic'] == statistic
        assert unc['interval'] is not None if statistic == 'ci' else unc['magnitude'] is not None
        assert '95%' not in json.dumps(rows)
    finally:
        store.close()


@pytest.mark.parametrize('kind', ['unknown', 'conflicting'])
def test_unresolved_dimension_preserves_originals_and_count(tmp_path, kind):
    store, ctx, args, binding, _ = setup(tmp_path/'state', ['source_mean_standard_error', 'source_source_summary_count'])
    try:
        meaning = args['selection']['kinetic_selection']['numerator']['parameter_kind']
        meaning['value'] = kind
        if kind == 'conflicting':
            meaning['witnesses'].append(deepcopy(args['selection']['kinetic_selection']['numerator']['subject']['construct']))
        _, out, rows = selected(store, ctx, args, binding)
        assert rows[0]['cell']['unavailable_reason'] == 'source_parameter_kind_'+kind
        assert rows[0]['cell']['unit'] is None and rows[1]['cell']['value'] == 4
        saved = binding._summary_precision_repository().read(out['result']['sheet_ref'])
        assert saved['extraction']['kinetic_extraction']['operands']['numerator']['uncertainty']['magnitude']['raw_number'] == '0.2'
    finally:
        store.close()


def test_explicit_scenario_never_rewrites_source_conditions(tmp_path):
    components = ['source_mean_standard_error', 'scenario_mean_standard_error', 'source_independent_preparation_count']
    store, ctx, args, binding, _ = setup(tmp_path/'state', components)
    try:
        inter = args['selection']['interpretation']
        inter['sample_sd_n_minus_one'] = {'state': 'unknown', 'witnesses': []}
        args['selection']['scenario'] = {'version': 'a105_summary_precision_scenario_v1',
            'count_rule': 'source_statistical_count', 'stipulated_assumptions': ['sample_sd_n_minus_one']}
        _, out, rows = selected(store, ctx, args, binding)
        assert rows[0]['cell']['value'] is None
        assert rows[1]['cell']['value'] == 6
        assert rows[1]['cell']['qualification'] == 'conditional_on_stipulated_assumptions'
        assert rows[1]['cell']['stipulated_assumptions'] == ['sample_sd_n_minus_one']
        assert rows[2]['cell']['value'] == 4
        assert binding._summary_precision_repository().read(out['result']['sheet_ref'])['calculation_inputs']['assessments']['sample_sd_n_minus_one'] == 'unknown'
    finally:
        store.close()


def test_selected_valid_count_does_not_inherit_unrelated_unknown_extra_count(tmp_path):
    store, ctx, args, binding, source = setup(tmp_path/'state', ['source_mean_standard_error', 'source_statistical_estimator_count'])
    try:
        original_ref = args['selection']['kinetic_selection']['source_ref']
        original = args['selection']['kinetic_selection']['numerator']['uncertainty']['count']
        extra = source(b'', 'controlled_unused_count_alias251', artifact=store.get(original_ref)['artifact_ref'])
        separate = deepcopy(original); separate['witness']['source_ref'] = extra
        args['selection']['interpretation']['statistical_count'] = separate
        ctx = replace(ctx, received_record_refs=(*ctx.received_record_refs, extra))
        _, out, rows = selected(store, ctx, args, binding)
        assert [r['cell']['value'] for r in rows] == [6, 4]
        for row in rows:
            assert 'statistical_count_matches_sd' not in [c['condition'] for c in row['model_conditions']]
            assert extra not in [d['source_ref'] for d in row['dependency_locations']]
        saved = binding._summary_precision_repository().read(out['result']['sheet_ref'])
        assert saved['calculation_inputs']['source_statistical_count']['selector']['witness']['source_ref'] == extra
        assert saved['calculation_inputs']['assessments']['statistical_count_matches_sd'] == 'unknown'
    finally:
        store.close()


@pytest.mark.parametrize('unknown_extra', [False, True])
def test_missing_physical_mapping_conditions_reach_selected_parent_view(tmp_path, unknown_extra):
    store, ctx, args, binding, _ = setup(tmp_path/'state', ['source_statistical_estimator_count', 'source_mean_standard_error'])
    try:
        inter = args['selection']['interpretation']
        inter['source_count_meaning']['value'] = 'physical_preparation_count'
        mapping = ['one_estimate_per_preparation', 'reported_sd_summarizes_counted_preparation_estimates']
        for condition in mapping:
            inter[condition] = {'state': 'unknown', 'witnesses': []}
        if unknown_extra:
            inter['statistical_count'] = deepcopy(args['selection']['kinetic_selection']['numerator']['uncertainty']['count'])
        _, _, rows = selected(store, ctx, args, binding)
        for row in rows:
            assert row['cell']['value'] is None
            assert all({'condition': c, 'state': 'unknown'} in row['model_conditions'] for c in mapping)
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'},
            'working_state': {}, 'child_reports': [{'precision': rows}]}
        text = render_literature_experimental_prompt(state, 'Assess the missing estimator mapping.').split('\n\nSTEERING\n')[1]
        assert all(c+'=unknown' in text for c in mapping)
        assert ('statistical_count_sd_relationship_unknown' if unknown_extra else 'statistical_estimator_count_unknown') in text
    finally:
        store.close()


@pytest.mark.parametrize('technical', [False, True])
def test_receiving_parent_sees_sampling_source_origin_and_approximation(tmp_path, technical):
    names = ['source_reported_parameter', 'source_relative_reported_sd', 'source_mean_standard_error']
    store, ctx, args, binding, _ = setup(tmp_path/'state', names)
    try:
        row = args['selection']['kinetic_selection']['numerator']
        row['qualification']['value'] = 'source_qualified_approximate'
        if technical:
            row['uncertainty']['repetition_basis']['value'] = 'technical_measurements'
            args['selection']['interpretation']['source_count_meaning']['value'] = 'technical_measurement_count'
        _, _, rows = selected(store, ctx, args, binding)
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'},
            'literature_assignment': {}, 'working_state': {}, 'child_reports': [{'precision': rows}]}
        steering = render_literature_experimental_prompt(state, 'Interpret the received precision.').split('\n\nSTEERING\n')[1]
        assert ('technical_measurements' if technical else 'biological_preparations') in steering
        assert ('technical_measurement_count' if technical else 'both_same_count') in steering
        assert 'synthetic_fixture' in steering and 'synthetic' in steering
        assert 'Approximate' in steering and 'true' in steering
        assert rows[0]['cell']['approximate'] and rows[1]['cell']['approximate']
        assert rows[2]['cell']['value'] == 6
    finally:
        store.close()


def test_nonowner_exact_desired_order_intersection_and_private_alias_custody(tmp_path):
    store, ctx, args, binding, source = setup(tmp_path/'state')
    try:
        current, out, rows = selected(store, ctx, args, binding)
        repo = binding._summary_precision_repository(); ref = out['result']['sheet_ref']
        parent = replace(current, episode_id='parent251', path=(('literature', 'parent251'),),
            assignment={**plain(ctx.assignment), REQUESTED: SELECTED[:1]})
        schema = obj({'numbers': summary_precision_cells_schema()})
        binding.received_form_references(parent, {'numbers': rows[:1]}, schema, 'controlled251')
        assert repo.fact_cells(parent, [ref], components=list(reversed(SELECTED))) == rows[:1]
        with pytest.raises(ContractError):
            repo.validate_fact_values(parent, rows)
        metadata = store.get(ref)
        aliases = [source(b'', 'controlled_private_alias251', artifact=metadata[k]) for k in ('artifact_ref', 'request_ref')]
        for target in [ref, *aliases]:
            receiver = replace(parent, received_record_refs=(*parent.received_record_refs, target))
            out = asyncio.run(binding.execute(receiver, 'source.read', {'source_ref': target, 'representation': 'original'}, 'private251'+target))
            assert out['status'] == 'invalid' and out['feedback']['code'] == 'summary_precision_receipt_private'
        public = asyncio.run(binding.execute(parent, 'source.read', {'source_ref': args['selection']['kinetic_selection']['source_ref'], 'representation': 'original'}, 'public251'))
        assert public['status'] == 'completed'
    finally:
        store.close()


def test_narrow_context_rejects_selected_numeric_tokens(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        row = args['selection']['kinetic_selection']['numerator']
        witness = deepcopy(row['measurement']['number']['witness'])
        row['context']['conditions'] = witness
        args['return_context']['conditions'] = [{'start': witness['start'], 'end': witness['end']}]
        out = asyncio.run(binding.execute(ctx, 'literature.kinetic.populate', args, 'broad251'))
        assert out['status'] == 'invalid'
        assert out['feedback']['code'] == 'summary_precision_context_overlaps_numeric_operand'
    finally:
        store.close()


def test_full_task_union_lookup_and_failed_history_no_input_dump(tmp_path):
    from gene_annotation_episode.episode_contract_information import operation_contract_information
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        current, out, rows = selected(store, ctx, args, binding)
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'},
            'literature_assignment': plain(ctx.assignment), 'working_state': {}, 'last_local_outcome': out,
            **binding._summary_precision_display_context(current)}
        task, steering = render_literature_experimental_prompt(state, 'Evaluate requested precision.').split('\n\nSTEERING\n')
        for paragraph in KINETIC_SUMMARY_PRECISION_TASK.strip().split('\n\n'):
            assert paragraph in task
        assert KINETIC_MODEL_TASK not in task
        assert 'source_count' not in steering and '600' not in steering
        lookup = operation_contract_information(catalog=binding.catalog(ctx), operation='literature.kinetic.populate')
        union = render_literature_experimental_prompt(state, 'Select a kinetic interpretation.', lookup_results=[lookup])
        task = union.split('\n\nSTEERING\n')[0]
        assert KINETIC_SUMMARY_PRECISION_TASK in task and KINETIC_MODEL_TASK in task
        history = {'status': 'completed', 'result': {'view': 'records', 'records': [{'selection': {
            'kind': 'tool', 'tool': 'literature.kinetic.populate', 'arguments': args},
            'outcome': {'status': 'invalid', 'result': None, 'feedback': {'code': 'controlled_missing251'}}}]}}
        prompt = render_literature_experimental_prompt({**state, 'last_local_outcome': None}, 'Repair the selected source.', lookup_results=[history])
        assert 'controlled_missing251' in prompt and 'number_start' not in prompt.split('\n\nSTEERING\n')[1]
        assert KINETIC_SUMMARY_PRECISION_TASK in prompt
    finally:
        store.close()


def test_parent_history_admitted_subset_does_not_expand_owner_rows_or_recipe(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        _, out, rows = selected(store, ctx, args, binding)
        history = {'status': 'completed', 'result': {'view': 'records', 'records': [{
            'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate', 'arguments': args},
            'outcome': out, 'admitted_report': {'precision': rows[:1]}}]}}
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'},
            'working_state': {}, 'literature_assignment': {REQUESTED: SELECTED[:1]}}
        text = render_literature_experimental_prompt(state, 'Assess only admitted precision.', lookup_results=[history])
        steering = text.split('\n\nSTEERING\n')[1]
        assert '| mean_standard_error |' in steering and '| reported_sd |' not in steering
        assert 'number_start' not in steering and 'parameter_native_exact' not in steering
    finally:
        store.close()


def test_forged_changed_record_outcome_is_not_replayed(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        _, out, _ = selected(store, ctx, args, binding)
        forged = deepcopy(out); forged['changed_record_refs'] = [ctx.received_record_refs[0]]
        store.db.execute('UPDATE literature_kinetic_summary_precision_operations SET outcome=?', (canonical(forged),))
        with pytest.raises(ContractError): binding._summary_precision_repository().read(out['result']['sheet_ref'])
    finally:
        store.close()


@pytest.mark.parametrize('field', ['row', 'sheet', 'schema', 'source', 'receipt'])
def test_saved_tampering_rejected_without_current_science(tmp_path, monkeypatch, field):
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    try:
        _, out, _ = selected(store, ctx, args, binding)
        repo = binding._summary_precision_repository(); ref = out['result']['sheet_ref']
        artifact = store.get(ref)['artifact_ref']; original = repo._json
        def changed(reference):
            value = original(reference)
            if reference == artifact:
                if field == 'row': value['row_templates'][0]['cell']['value'] = 123
                elif field == 'sheet': value['sheet']['source_cells']['mean_standard_error']['value'] = 123
                elif field == 'schema': value['original_schemas']['rows']['items']['oneOf'].clear()
                elif field == 'source': value['input_artifact_ref'] = 'artifact_'+'0'*64
                else: value['original_implementation']['files'] = {}
            return value
        monkeypatch.setattr(repo, '_json', changed); block_science(monkeypatch)
        with pytest.raises(ContractError): repo.read(ref)
    finally:
        store.close()


@pytest.mark.parametrize('profile,alias,nested,actual_source', [(None, False, False, False), (None, True, False, False), ('operation_contract_information_v1', True, False, False), (None, True, True, False), (None, True, False, True)])
def test_selected_shared_loop_first_readonly_composer_and_observations(tmp_path, monkeypatch, profile, alias, nested, actual_source):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController, ScriptedProvider
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select as action
    from test_literature_compiled_assay_185 import readonly
    import gene_annotation_episode.communication as communication
    requested = ['source_independent_preparation_count', 'source_statistical_estimator_count',
        'source_mean_standard_error', 'scenario_mean_standard_error'] if actual_source else SELECTED
    store, ctx, args, _, _ = setup(tmp_path/'state', requested, actual_source=actual_source); sources = list(ctx.received_record_refs)
    literal = obj({'numbers': summary_precision_cells_schema(), 'limit': {'type': 'string', 'enum': ['systematics_unknown']}})
    submitted = obj({'numbers': {'$ref': 'episode-fact:'+NAMESPACE}, 'limit': literal['properties']['limit']}) if alias else literal
    captured = []
    def response(value):
        if not profile: return value
        value = deepcopy(value)
        if value['selection']['kind'] == 'tool': value['selection']['arguments'] = json.dumps(value['selection']['arguments'])
        return action(value)
    def commission(role, assignment):
        return response({'selection': {'kind': 'episode_child', 'role': role, 'assignment': assignment,
            'goal': 'Determine the selected original-source kinetic summary precision with its sampling qualifications.' if actual_source else 'Determine the selected synthetic kinetic summary precision with its sampling qualifications.',
            'scope': plain(ctx.scope), 'purpose': 'Return exactly requested precision cells and necessary limits.',
            'schema_json': json.dumps(submitted), 'initial_report_json': json.dumps({'limit': 'systematics_unknown'})}, 'report_update': {}})
    def work(inputs):
        view = provider.views[provider.active_episode] if profile else inputs
        assert KINETIC_SUMMARY_PRECISION_TASK in render_literature_experimental_prompt(view, 'Read selected precision.')
        return response({'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate', 'arguments': args}, 'report_update': {'limit': 'systematics_unknown'}})
    def integrate(inputs):
        view = provider.views[provider.active_episode] if profile else inputs
        form, = view['child_reports']; captured.append(deepcopy(form))
        wanted = requested[:1] if nested and len(captured) == 2 else requested
        assert [r['component'] for r in form['numbers']] == wanted
        if actual_source:
            cells = {r['component']: r['cell'] for r in form['numbers']}
            assert cells['source_independent_preparation_count']['value'] == 2
            assert cells['source_statistical_estimator_count']['value'] is None
            assert cells['source_mean_standard_error']['value'] is None
            assert cells['scenario_mean_standard_error']['value'] == pytest.approx(4.242640687119285e-6)
            assert cells['scenario_mean_standard_error']['qualification'] == 'conditional_on_stipulated_assumptions'
            assert all(r['source_kind'] == 'primary_source' for r in form['numbers'])
        prompt = render_literature_experimental_prompt(view, 'Assess received precision.')
        assert KINETIC_SUMMARY_PRECISION_TASK in prompt
        assert 'parameter_native_exact' not in prompt.split('\n\nSTEERING\n')[1]
        commit = {key: [] for key in store.reasoning_schema()['required']}
        witness = args['selection']['kinetic_selection']['numerator']['subject']['construct']
        artifact = store.get(witness['source_ref'])['text_ref']
        commit['source_subjects'] = [{'alias': 'studied_construct251', 'reference_type': 'assay',
            'source_ref': witness['source_ref'], 'label': witness['quote'], 'anchor': {
                'source_ref': witness['source_ref'], 'artifact_ref': artifact,
                'start': witness['start'], 'end': witness['end'], 'quote': witness['quote']}}]
        return response({'selection': {'kind': 'reason', 'commit': commit},
            'report_update': {'limit': 'systematics_unknown'} if nested and len(captured) == 1 else {}})
    outer = plain(ctx.assignment)
    if nested: outer[REQUESTED] = requested[:1]
    script = [commission('literature', outer)]
    if nested: script.append(commission('literature_strategy', {'version': 'strategy_assignment_v1', 'question_context_refs': [], 'prior_search_refs': sources, REQUESTED: requested}))
    script += [work, integrate, *([integrate] if nested else [])]
    class ControlledPresented(PresentedProvider):
        async def complete(self, episode_id, *a):
            self.active_episode = episode_id
            return await super().complete(episode_id, *a)
    provider = ControlledPresented(script) if profile else ScriptedProvider(script)
    progress = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 or nested and len(path) == 2 else 1),
            project_credit=progress, binding_definitions={'credit': progress.as_record()}, initial_known_record_refs=sources,
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=sources, contract_information_profile=profile),),
            **({'decision_protocol': 'decision_exchange_v1'} if profile else {})))
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == (5 if nested else 3)
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_summary_precision_operations').fetchone()[0] == 1
        run_id, parent = store.db.execute('SELECT run_id,episode_id FROM literature_kinetic_summary_precision_received ORDER BY rowid DESC LIMIT 1').fetchone()
        original = captured[-1]; ref = original['numbers'][0]['sheet_ref']
        repo = LiteratureKineticSummaryPrecisionRepository(store, run_id); saved = repo.read(ref)
        descriptors = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
        allowed = {store.get(ref)[k] for k in ('artifact_ref', 'request_ref')}
        receiver = replace(ctx, run_id=run_id, episode_id=parent, role='annotation', path=(('annotation', parent),),
            assignment={}, received_record_refs=tuple(repo.cell_record_refs(original['numbers'])))
        for name, value in [('ORIGINAL_FORM_251.json', original), ('ORIGINAL_SCHEMA_251.json', literal),
                ('ORIGINAL_SHEET_251.json', saved), ('ORIGINAL_DESCRIPTOR_251.json', descriptors)]:
            (tmp_path/name).write_text(json.dumps(value, indent=2)+'\n')
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
        before = {str(p.relative_to(tmp_path/'state')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'state').rglob('*') if p.is_file()}
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
            assert binding.received_report_facts(receiver)[NAMESPACE] == original['numbers']
            assert binding._summary_precision_repository().read(ref) == saved
            validate_form(original, literal, lambda ref, namespace: True)
            assert communication._compiled_schema_content.cache_info().currsize > 0
            assert cold.db.total_changes == 0
        after = {str(p.relative_to(tmp_path/'state')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'state').rglob('*') if p.is_file()}
        assert before == after
    finally:
        try: store.close()
        except Exception: pass


@pytest.mark.parametrize('profile', [None, 'operation_contract_information_v1'])
def test_original_pending_alias_first_cold_compose_no_new_factories(tmp_path, monkeypatch, profile):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from test_runtime import FixtureController
    from test_contract_information_runtime_059 import PresentedProvider
    from test_literature_compiled_assay_185 import readonly
    import gene_annotation_episode.communication as communication
    store, ctx, _, _, _ = setup(tmp_path/'state'); sources = list(ctx.received_record_refs)
    literal = obj({'numbers': summary_precision_cells_schema()})
    alias = obj({'numbers': {'$ref': 'episode-fact:'+NAMESPACE}})
    provider = PresentedProvider([OSError('Controlled pending251 interruption')])
    workflow = Workflow(store, ToolRegistry(store), provider, tmp_path/'run', ctx.run_id,
        lambda path, initial: FixtureController(str(path), initial, 2), ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=sources, episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=sources, contract_information_profile=profile),), decision_protocol='decision_exchange_v1')
    root = workflow.build('annotation', 'root', 'Evaluate the selected synthetic precision.', plain(ctx.scope))
    with pytest.raises(OSError, match='pending251'): asyncio.run(root.run_async(workflow.context))
    episode = root.source.episode_id
    # This is this explicitly controlled fixture's original request only.
    raw = workflow.journal.row('runtime_model_calls', episode, 0)['request']
    descriptors = [workflow.episode_bindings.for_role('literature').as_record()]
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
    block_science(monkeypatch)
    for name in ('report_sources', 'catalog', 'action_schema'): monkeypatch.setattr(Workflow, name, forbid)
    communication._compiled_schema_content.cache_clear()
    with readonly(tmp_path/'state') as cold:
        monkeypatch.setattr(cold, 'get_artifact', forbid)
        host = SimpleNamespace(store=cold, run_id=ctx.run_id, tools=None)
        compose_episode_bindings(WorkflowServices(host), store=cold, journal=SimpleNamespace(store=cold, run_id=ctx.run_id),
            execution_backend=None, descriptors=descriptors, job_episodes=None, resource_estimator=None, role_credit_bindings={})
        actual = cold.db.execute('SELECT request FROM runtime_model_calls WHERE episode_id=? AND call_index=0', (episode,)).fetchone()[0]
        assert actual == raw
        if profile is None:
            expanded = contracts.expand_numerical_form(json.dumps(alias), child_role='literature', saved=json.loads(actual))
        else:
            from gene_annotation_episode.episode_contract_information import expand_fact_form
            record = Workflow.validate_contract_information(None, json.loads(actual))
            typed = {role: {name: row for name, row in rows.items() if 'report_schema' in row} for role, rows in record['fact_sources_by_role'].items()}
            expanded = expand_fact_form(json.dumps(alias), child_role='literature', facts_by_role=typed, permitted_child_roles=record['permitted_child_roles'])
        assert expanded['expanded_schema'] == literal
        assert cold.db.total_changes == 0
        assert not cold.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_kinetic_summary_precision_operations'").fetchone()


def test_legacy_selected_kinetic_request_result_and_cold_unchanged(tmp_path, monkeypatch):
    from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, kinetic_cells_schema
    from test_literature_compiled_assay_185 import readonly
    store, ctx, args, binding, _ = setup(tmp_path/'state')
    legacy = args['selection']['kinetic_selection']
    ctx = replace(ctx, assignment={**plain(ctx.assignment), 'requested_kinetic_components': ['numerator_parameter']})
    try:
        out = asyncio.run(binding.execute(ctx, 'literature.kinetic.populate', legacy, 'legacy251'))
        assert out['status'] == 'completed', out
        assert isinstance(out['result']['cells'], dict) and out['result']['cells']['numerator_parameter']['value'] == 600
        ref = out['result']['sheet_ref']; repo = LiteratureKineticRepository(store, ctx.run_id)
        saved = repo.read(ref)
        original = repo.project_cells([ref], permitted_record_refs=[ref], components=['numerator_parameter'])
        assert original[0]['numerator']['uncertainty_values']['magnitude'] == 12
        allowed = {store.get(ref)[k] for k in ('artifact_ref', 'request_ref')}
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
        from gene_annotation_episode import literature_kinetic_storage as legacy_storage
        monkeypatch.setattr(legacy_storage, 'read_kinetic_inputs', forbid)
        monkeypatch.setattr(legacy_storage, 'populate_kinetic_contrast', forbid)
        with readonly(tmp_path/'state') as cold:
            get = cold.get_artifact
            def saved_only(r): assert r in allowed; return get(r)
            monkeypatch.setattr(cold, 'get_artifact', saved_only)
            reopened = LiteratureKineticRepository(cold, ctx.run_id)
            assert reopened.read(ref) == saved
            assert reopened.project_cells([ref], permitted_record_refs=[ref], components=['numerator_parameter']) == original
            assert cold.db.total_changes == 0
    finally:
        try: store.close()
        except Exception: pass


def test_original_source_narrow_identity_context_survives_parent_view_and_cold(tmp_path, monkeypatch):
    from test_literature_compiled_assay_185 import readonly
    names = ['source_independent_preparation_count', 'source_statistical_estimator_count',
        'source_mean_standard_error', 'scenario_mean_standard_error']
    store, ctx, args, binding, _ = setup(tmp_path/'state', names, actual_source=True)
    subject = args['selection']['kinetic_selection']['numerator']['subject']
    for name in ('molecule', 'construct'):
        witness = subject[name]
        args['return_context'][name] = [{'start': witness['start'], 'end': witness['end']}]
    current, out, rows = selected(store, ctx, args, binding)
    ref = out['result']['sheet_ref']; repo = binding._summary_precision_repository()
    saved = repo.read(ref); schema = obj({'precision': summary_precision_cells_schema()})
    for name in ('molecule', 'construct'):
        assert rows[0]['source_context'][name]['fragments'][0]['text'] == subject[name]['quote']
    parent_state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
        'aspect': 'source_experimental_evidence'}, 'working_state': {}, 'child_reports': [{'precision': rows}]}
    text = render_literature_experimental_prompt(parent_state, 'Assess the returned source precision.').split('\n\nSTEERING\n')[1]
    assert subject['molecule']['quote'] in text and subject['construct']['quote'] in text
    assert 'primary_source' in text and 'physical_preparation_count' in text
    for name, value in [('ACTUAL_SOURCE_OPERATION_ARGUMENTS_012.json', args),
            ('ACTUAL_SOURCE_SELECTED_RETURN_012.json', {'precision': rows}),
            ('ACTUAL_SOURCE_SAVED_SHEET_012.json', saved)]:
        (tmp_path/name).write_text(json.dumps(value, indent=2)+'\n')
    allowed = {store.get(ref)[key] for key in ('artifact_ref', 'request_ref')}
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
    block_science(monkeypatch)
    with readonly(tmp_path/'state') as cold:
        get = cold.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'Original scientific bytes forbidden on first cold read'
            return get(reference)
        monkeypatch.setattr(cold, 'get_artifact', saved_only)
        reopened = LiteratureKineticSummaryPrecisionRepository(cold, ctx.run_id)
        assert reopened.read(ref) == saved
        assert reopened.project_cells([ref], permitted_record_refs=current.received_record_refs, components=names) == rows
        validate_form({'precision': rows}, schema, lambda reference, namespace: True)
        assert cold.db.total_changes == 0
