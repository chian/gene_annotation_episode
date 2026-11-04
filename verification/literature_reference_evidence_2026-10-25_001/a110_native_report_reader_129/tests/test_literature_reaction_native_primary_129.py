"""One retained original report; constructed episode choices, no model inference.

Reader129 POST_PAPER_RESET_002 precedes this bounded conversion. Root independently
read the same original source and recorded its own reset in132. The source's
printed product-pair ratio is read; its NMR spectrum is not reintegrated.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_reaction_native_inputs import VERSION
from gene_annotation_episode.literature_reaction_native_storage import native_observations_schema, POSITIONS_FIELD
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository, reaction_semantic_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_integration import setup_case, source
from test_runtime import FixtureController, ScriptedProvider


def test_primary_author_product_pair_ratio_selected_and_returned_with_unknown_sampling(tmp_path, monkeypatch, record_property):
    store, seed, args = setup_case(tmp_path / 'state', primary=True)
    captured = []
    with store:
        expression = deepcopy(args['interpretation_witnesses'][0])
        text = expression['quote']
        start = text.index('1:1')
        first = {'witness': expression, 'number_start': start, 'number_end': start + 1}
        second = {'witness': expression, 'number_start': start + 2, 'number_end': start + 3}
        model = dict.fromkeys(('definition', 'reaction', 'function_relation', 'prediction_evidence'))
        # An explicit stoichiometric hypothesis on this same product-pair scale,
        # not a second experimental measurement or an independently tested model.
        model.update(definition=expression, prediction_evidence=expression,
            prediction_basis='source_supported_inference')
        selection = {'version': VERSION, 'ratio': {'mode': 'source_summary', 'ratio_kind': 'product_pair',
            'unit': 'mol_per_mol', 'measurement_basis': 'source_supported_molar_ratio',
            'basis_witnesses': [expression], 'observations': [], 'summary': {
                'value': {'kind': 'reported_pair', 'numerator': first, 'denominator': second},
                'uncertainty': {'kind': 'unreported', 'number': None, 'basis_witnesses': []},
                'count': {'number': None, 'basis': 'unknown', 'basis_witnesses': []}},
            'claim': {'kind': 'declared', 'value': 1., 'basis': 'source_supported_inference', 'evidence': [expression]},
            'alternatives': []}, 'budget': None, 'meanings': {'ratio': {'claim': model, 'alternatives': []}, 'budget': None}}
        # No prepared measured mean, SD, n or resource value is copied into the
        # selector recipe. Both actual printed coefficients come from its spans.
        dataset = source(store, canonical(selection), parents=list(seed.received_record_refs[:2]))
        args = {**args, 'data_source_ref': dataset['id'], 'source_kind': 'primary_source'}
        components = ['ratio_mean', 'claim_nominal_squared_error', 'claim_mean_squared_error',
            'reaction_comparison', 'resource_capacity']
        assignment = {**plain(seed.assignment), 'requested_reaction_components': components, POSITIONS_FIELD: [0],
            'source_refs': [*seed.received_record_refs, dataset['id']]}
        form = obj({'components': reaction_semantic_cells_schema(), 'reported_operands': native_observations_schema()})
        def receive(inputs):
            report, = inputs['child_reports']
            captured.append(deepcopy(report))
            rows = report['components']
            assert [row['component'] for row in rows] == components
            assert [row['value'] for row in rows] == [1., 0., None, None, None]
            assert all(row['independent_n'] is row['reported_sample_sd'] is None for row in rows)
            native, = report['reported_operands']
            assert native['ratio_kind'] == 'product_pair'
            assert native['measurement_basis'] == 'source_supported_molar_ratio'
            assert native['ratio_form'] == 'normalized_reported_pair'
            assert native['numerator_value'] == native['denominator_value'] == native['value'] == 1
            assert native['reported_count'] is native['independent_n'] is None
            assert native['measurement_corrections'] == 'not_applied'
            paper = store.get(args['source_ref'])
            raw = store.get_artifact(paper['artifact_ref'])
            molecule = b'CsiD'; start = raw.index(molecule)
            commit = {key: [] for key in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'actual_source_molecule', 'reference_type': 'assay',
                'source_ref': paper['id'], 'label': 'CsiD', 'anchor': {'source_ref': paper['id'],
                    'artifact_ref': paper['artifact_ref'], 'start': start, 'end': start + len(molecule), 'quote': 'CsiD'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        provider = ScriptedProvider([
            {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
                'goal': 'Read the author-reported CsiD product-pair ratio with its sampling limitations',
                'scope': plain(seed.scope), 'purpose': 'Return the selected source ratio components and exact reported pair',
                'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}},
            {'selection': {'kind': 'tool', 'tool': 'literature.reaction.populate', 'arguments': args}, 'report_update': {}}, receive])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=[*seed.received_record_refs, dataset['id']],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args['source_ref']]),), binding_definitions={'credit': scorer.as_record()}))
        assert len(captured) == 1
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_reaction_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_reaction_native_observations_received').fetchone()[0] == 1
        operation = store.db.execute('select outcome from literature_reaction_operations').fetchone()
        outcome = json.loads(operation['outcome'])
        row = store.get(outcome['result']['sheet_ref'])
        saved_artifacts = {row['artifact_ref'], row['request_ref']}
        original = store.get_artifact
        def only_saved(reference):
            assert reference in saved_artifacts
            return original(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved primary replay cannot reread/reinterpret the paper')
        monkeypatch.setattr(store, 'get_artifact', only_saved)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_storage.read_reaction_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints', forbidden)
        store.db.execute('PRAGMA query_only=ON')
        repo = LiteratureReactionRepository(store, result['run_id'])
        native = repo.native_observations_projection().project_rows([row['id']], permitted_record_refs=[row['id']], positions=[0])
        assert native == captured[0]['reported_operands']
        record_property('native129_primary_result', json.dumps({'source': 'PMC6265302 Supplementary Figure2',
            'ratio_kind': 'product_pair', 'ratio_mean': 1., 'nominal_squared_error': 0., 'full_mse': None,
            'independent_n': None, 'sample_sd': None, 'alternative_count': 0, 'budget_evaluated': False,
            'raw_spectrum_integration': False, 'native_model_inference': False, 'actual_observations': 3}))
