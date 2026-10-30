"""Controlled selected A105 component custody; no configured model science."""
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

from gene_annotation_episode.communication import ReportBoundaryError, plain, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_product_coupling_storage import (
    LiteratureProductCouplingRepository, product_coupling_cells_schema, COMPONENTS, NAMESPACE, REQUESTED, VIEW,
)
from gene_annotation_episode.literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episode_contract_information import return_contract_information, operation_contract_information
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_product_coupling_212 import Source, original

REQUEST = ['product_per_cofactor', 'productive_fraction', 'reported_coupling_percent',
    'reconstructed_product_activity', 'productive_fraction_variance']
FORM = obj({'numbers': product_coupling_cells_schema()})


def rebind(value, references):
    if isinstance(value, dict):
        return {name: rebind(child, references) for name, child in value.items()}
    if isinstance(value, list):
        return [rebind(child, references) for child in value]
    return references.get(value, value) if isinstance(value, str) else value


def setup(path, *, requested=REQUEST, primary=None, covariance=False, scale=None, source_fixture=None):
    if primary is not None:
        source, args, _ = original(primary)
    else:
        source = source_fixture or Source(product=scale or '2', cofactor=scale or '4'); args = source.args()
        args['context']['product_conditions'] = source.witness('pH7.4')
    if covariance:
        source.covariance(args)
    store = Store(path)
    manifest = store.path/'empty-inputs.json'; manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    refs = {}
    def publish(old, raw, provider):
        artifact = store.artifact(raw, 'application/xml' if raw.startswith(b'<') else 'application/json')
        row = store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
        refs[old] = row['id']
    publish(source.reference, source.content, 'retained_207' if primary is not None else 'synthetic_coupling218')
    for ref, extra in source.extra.items():
        publish(ref, extra['content'], 'synthetic_covariance218')
    args = rebind(args, refs)
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [refs[source.reference]], REQUESTED: list(requested)}
    ctx = BindingContext('coupling218', 'child218', 'literature', (('literature', 'child218'),),
        store.validate_scope(), assignment, {}, tuple(refs.values()))
    return store, ctx, args


def binding_for(store, context, **configuration):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, **configuration)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def populated(store, ctx, args):
    repo = LiteratureProductCouplingRepository(store, ctx.run_id)
    out = repo.populate(ctx, args, 'selected_coupling')
    current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *out['record_refs']))
    return repo, out, current


def test_native_source_and_exact_scoped_saved_views(tmp_path):
    store, ctx, args = setup(tmp_path, covariance=True)
    with store:
        repo, out, current = populated(store, ctx, args)
        rows = out['result']['cells']; assert [r['component'] for r in rows] == REQUEST
        assert rows[0]['value'] == .5 and rows[1]['value'] == .5
        assert all(row['source_value'] is None for row in rows if row['component'] != 'reported_coupling_percent')
        assert all(row['reaction_account'] is None for row in rows if row['component'] not in ('productive_fraction', 'productive_fraction_variance'))
        covariance = rows[-1]['covariance']
        assert covariance['origin'] == 'synthetic' and covariance['variance_status'] == 'estimated'
        assert covariance['measurement_keys'] == rows[0]['input_measurement_keys']
        assert 'matrix_exact' not in json.dumps(rows) and 'native_exact_value' not in json.dumps(rows)
        assert repo.fact_cells(current, out['record_refs'], components=COMPONENTS) == rows
        assert repo.populate(ctx, args, 'selected_coupling') == out
        assert repo.read(out['result']['sheet_ref'])['sheet']['cells']['reported_product_activity']['value'] == 2
        validate_form({'numbers': rows}, FORM, lambda ref, namespace: bool(store.get(ref)))
        assert not store.list('assessment') and not store.list('observation')


@pytest.mark.parametrize('primary', [1, 3], ids=['positive', 'nondetection'])
def test_retained207_native_and_conditional_qualification_survive(tmp_path, primary):
    store, ctx, args = setup(tmp_path, primary=primary, requested=COMPONENTS)
    with store:
        repo, out, _ = populated(store, ctx, args); cells = {r['component']: r for r in out['result']['cells']}
        assert cells['reported_cofactor_activity']['value'] == (216 if primary == 1 else 427)
        if primary == 1:
            assert cells['product_per_cofactor']['exact_value'] == {'numerator': '23', 'denominator': '54'}
            assert cells['productive_fraction']['value'] is None and cells['productive_fraction']['conditional_value'] == pytest.approx(23/54)
        else:
            assert cells['reported_product_activity']['value'] == 0
            assert cells['reported_product_activity']['native_measurement_semantics'] == 'reported_nondetection'
            assert cells['product_per_cofactor']['value'] is None and cells['productive_fraction']['conditional_value'] is None
        assert cells['reconstructed_product_activity']['contribution_key'] == cells['reported_product_activity']['contribution_key']
        assert repo.read(out['result']['sheet_ref'])['extraction']['relationships']['molecular_attribution']['value'] == 'unknown'


def test_default_empty_catalog_no_state_and_possession(tmp_path):
    store, ctx, args = setup(tmp_path, requested=[])
    with store:
        binding = binding_for(store, ctx)
        assert 'literature.product_coupling.populate' in {r['name'] for r in binding.catalog(ctx)}
        assert 'product_coupling_population' not in binding.as_record()['configuration']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_product_coupling_operations'").fetchone()
        out = asyncio.run(binding.execute(replace(ctx, received_record_refs=()), 'literature.product_coupling.populate', args, 'missing'))
        assert out['feedback']['code'] == 'literature_source_not_received'
        out = asyncio.run(binding.execute(ctx, 'literature.product_coupling.populate', args, 'empty'))
        assert out['status'] == 'completed' and out['result']['cells'] == []
        repo = binding._product_coupling_repository()
        with pytest.raises(ContractError, match='component_not_selected'):
            repo.project_cells(out['record_refs'], permitted_record_refs=out['record_refs'], components=['productive_fraction'])


def test_forwarding_keeps_only_admitted_subset_and_duplicate_rejection(tmp_path):
    store, ctx, args = setup(tmp_path)
    with store:
        repo, out, current = populated(store, ctx, args)
        chosen = out['result']['cells'][:1]
        parent = replace(current, role='annotation', episode_id='parent218', path=(('annotation', 'parent218'),), assignment={})
        repo.receive_cells(parent, chosen, 'trusted_fixture_admission')
        assert repo.received_cells(parent) == chosen
        assert repo.fact_cells(parent, out['record_refs'], components=COMPONENTS) == chosen
        with pytest.raises(ContractError, match='not_received'):
            repo.validate_fact_values(parent, out['result']['cells'][1:])
        repo.receive_cells(parent, chosen, 'trusted_fixture_admission')
        with pytest.raises(ContractError, match='duplicate'):
            repo.receive_cells(parent, [*chosen, *chosen], 'duplicate')


@pytest.mark.parametrize('mutation', ['omitted', 'value', 'conditional', 'unrequested', 'model', 'covariance', 'shared_key'])
def test_exact_requested_roster_and_actual_saved_values_are_required(tmp_path, mutation):
    store, ctx, args = setup(tmp_path, covariance=True)
    with store:
        repo, out, current = populated(store, ctx, args); rows = deepcopy(out['result']['cells'])
        if mutation == 'omitted': rows.pop()
        elif mutation == 'value': rows[0]['value'] = 123
        elif mutation == 'conditional': rows[1]['conditional_value'] = .7
        elif mutation == 'unrequested': rows[0]['component'] = 'calculated_coupling_percent'
        elif mutation == 'model': rows[1]['reaction_account']['direction'] = 'product_per_cofactor'
        elif mutation == 'covariance': rows[-1]['covariance']['variance_status'] = 'known'
        else: rows[3]['contribution_key'] = 'invented_contribution'
        with pytest.raises((ContractError, ReportBoundaryError)):
            binding_for(store, ctx).validate_report(current, {'numbers': rows}, FORM)


@pytest.mark.parametrize('mutation', ['signature', 'outcome_value', 'outcome_omission', 'run', 'source_metadata'])
def test_original_operation_request_outcome_and_source_authentication(tmp_path, mutation):
    store, ctx, args = setup(tmp_path)
    with store:
        repo, out, _ = populated(store, ctx, args); ref = out['result']['sheet_ref']
        if mutation == 'signature': store.db.execute("UPDATE literature_product_coupling_operations SET signature='{}'")
        elif mutation == 'run': repo = LiteratureProductCouplingRepository(store, 'different_run')
        elif mutation == 'source_metadata':
            raw = json.loads(store.db.execute('SELECT data FROM records WHERE id=?', (args['source_ref'],)).fetchone()[0])
            raw['provider'] = 'changed_provider'
            store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(raw), args['source_ref']))
        else:
            changed = deepcopy(out)
            if mutation == 'outcome_value': changed['result']['cells'][0]['value'] = 99
            else: changed['result']['cells'].pop()
            store.db.execute('UPDATE literature_product_coupling_operations SET outcome=?', (canonical(changed),))
        with pytest.raises(ContractError): repo.read(ref)


def test_broad_context_and_same_artifact_alias_mask_unrequested_measurements(tmp_path):
    store, ctx, args = setup(tmp_path, requested=['productive_fraction'])
    with store:
        source = store.get(args['source_ref']); raw = store.get_artifact(source['artifact_ref'])
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        value.update(provider='same_artifact_alias218', text_ref=source['artifact_ref'])
        alias = store.put('source', value, origin='caller')['id']
        args['context']['experiment'] = {'source_ref': alias, 'representation': 'text',
            'start': raw.index(b'<table>'), 'end': raw.index(b'</table>')+len(b'</table>'),
            'quote': raw[raw.index(b'<table>'):raw.index(b'</table>')+len(b'</table>')].decode()}
        args['context']['normalization'] = {**args['quantities']['cofactor']['number']['witness'],
            'source_ref': alias, 'representation': 'text'}
        current = replace(ctx, received_record_refs=(*ctx.received_record_refs, alias))
        repo, out, _ = populated(store, current, args); row, = out['result']['cells']
        assert row['source_meanings']['experiment']['status'] == 'numerical_scope_unresolved'
        assert row['source_meanings']['normalization']['display_text'] == '[unrequested numerical operand]'
        assert row['source_meanings']['product_conditions']['display_text'] == 'pH7.4'
        assert row['source_value'] is None and row['source_exact_value'] is None
        assert repo.read(out['result']['sheet_ref'])['extraction']['context']['experiment']['value'] == args['context']['experiment']['quote']


@pytest.mark.parametrize('surface', ['own', 'child', 'current', 'history', 'parent_history', 'operation_lookup', 'return_lookup', 'parent_direct'])
def test_recurring_task_and_scoped_text_on_all_actual_surfaces(tmp_path, surface):
    store, ctx, args = setup(tmp_path, requested=['product_per_cofactor'])
    with store:
        repo, out, _ = populated(store, ctx, args); rows = out['result']['cells']
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'goal': {'objective': 'Evaluate the supplied product and cofactor experiments.'}, 'requested_form': FORM}
        lookups = []
        if surface == 'own': state['last_local_outcome'] = out
        elif surface == 'child': state['child_reports'] = [{'numbers': rows}]
        elif surface == 'current': state['current_report_update'] = {'numbers': rows}
        elif surface in ('history', 'parent_history'):
            record = {'outcome': out}
            if surface == 'parent_history': record['admitted_report'] = {'numbers': rows}
            lookups = [{'status': 'completed', 'result': {'view': 'records', 'records': [record]}}]
        elif surface == 'parent_direct':
            state['literature_experimental_work']['aspect'] = 'reference_evidence_parent'
            state['reference_evidence_parent'] = {'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]}
            state['child_reports'] = [{'numbers': rows}]
        else:
            state['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
            if surface == 'operation_lookup':
                lookups = [operation_contract_information(catalog=_population_catalog(), operation='literature.product_coupling.populate')]
            else:
                lookups = [return_contract_information(facts_by_role={'literature': {NAMESPACE: {'type': 'array',
                    'meaning': 'Requested endpoint coupling components.', 'report_schema': product_coupling_cells_schema()}}},
                    permitted_child_roles=['literature'], role='literature', source=NAMESPACE)]
        prompt = render_literature_experimental_prompt(state, 'Examine the selected experiment.', lookup_results=lookups)
        task, steering = prompt.split('\n\nSTEERING\n', 1)
        assert task.count(PRODUCT_COUPLING_TASK) == 1 and PRODUCT_COUPLING_TASK not in steering
        assert 'conditional_exact_value' not in task
        if surface not in ('operation_lookup', 'return_lookup'):
            assert 'Requested product and cofactor components' in steering
            assert 'source measurement' in steering
            assert out['result']['sheet_ref'] not in steering
            assert rows[0]['input_measurement_keys'][0] not in steering
        if surface == 'parent_direct':
            direct = render_reference_evidence_parent_prompt(state, 'Evaluate received endpoint evidence.')
            assert direct.split('\n\nSTEERING\n', 1)[0].count(PRODUCT_COUPLING_TASK) == 1


@pytest.mark.parametrize('scale', ['1e400', '1e-400'])
def test_exact_rational_range_survives_typed_return_and_render(tmp_path, scale):
    store, ctx, args = setup(tmp_path, scale=scale, requested=['reported_product_activity', 'product_per_cofactor'])
    with store:
        _, out, _ = populated(store, ctx, args); rows = out['result']['cells']
        assert rows[0]['value'] is None and rows[0]['exact_value'] is not None and rows[1]['value'] == 1
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'last_local_outcome': out}
        text = render_literature_experimental_prompt(state, 'Evaluate native activity.')
        exact = rows[0]['exact_value']; shown = exact['numerator'] if exact['denominator'] == '1' else exact['numerator']+'/'+exact['denominator']
        assert shown in text


def test_exact_closed_registered_schema_cannot_be_loosened():
    form = deepcopy(FORM); form['properties']['numbers']['items']['properties']['source_value']['type'] = 'number'
    with pytest.raises(ReportBoundaryError, match='registered source'): validate_closed_schema(form)


@pytest.mark.parametrize('case', ['unknown_model', 'unknown_link', 'incompatible_link', 'uncertain_model'])
def test_scientific_partials_survive_saved_typed_return(tmp_path, case):
    store, ctx, args = setup(tmp_path, covariance=True,
        requested=['product_per_cofactor', 'productive_fraction', 'productive_fraction_variance'])
    with store:
        raw = store.get_artifact(store.get(args['source_ref'])['artifact_ref'])
        def witness(text):
            start = raw.index(text.encode())
            return {'source_ref': args['source_ref'], 'representation': 'original', 'start': start,
                'end': start+len(text.encode()), 'quote': text}
        if case == 'unknown_model':
            args['nu_cofactor_per_product'].update(status='unknown', exact_value=None, witnesses=[])
        elif case == 'uncertain_model':
            args['nu_cofactor_per_product'].update(status='uncertain_model', exact_value={'numerator': '2', 'denominator': '1'},
                witnesses=[witness('Uncertain stoichiometry estimate')])
        elif case == 'unknown_link':
            args['relationships']['same_preparation'] = {'value': 'unknown', 'witnesses': []}
        else:
            args['relationships']['same_preparation'] = {'value': 'different', 'witnesses': [witness('Different preparation')]}
        repo, out, current = populated(store, ctx, args); rows = out['result']['cells']; eta = rows[1]
        assert rows[0]['value'] == .5 and eta['value'] is None
        if case in ('unknown_model', 'incompatible_link'): assert eta['conditional_value'] is None
        elif case == 'unknown_link': assert eta['conditional_value'] == .5
        else:
            assert eta['conditional_value'] == 1
            assert rows[2]['value'] is None and rows[2]['conditional_value'] is not None
            assert 'conditional_variance_term_excludes_nu_variance_and_covariance' in rows[2]['assumptions']
        assert rows[1]['relationships']['molecular_attribution']['value'] == 'unknown'
        assert repo.fact_cells(current, out['record_refs'], components=COMPONENTS) == rows
        binding_for(store, ctx).validate_report(current, {'numbers': rows}, FORM)


def test_unrequested_model_coefficient_hidden_in_metadata_and_generic_alias_record(tmp_path):
    text = 'Explicit reaction account coefficient 37 cofactor per product.'
    fixture = Source(content=Source().content+('<p>'+text+'</p>').encode())
    store, ctx, args = setup(tmp_path, source_fixture=fixture, requested=['reported_cofactor_activity'])
    with store:
        raw = fixture.content; start = raw.index(text.encode())
        witness = {'source_ref': args['source_ref'], 'representation': 'original', 'start': start,
            'end': start+len(text.encode()), 'quote': text}
        args['nu_cofactor_per_product'].update(exact_value={'numerator': '37', 'denominator': '1'}, witnesses=[witness])
        args['context']['experiment'] = witness
        repo, out, _ = populated(store, ctx, args); row, = out['result']['cells']
        assert row['reaction_account'] is None
        assert '37' not in row['source_meanings']['experiment']['display_text']
        artifact = store.get(args['source_ref'])['artifact_ref']
        record = store.put('reference', {'reference_type': 'literature_result', 'source_ref': args['source_ref'],
            'accession': 'synthetic_numeric_model218', 'label': text, 'sequence_ref': None, 'molecule': None,
            'length': None, 'term_refs': [], 'context_refs': [], 'anchor': {
                'source_ref': args['source_ref'], 'artifact_ref': artifact, 'start': start,
                'end': start+len(text.encode()), 'quote': text}}, origin='tool')
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'child_reports': [{'numbers': [row]}], 'working_state': {'references': [record]},
            'current_report_basis_refs': [record['id']]}
        steering = render_literature_experimental_prompt(state, 'Evaluate only the requested cofactor report.').split('\n\nSTEERING\n', 1)[1]
        assert text not in steering and '37' not in steering


def test_unknown_table_statistics_redacted_without_losing_nonnumeric_source_meaning(tmp_path):
    fixture = Source(content=Source().content.replace(b'</tbody>', b'<tr><td>9.123e123</td></tr></tbody>'))
    store, ctx, args = setup(tmp_path, source_fixture=fixture, requested=['productive_fraction'])
    with store:
        raw = fixture.content; start = raw.index(b'<table>'); end = raw.index(b'</table>')+len(b'</table>')
        args['context']['experiment'] = {'source_ref': args['source_ref'], 'representation': 'original',
            'start': start, 'end': end, 'quote': raw[start:end].decode()}
        _, out, _ = populated(store, ctx, args)
        meaning = out['result']['cells'][0]['source_meanings']['experiment']
        assert meaning['status'] == 'numerical_scope_unresolved'
        assert '9.123' not in meaning['display_text'] and 'e123' not in meaning['display_text']
        assert 'Product formation' in meaning['display_text'] and 'Cofactor consumption' in meaning['display_text']


def test_empty_received_covariance_preserves_point_partials_and_saved_read(tmp_path):
    store, ctx, args = setup(tmp_path, requested=['product_per_cofactor', 'product_per_cofactor_variance'])
    with store:
        artifact = store.artifact(b'', 'application/json')
        covariance = store.put('source', {'provider': 'synthetic_empty_covariance218', 'accession': None,
            'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='caller')['id']
        args['covariance_source_ref'] = covariance
        ctx = replace(ctx, received_record_refs=(*ctx.received_record_refs, covariance))
        repo, out, _ = populated(store, ctx, args); point, variance = out['result']['cells']
        assert point['value'] == .5 and variance['value'] is None
        assert variance['covariance']['unavailable_reason'] == 'covariance_json_invalid'
        repo.read(out['result']['sheet_ref'])


@pytest.mark.parametrize('field', ['uncertainty', 'product_conditions'])
@pytest.mark.parametrize('statistic', ['SD 5 µM', 'mean 5 mM'])
def test_statistic_with_concentration_unit_is_never_a_condition_exception(tmp_path, field, statistic):
    fixture = Source(content=Source().content+('<p>'+statistic+'</p><p>37 C</p>').encode())
    store, ctx, args = setup(tmp_path, source_fixture=fixture, requested=['productive_fraction'])
    with store:
        raw = fixture.content
        def witness(text):
            start = raw.index(text.encode()); return {'source_ref': args['source_ref'], 'representation': 'original',
                'start': start, 'end': start+len(text.encode()), 'quote': text}
        args['context'][field] = witness(statistic)
        args['context']['cofactor_conditions'] = witness('37 C')
        args['relationships']['molecular_attribution'] = {'value': 'mixed_or_unresolved', 'witnesses': [witness(statistic)]}
        repo, out, _ = populated(store, ctx, args); row, = out['result']['cells']
        assert row['source_meanings'][field]['status'] == 'numerical_scope_unresolved'
        assert '5' not in row['source_meanings'][field]['display_text']
        assert '5' not in row['relationships']['molecular_attribution']['support'][0]['display_text']
        assert row['source_meanings']['cofactor_conditions']['display_text'] == '37 C'
        assert row['source_meanings']['product_conditions']['display_text'] == ('pH7.4' if field != 'product_conditions'
            else row['source_meanings'][field]['display_text'])
        repo.read(out['result']['sheet_ref'])


@pytest.mark.parametrize('component', ['reported_product_activity', 'productive_fraction'])
@pytest.mark.parametrize('statistic', ['mean 5mM', 'mean5mM', 'SD 5uM', '5mM', '5-fold', '5-10'])
def test_new_policy_preserves_chemical_locant_and_constructs_withholds_attached_statistics(tmp_path, component, statistic):
    chemical = '5-exo-hydroxycamphor'
    text = chemical+'; P450cam T252N/V253T; '+statistic
    fixture = Source(content=Source().content+('<p>'+text+'</p><p>37 C</p>').encode())
    store, ctx, args = setup(tmp_path, source_fixture=fixture, requested=[component])
    with store:
        raw = fixture.content
        def witness(token):
            start = raw.index(token.encode()); return {'source_ref': args['source_ref'], 'representation': 'original',
                'start': start, 'end': start+len(token.encode()), 'quote': token}
        args['context']['product'] = witness(chemical)
        args['context']['product_identity_method'] = witness(text)
        args['context']['uncertainty'] = witness(statistic)
        args['context']['cofactor_conditions'] = witness('37 C')
        repo, out, _ = populated(store, ctx, args); row, = out['result']['cells']
        assert row['source_meanings']['product']['display_text'] == chemical
        shown = row['source_meanings']['product_identity_method']['display_text']
        assert chemical in shown and 'P450cam T252N/V253T' in shown
        assert statistic not in shown and row['source_meanings']['uncertainty']['status'] == 'numerical_scope_unresolved'
        assert row['source_meanings']['cofactor_conditions']['display_text'] == '37 C'
        saved = repo.read(out['result']['sheet_ref'])
        assert saved['projection_version'] == 'product_coupling_projection_v2'
        assert saved['extraction']['context']['product_identity_method']['value'] == text
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'child_reports': [{'numbers': [row]}]}
        task, steering = render_literature_experimental_prompt(state, 'Examine the requested product evidence.').split('\n\nSTEERING\n', 1)
        assert chemical in steering and 'P450cam T252N/V253T' in steering and statistic not in steering
        assert 'projection_version' not in task and 'product_coupling_projection' not in steering


@pytest.mark.parametrize('primary', [1, 3], ids=['old_positive', 'old_nondetection'])
def test_current_repository_reads_actual_markerless_pin001_rows_and_forms_readonly_without_science(tmp_path, monkeypatch, primary):
    # Actual earlier controlled218run state, not a new synthetic legacy record.
    previous = Path('/home/chia/repos/gene_annotation_episode/verification/literature_reference_evidence_2026-10-25_001/a105_product_coupling_binding_218/pytest_001')
    candidates = [p for p in previous.glob('test_selected_shared*/COLD_PROOF_218.json')
        if json.loads(p.read_text())['retained_case_arm'] == primary]
    assert candidates, 'The original immutable pin001cohort must first complete its positive/NDcold proofs'
    directory = sorted(candidates)[0].parent; original_form = json.loads((directory/'ORIGINAL_ADMITTED_FORM_218.json').read_text())
    state_path = directory/'state'
    hashes = lambda: {str(p.relative_to(state_path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in state_path.rglob('*') if p.is_file()}
    before = hashes(); cold = Store.__new__(Store); cold.path = state_path; cold._savepoint = 0
    cold.db = sqlite3.connect((state_path/'state.sqlite3').as_uri()+'?mode=ro&immutable=1', uri=True, isolation_level=None)
    cold.db.row_factory = sqlite3.Row; cold.db.execute('PRAGMA query_only=ON')
    cold.db.create_function('library_scope_record', 2, cold._scope_filter_record)
    row = cold.db.execute('SELECT run_id,episode_id,cells FROM literature_product_coupling_received').fetchone()
    run_id = row['run_id']; rows = json.loads(row['cells']); assert rows == original_form['numbers']
    source_artifacts = [r[0] for r in cold.db.execute("SELECT json_extract(data,'$.artifact_ref') FROM records WHERE record_type='source' AND json_extract(data,'$.provider') != 'literature.a105.product_coupling'")]
    get_artifact = cold.get_artifact
    def saved_artifact(reference):
        assert reference not in source_artifacts, 'Old scientific bytes cannot be reacquired'
        return get_artifact(reference)
    def forbidden(*_args, **_kwargs):
        raise AssertionError('Old saved projection cannot run new source/science/admission/model work')
    monkeypatch.setattr(cold, 'get_artifact', saved_artifact)
    for module, names in {
        'literature_product_coupling_storage': ['read_product_coupling_inputs', 'populate_product_coupling', '_meaning'],
        'literature_product_coupling_inputs': ['read_product_coupling_inputs', 'validate_product_coupling_extraction', '_read_number', '_covariance'],
        'literature_product_coupling_calculations': ['populate_product_coupling', 'validate_product_coupling_extraction', '_sqrt'],
    }.items():
        for name in names: monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name, forbidden)
    monkeypatch.setattr(LiteratureProductCouplingRepository, 'receive_cells', forbidden)
    monkeypatch.setattr(LiteratureProductCouplingRepository, '_implementation_receipt', forbidden)
    from test_contract_information_runtime_059 import PresentedProvider
    monkeypatch.setattr(PresentedProvider, 'complete', forbidden)
    repo = LiteratureProductCouplingRepository(cold, run_id)
    refs = list(dict.fromkeys(r['sheet_ref'] for r in rows))
    for ref in refs:
        assert 'projection_version' not in repo.read(ref)
    assert repo.project_cells(refs, permitted_record_refs=refs) == rows
    receiver = BindingContext(run_id, row['episode_id'], 'annotation', (('annotation', 'root'),),
        cold.validate_scope(), {}, {}, tuple(LiteratureProductCouplingRepository.cell_record_refs(rows)))
    assert repo.received_cells(receiver) == rows and repo.fact_cells(receiver, refs, components=COMPONENTS) == rows
    assert json.loads(cold.db.execute('SELECT form FROM runtime_forms').fetchone()[0]) == original_form
    old_child = json.loads(cold.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0])
    old_schema = old_child['report_contract']['measurements']['schema']
    assert old_schema['properties']['numbers'] == product_coupling_cells_schema()
    validate_form(original_form, old_schema, lambda ref, namespace: bool(cold.get(ref)))
    assert cold.db.total_changes == 0 and cold.db.execute('PRAGMA query_only').fetchone()[0] == 1
    cold.close(); assert hashes() == before
    (tmp_path/'OLD_PIN001_PROJECTION_PROOF_218.json').write_text(json.dumps({'primary': primary,
        'actual_old_case': str(directory), 'original_markerless_rows_and_form': True,
        'current_projection_source_science_model_receive_blocked': True,
        'connection': 'mode=ro&immutable=1;query_only=ON', 'written_rows': 0, 'state_files': before,
        'old_descriptor_not_migrated': True}, indent=2)+'\n')


def test_unknown_host_projection_generation_is_rejected_after_source_authentication(tmp_path):
    store, ctx, args = setup(tmp_path, requested=['productive_fraction'])
    with store:
        repo, out, _ = populated(store, ctx, args); original_ref = out['result']['sheet_ref']
        saved = repo.read(original_ref); saved['projection_version'] = 'untrusted_projection_generation'
        artifact = store.artifact(canonical(saved), 'application/json')
        source = store.get(original_ref)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        value.update(artifact_ref=artifact, text_ref=artifact)
        new_ref = store.put('source', value, origin='tool', scope=plain(ctx.scope))['id']
        changed = deepcopy(out); changed['record_refs'] = [new_ref]; changed['changed_record_refs'] = [new_ref]
        changed['result']['sheet_ref'] = new_ref
        for row in changed['result']['cells']: row['sheet_ref'] = new_ref
        store.db.execute('UPDATE literature_product_coupling_operations SET outcome=?', (canonical(changed),))
        with pytest.raises(ContractError, match='saved_projection_version_unsupported'): repo.read(new_ref)


def test_saved_projection_is_authenticated_without_fallback_to_altered_outcome(tmp_path):
    store, ctx, args = setup(tmp_path, requested=['productive_fraction'])
    with store:
        repo, out, _ = populated(store, ctx, args); changed = deepcopy(out)
        changed['result']['cells'][0]['source_meanings']['product_conditions']['display_text'] = 'invented_display'
        store.db.execute('UPDATE literature_product_coupling_operations SET outcome=?', (canonical(changed),))
        with pytest.raises(ContractError, match='saved_outcome_mismatch'): repo.read(out['result']['sheet_ref'])


@pytest.mark.parametrize('profile', [None, CONTRACT_INFORMATION_PROFILE], ids=['legacy', 'explicit_profile'])
def test_pending_decision_restores_original_alias_schema_without_current_fact_catalog(tmp_path, monkeypatch, profile):
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import Workflow
    from test_runtime import FixtureController
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select
    store, ctx, args = setup(tmp_path/'state', requested=['product_per_cofactor'])
    qualification = {'type': 'string', 'enum': ['attribution_unknown']}
    literal = obj({'numbers': product_coupling_cells_schema(), 'limits': qualification})
    submitted = obj({'numbers': {'$ref': 'episode-fact:'+NAMESPACE}, 'limits': qualification})
    selected = select({'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(ctx.assignment),
        'goal': 'Evaluate the supplied endpoint pair and preserve unknown molecular attribution.', 'scope': plain(ctx.scope),
        'purpose': 'Return requested ratio and constrained attribution qualification.',
        'schema_json': json.dumps(submitted), 'initial_report_json': json.dumps({'limits': 'attribution_unknown'})}, 'report_update': {}})
    provider = PresentedProvider([OSError('Controlled pending218 interruption')])
    value = Workflow(store, ToolRegistry(store), provider, tmp_path/'run', ctx.run_id,
        lambda path, initial: FixtureController(str(path), initial, 2), ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=list(ctx.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args['source_ref']], contract_information_profile=profile),),
        decision_protocol='decision_exchange_v1')
    root = value.build('annotation', 'root', 'Evaluate the supplied experimental source.', plain(ctx.scope))
    try:
        with pytest.raises(OSError, match='pending218'):
            asyncio.run(root.run_async(value.context))
        original_request = value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request']
        def forbidden(*_args, **_kwargs):
            raise AssertionError('Pending original declarations cannot reload current fact/catalog factories')
        monkeypatch.setattr(Workflow, 'report_sources', forbidden)
        monkeypatch.setattr(Workflow, 'catalog', forbidden)
        monkeypatch.setattr(Workflow, 'action_schema', forbidden)
        current_factory = contracts.registered_schema
        monkeypatch.setattr(contracts, 'registered_schema', forbidden)
        schema, declaration = value.expanded_contract_form(root.source, selected['response']['selection'], 0, 'literature')
        assert schema == literal and declaration['submitted_schema_json'] == selected['response']['selection']['schema_json']
        assert value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request'] == original_request
        # Presentation can inspect current exact TYPEs, as existing native form
        # validators do; it still cannot retrieve current facts or tools.
        monkeypatch.setattr(contracts, 'registered_schema', current_factory)
        root.source.calls = 0; provider.script = iter([selected])
        async def choose_only():
            return await root.source.next(SimpleNamespace())
        assert asyncio.run(choose_only()) is not None
        child = json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0])
        assert child['report_contract']['measurements']['schema'] == literal
        assert child['message']['report_contract_declaration']['submitted_schema_json'] == selected['response']['selection']['schema_json']
        assert value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request'] == original_request
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()


def test_actual_nested_parent_forwards_only_its_requested_admitted_cells(tmp_path):
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select
    store, ctx, args = setup(tmp_path/'state', primary=1, requested=['productive_fraction'])
    source_ref = args['source_ref']; captures = []; root_prompts = []
    limits = {'type': 'string', 'enum': ['molecular_attribution_unknown']}
    form = obj({'numbers': {'$ref': 'episode-fact:'+NAMESPACE}, 'limits': limits})
    def commission(role, assignment):
        return {'selection': {'kind': 'episode_child', 'role': role, 'assignment': assignment,
            'goal': 'Examine the selected product and cofactor evidence with explicit source relationships.',
            'scope': plain(ctx.scope), 'purpose': 'Return requested numerical components and unknown attribution.',
            'schema_json': json.dumps(form), 'initial_report_json': json.dumps({'limits': 'molecular_attribution_unknown'})},
            'report_update': {} if role == 'literature' else {'limits': 'molecular_attribution_unknown'}}
    root_choice = commission('literature', plain(ctx.assignment))
    nested_choice = commission('literature_strategy', {'version': 'strategy_assignment_v1',
        'question_context_refs': [], 'prior_search_refs': [source_ref],
        REQUESTED: ['productive_fraction', 'reported_cofactor_activity']})
    populate = {'selection': {'kind': 'tool', 'tool': 'literature.product_coupling.populate', 'arguments': args},
        'report_update': {'limits': 'molecular_attribution_unknown'}}
    class FixtureProvider(PresentedProvider):
        async def complete(self, episode_id, *arguments):
            self.active_episode = episode_id
            return await super().complete(episode_id, *arguments)
    provider = FixtureProvider([])
    def integrate(inputs):
        report, = inputs['child_reports']; captures.append(report)
        is_root = len(captures) == 2
        if is_root:
            root_prompts.append(render_literature_experimental_prompt(inputs, 'Evaluate only received product coupling.'))
        raw = store.get_artifact(store.get(source_ref)['artifact_ref']); token = b'P450'; start = raw.index(token)
        commit = {name: [] for name in store.reasoning_schema()['required']}
        commit['source_subjects'] = [{'alias': 'reference_P450', 'reference_type': 'assay', 'source_ref': source_ref,
            'label': token.decode(), 'anchor': {'source_ref': source_ref, 'artifact_ref': store.get(source_ref)['artifact_ref'],
                'start': start, 'end': start+len(token), 'quote': token.decode()}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update':
            {} if is_root else {'limits': 'molecular_attribution_unknown'}}
    provider.script = iter([select(root_choice), select(nested_choice), select(populate),
        lambda frame: select(integrate(provider.views[provider.active_episode])),
        lambda frame: select(integrate(provider.views[provider.active_episode]))])
    try:
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 3 else 2),
            project_credit=progress, initial_known_record_refs=[source_ref],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=[source_ref]),),
            binding_definitions={'credit': progress.as_record()}, decision_protocol='decision_exchange_v1'))
        assert [[row['component'] for row in form['numbers']] for form in captures] == [
            ['productive_fraction', 'reported_cofactor_activity'], ['productive_fraction']]
        assert captures[0]['numbers'][0] == captures[1]['numbers'][0]
        assert '216' not in root_prompts[0].split('\n\nSTEERING\n', 1)[1]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 5
        assert store.db.execute('SELECT count(*) FROM literature_product_coupling_operations').fetchone()[0] == 1
    finally:
        store.close()


@pytest.mark.parametrize('profile', [None, CONTRACT_INFORMATION_PROFILE], ids=['legacy', 'explicit_profile'])
@pytest.mark.parametrize('compact', [False, True], ids=['literal', 'alias'])
@pytest.mark.parametrize('primary', [1, 3], ids=['positive', 'nondetection'])
def test_selected_shared_loop_original_form_and_first_readonly_cold_composition(tmp_path, monkeypatch, profile, compact, primary):
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select
    requested = ['product_per_cofactor', 'productive_fraction', 'reported_product_activity',
        'productive_fraction_variance', 'productive_fraction_standard_uncertainty']
    store, ctx, args = setup(tmp_path/'state', primary=primary, requested=requested, covariance=primary == 1)
    source_ref = args['source_ref']; captured = []; controllers = []
    qualification = {'type': 'string', 'enum': ['preparation_relationships_unknown']}
    literal = obj({'numbers': product_coupling_cells_schema(), 'limits': qualification})
    submitted = obj({'numbers': {'$ref': 'episode-fact:'+NAMESPACE}, 'limits': qualification}) if compact else literal
    child = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(ctx.assignment),
        'goal': 'Determine what the source product-formation and NADH-consumption endpoints establish about the reference molecule.',
        'scope': plain(ctx.scope), 'purpose': 'Return only the requested endpoint components with original measurement and model qualifications.',
        'schema_json': json.dumps(submitted), 'initial_report_json': json.dumps({'limits': 'preparation_relationships_unknown'})}, 'report_update': {}}
    # Covariance is a separate explicitly synthetic source. Pass its reference
    # as actual selected assignment context, rather than assuming global custody.
    if primary == 1:
        child['selection']['assignment']['source_refs'].append(args['covariance_source_ref'])
    populate = {'selection': {'kind': 'tool', 'tool': 'literature.product_coupling.populate', 'arguments': args},
        'report_update': {'limits': 'preparation_relationships_unknown'}}
    def integrate(inputs):
        report, = inputs['child_reports']; captured.append(report)
        assert [row['component'] for row in report['numbers']] == requested
        assert report['limits'] == 'preparation_relationships_unknown'
        cells = {row['component']: row for row in report['numbers']}
        if primary == 1:
            assert cells['product_per_cofactor']['exact_value'] == {'numerator': '23', 'denominator': '54'}
            assert cells['productive_fraction']['value'] is None and cells['productive_fraction']['conditional_value'] is not None
            assert cells['productive_fraction_variance']['covariance']['origin'] == 'synthetic'
            assert cells['productive_fraction_variance']['input_origins'] == ['reported', 'synthetic']
            assert cells['productive_fraction_variance']['contribution_key'] == cells['productive_fraction_standard_uncertainty']['contribution_key']
        else:
            assert cells['reported_product_activity']['value'] == 0
            assert cells['reported_product_activity']['native_measurement_semantics'] == 'reported_nondetection'
            assert cells['product_per_cofactor']['value'] is None and cells['productive_fraction']['conditional_value'] is None
        assert 'matrix_exact' not in json.dumps(report)
        assert cells['product_per_cofactor']['source_value'] is None
        commit = {name: [] for name in store.reasoning_schema()['required']}
        raw = store.get_artifact(store.get(source_ref)['artifact_ref']); token = b'P450'; start = raw.index(token)
        commit['source_subjects'] = [{'alias': 'retained_reference_molecule', 'reference_type': 'assay',
            'source_ref': source_ref, 'label': token.decode(), 'anchor': {'source_ref': source_ref,
                'artifact_ref': store.get(source_ref)['artifact_ref'], 'start': start,
                'end': start+len(token), 'quote': token.decode()}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
    class FixtureProvider(PresentedProvider):
        async def complete(self, episode_id, *arguments):
            self.active_episode = episode_id
            return await super().complete(episode_id, *arguments)
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result); return result
    def action(value):
        value = deepcopy(value)
        if profile is not None and value['selection']['kind'] == 'tool':
            value['selection']['arguments'] = json.dumps(value['selection']['arguments'])
        return select(value)
    provider = FixtureProvider([])
    provider.script = iter([action(child), action(populate), lambda frame: action(integrate(provider.views[provider.active_episode]))])
    try:
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=controller, project_credit=progress, initial_known_record_refs=list(ctx.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=list(ctx.received_record_refs), contract_information_profile=profile),),
            binding_definitions={'credit': progress.as_record()}, decision_protocol='decision_exchange_v1'))
        assert len(captured) == 1 and summary['credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_product_coupling_operations').fetchone()[0] == 1
        child_request = json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0])
        assert child_request['report_contract']['measurements']['schema'] == literal
        if compact:
            assert child_request['message']['report_contract_declaration']['submitted_schema_json'] == child['selection']['schema_json']
        elif profile is None:
            assert 'report_contract_declaration' not in child_request['message']
        row = store.db.execute('SELECT run_id,episode_id,cells FROM literature_product_coupling_received').fetchone()
        exact_rows = json.loads(row['cells']); assert exact_rows == captured[0]['numbers']
        run_id, parent_id = row['run_id'], row['episode_id']
        all_refs = LiteratureProductCouplingRepository.cell_record_refs(exact_rows)
        receiver = BindingContext(run_id, parent_id, 'annotation', (('annotation', 'root'),), ctx.scope, {}, {}, tuple(all_refs))
        binding = binding_for(store, replace(ctx, run_id=run_id), reference_parent_sources=list(ctx.received_record_refs), contract_information_profile=profile)
        descriptor = binding.as_record(); refs = list(dict.fromkeys(r['sheet_ref'] for r in exact_rows))
        assert len(provider.rendered) == 3
        for text in provider.rendered[1:]:
            task, steering = text.split('\n\nSTEERING\n', 1)
            assert task.count(PRODUCT_COUPLING_TASK) == 1 and PRODUCT_COUPLING_TASK not in steering
            assert 'conditional_exact_value' not in task
        assert REFERENCE_PARENT_TASK in provider.rendered[-1].split('\n\nSTEERING\n', 1)[0]
        assert [c.scores for c in controllers] == [[0, 0], [0]]
        original_form = json.loads(store.db.execute('SELECT form FROM runtime_forms').fetchone()[0])
        assert original_form == captured[0]
        (tmp_path/'ORIGINAL_ADMITTED_FORM_218.json').write_text(json.dumps(original_form, indent=2)+'\n')
        before_counts = {table: store.db.execute('SELECT count(*) FROM '+table).fetchone()[0]
            for table in ('runtime_observations', 'runtime_actions', 'runtime_forms')}
        source_artifacts = [store.get(ref)['artifact_ref'] for ref in ctx.received_record_refs]
        assert tuple(store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()) == (0, 0, 0)
        state_path = store.path; store.close(); store = None
        hashes = lambda: {str(p.relative_to(state_path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in state_path.rglob('*') if p.is_file()}
        before = hashes(); cold = Store.__new__(Store); cold.path = state_path; cold._savepoint = 0
        cold.db = sqlite3.connect((state_path/'state.sqlite3').as_uri()+'?mode=ro&immutable=1', uri=True, isolation_level=None)
        cold.db.row_factory = sqlite3.Row; cold.db.execute('PRAGMA query_only=ON')
        cold.db.create_function('library_scope_record', 2, cold._scope_filter_record)
        statements = []; cold.db.set_trace_callback(statements.append)
        get_artifact = cold.get_artifact
        def saved_artifact(ref):
            assert ref not in source_artifacts, 'Original source and covariance bytes must not be reacquired'
            return get_artifact(ref)
        def forbidden(*_args, **_kwargs):
            raise AssertionError('Saved reconstruction must not acquire, parse, calculate, receive or invoke a model')
        monkeypatch.setattr(cold, 'get_artifact', saved_artifact)
        for module, names in {
            'literature_product_coupling_storage': ['read_product_coupling_inputs', 'populate_product_coupling'],
            'literature_product_coupling_inputs': ['read_product_coupling_inputs', 'validate_product_coupling_extraction', '_read_number', '_covariance'],
            'literature_product_coupling_calculations': ['populate_product_coupling', 'validate_product_coupling_extraction', '_sqrt'],
        }.items():
            for name in names: monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name, forbidden)
        monkeypatch.setattr(LiteratureProductCouplingRepository, '_implementation_receipt', forbidden)
        monkeypatch.setattr(LiteratureProductCouplingRepository, 'receive_cells', forbidden)
        monkeypatch.setattr(PresentedProvider, 'complete', forbidden)
        cold_host = SimpleNamespace(store=cold, run_id=run_id, tools=None); services = WorkflowServices(cold_host)
        monkeypatch.setattr(services, 'execute_tool', forbidden)
        restored, = compose_episode_bindings(services, store=cold, journal=SimpleNamespace(store=cold, run_id=run_id),
            execution_backend=None, descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        cold_host.episode_bindings = EpisodeBindingRegistry((restored,))
        assert restored.as_record() == descriptor
        assert restored.received_report_facts(receiver)[NAMESPACE] == exact_rows
        repo = restored._product_coupling_repository()
        assert repo.fact_cells(receiver, refs, components=COMPONENTS) == exact_rows
        assert json.loads(cold.db.execute('SELECT form FROM runtime_forms').fetchone()[0]) == original_form
        assert json.loads(cold.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0]) == child_request
        assert {table: cold.db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in before_counts} == before_counts
        assert cold.db.total_changes == 0 and cold.db.execute('PRAGMA query_only').fetchone()[0] == 1
        cold.close(); assert hashes() == before
        (tmp_path/'COLD_PROOF_218.json').write_text(json.dumps({'profile': profile, 'alias': compact,
            'retained_case_arm': primary, 'original_typed_rows_form_and_schema': True,
            'source_covariance_science_receive_model_blocked_before_composition': True,
            'connection': 'mode=ro&immutable=1;query_only=ON', 'changed_rows': 0, 'state_files': before,
            'existing_idempotent_schema_checks': sum('CREATE TABLE IF NOT EXISTS' in sql.upper() for sql in statements),
            'ordinary_own_action_observations': 3, 'selected_component_operations': 1,
            'actual_model_execution': False, 'a105_adequacy_claim': False}, indent=2)+'\n')
    finally:
        if store is not None: store.close()
