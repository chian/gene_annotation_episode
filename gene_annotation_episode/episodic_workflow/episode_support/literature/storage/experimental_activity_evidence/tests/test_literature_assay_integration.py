'Synthetic source operand graph through selected action, state and typed return.\n\nNo biological source or actual model inference is represented by these fixtures.\n'
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_storage import LiteratureAssayRepository, assay_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_inputs import read_assay_inputs
from .unit_world import in_unit
TEXT = 'Protein P from organism X was assayed as construct P-His in purified preparation with substrate A.\nThe assay condition was 30 C and pH 7.\nOne preparation was measured for identified product B formation.\nThe reported net sample-minus-blank rate was 1.00 µM/min.\nA separately measured contaminant contributed 0.15 uM/min.\nThe quantitative calibration recovery ratio was 1.00 fraction.\nThe assayed molecule concentration was 1000 nM.\nThe same-endpoint condition-control test rate was 2.00 uM/min.\nThe same-endpoint condition-control reference rate was 1.60 uM/min.\nThe distinct corrected-scale residual variance was 0.0625 min^-2.\nSynthetic assumption: complete known covariance and a normal corrected-effect observation model.\n'
COMPONENTS = ['attributed_rate', 'condition_response', 'corrected_activity', 'effect_variance', 'source_presence_index']
FORM = obj({'measurements': assay_cells_schema()})

def location_only(value):
    """The model's input form: a source location without the quotation the host reads."""
    if isinstance(value, list):
        return [location_only(item) for item in value]
    if isinstance(value, dict):
        located = 'start' in value and 'end' in value
        return {key: location_only(item) for key, item in value.items() if not (located and key == 'quote')}
    return value


def setup_store(store, ctx, *, full=True):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')

    def source(text, provider):
        artifact = store.artifact(text, 'text/plain')
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    main = source(TEXT, 'synthetic_assay_fixture')

    def witness(quote):
        start = len(TEXT[:TEXT.index(quote)].encode('utf-8'))
        return {'source_ref': main, 'representation': 'original', 'start': start, 'end': start + len(quote.encode('utf-8')), 'quote': quote}

    def measurement(line, number, unit):
        quote = next((row for row in TEXT.splitlines() if row.startswith(line)))
        nstart, ustart = (quote.index(number), quote.index(unit) if unit else len(quote))
        return {'witness': witness(quote), 'number_start': nstart, 'number_end': nstart + len(number), 'unit_start': ustart, 'unit_end': ustart + len(unit)}
    args = {'source_ref': main, 'source_kind': 'synthetic_fixture', 'assay': {'molecule': witness('Protein P'), 'organism': witness('organism X'), 'genotype': None, 'construct': witness('construct P-His'), 'preparation': witness('purified preparation'), 'condition': witness('30 C and pH 7'), 'intended_variable': None, 'experimental_system': None, 'expression_host': None, 'measured_entity': witness('product B'), 'asserted_input': witness('substrate A'), 'asserted_output': witness('product B'), 'endpoint': {'value': 'product_formation', 'witnesses': [witness('identified product B formation')]}, 'arrangement': {'value': 'single_preparation', 'witnesses': [witness('One preparation')]}}, 'primitives': {'q': measurement('The reported net', '1.00', 'µM/min'), 'g': measurement('A separately measured', '0.15', 'uM/min'), 'k': measurement('The quantitative calibration', '1.00', 'fraction'), 'E': measurement('The assayed molecule', '1000', 'nM'), 'u': measurement('The same-endpoint condition-control test', '2.00', 'uM/min'), 'v': measurement('The same-endpoint condition-control reference', '1.60', 'uM/min')}, 'covariance_source_ref': None, 'distinct_residual_variance': measurement('The distinct corrected', '0.0625', 'min^-2') if full else None, 'variance_status': 'known' if full else 'unknown', 'observation_model': 'known_normal_nonnegative_presence' if full else 'none', 'model_witnesses': [witness('Synthetic assumption: complete known covariance and a normal corrected-effect observation model.')] if full else []}
    references = [main]
    if full:

        def read(ref, representation):
            row = store.get(ref)
            artifact = row['artifact_ref'] if representation == 'original' else row['text_ref']
            return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
        parsed = read_assay_inputs(args, read_source=read)
        observations = parsed['primitive_observations']
        order = ['q', 'g', 'k', 'E', 'u', 'v']
        diagonal = [0.04, 0.0225, 0.0025, 10000, 0.01, 0.01]
        covariance = {'version': 'a105_primitive_covariance', 'primitive_order': order, 'primitive_measurement_keys': [observations[key]['measurement_key'] for key in order], 'primitive_units': [observations[key]['raw_unit'] for key in order], 'covariance': [[diagonal[i] if i == j else 0.0 for j in range(6)] for i in range(6)], 'origin': 'synthetic'}
        cov = source(canonical(covariance), 'synthetic_assay_covariance')
        args['covariance_source_ref'] = cov
        references.append(cov)
    else:
        args['primitives']['g'] = None
    assignment = {'version': 'literature_assignment', 'question_context_refs': [], 'source_refs': references, 'requested_assay_components': COMPONENTS}
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), assignment, {}, references)
    return (store, context, args)

@in_unit
def test_copied_provider_label_does_not_manufacture_a_selected_assay_output(store, ctx):
    store, context, args = setup_store(store, ctx, full=False)
    repo = LiteratureAssayRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    row = store.get(outcome['result']['sheet_ref'])
    request = json.loads(store.get_artifact(row['request_ref']))
    request['operation_key'] = 'never-selected'
    false_request = store.artifact(canonical(request), 'application/json')
    fields = {name: row[name] for name in ('provider', 'accession', 'uri', 'artifact_ref', 'text_ref', 'version', 'retrieved_at', 'parent_source_refs')}
    fields['request_ref'] = false_request
    fake = store.put('source', fields, origin='tool', scope=plain(context.scope))
    with pytest.raises(ContractError, match='not_selected_output'):
        repo.read(fake['id'])

@pytest.mark.parametrize('unknown', ['molecule', 'endpoint'])
@in_unit
def test_unidentified_observation_scope_preserves_arithmetic_without_claiming_source_score(store, ctx, unknown):
    store, context, args = setup_store(store, ctx)
    if unknown == 'molecule':
        args['assay']['molecule'] = None
    else:
        args['assay']['endpoint'] = {'value': 'unknown', 'witnesses': []}
    result = LiteratureAssayRepository(store, context.run_id).populate(context, args, 'partial-scope')
    assert result['status'] == 'completed'
    cells = result['result']['cells']
    assert cells['corrected_activity']['value'] == pytest.approx(0.68)
    assert cells['source_presence_index']['value'] is None
    assert cells['source_presence_index']['unavailable_reason'] == ('assayed_molecule_unresolved' if unknown == 'molecule' else 'source_endpoint_unresolved')

@pytest.mark.parametrize('endpoint', ['growth', 'abundance', 'ligand_binding', 'other_measured_endpoint'])
@in_unit
def test_concentration_rate_correction_does_not_score_a_different_endpoint_model(store, ctx, endpoint):
    store, context, args = setup_store(store, ctx)
    args['assay']['endpoint']['value'] = endpoint
    result = LiteratureAssayRepository(store, context.run_id).populate(context, args, 'different-model')
    cells = result['result']['cells']
    assert cells['net_rate']['value'] == 1
    assert cells['condition_response']['value'] == 1.25
    for name in ('corrected_activity', 'effect_variance', 'effect_standard_uncertainty', 'effect_precision', 'source_profile_log_ratio', 'source_presence_index'):
        assert cells[name]['value'] is None
        assert cells[name]['unavailable_reason'] == 'endpoint_requires_different_model'
