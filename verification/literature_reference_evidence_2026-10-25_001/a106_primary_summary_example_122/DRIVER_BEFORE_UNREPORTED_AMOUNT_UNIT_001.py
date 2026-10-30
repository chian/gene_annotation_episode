"""One retained primary experiment; explicit selectors; scripted runtime, no model.

Run from the repository with Python 3. Dependencies are the released 119 pin002.
Outputs are created under a NEW --output directory, never silently overwritten.
"""
from pathlib import Path
import argparse
import asyncio
from dataclasses import replace
from functools import partial
import hashlib
import importlib
import json
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
V = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument('--code-root', type=Path, default=BASE / 'pin_001_basis')
PIN = _pre.parse_known_args()[0].code_root.resolve()
sys.path[:0] = [str(PIN), str(PIN / 'tests')]

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_perturbation_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository
from gene_annotation_episode.literature_perturbation_summary import ROLES
from gene_annotation_episode.literature_perturbation_summary_storage import perturbation_summary_cells_schema
from gene_annotation_episode.literature_summary_figure_reader import read_summary_figure
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

XML = V / 'primary_yeag/PMC4664914_original.xml'
IMAGE = ROOT / 'research/experimental_scoring_review_2026-10-23/a106_perturbation_sheet_013/raw/PMC4664914_figure6.jpg'
PDF = V / 'primary_yeag/srep17524-s1.pdf'
SUPPLEMENT = V / 'a106_reported_uncertainty_case_115/SUPPLEMENT_TEXT_001.txt'
TEXT = BASE / 'PRIMARY_RELEVANT_TEXT_001.txt'
EXPERIMENT = 'Figueira2015_Fig6B_120h_WTKOR_one_experiment'
REQUESTED = [*[r + '_' + k for r in ('W', 'K', 'R') for k in
    ('summary_value', 'reported_spread', 'reported_count', 'mean_se', 'mean_variance')],
    'perturbation_difference', 'symmetric_effect', 'restoration_difference',
    'restoration_fraction_raw', 'restoration_agreement', 'amount_comparability',
    'effect_isolation', 'reference_restoration_index', 'perturbation_mean_variance',
    'perturbation_variance_lower', 'perturbation_variance_upper',
    'shared_contrast_covariance']
FORM = obj({'measurements': perturbation_summary_cells_schema()})


def sha(body):
    return hashlib.sha256(body).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def feature(box, kind):
    return {'kind': kind, 'roi': dict(zip(('left', 'top', 'right', 'bottom'), box)),
        'rgb_min': [0, 0, 0], 'rgb_max': [110, 110, 110],
        'minimum_row_fraction': .8, 'minimum_run_rows': 1, 'edge_tolerance_pixels': .5}


def selection(role):
    # Native original-image coordinates, explicitly selected after visual inspection.
    # Black top border identifies the bar edge; upper cap is a separate horizontal run.
    mean, cap = {
        'W': ((1035, 665, 1061, 680), (1035, 651, 1061, 665)),
        'K': ((1112, 724, 1138, 742), (1112, 704, 1138, 720)),
        'R': ((1188, 663, 1214, 679), (1188, 649, 1214, 663)),
    }[role]
    return {'calibration': {'scale': 'log10', 'first': {'pixel': 807.5, 'value': 1e6},
        'second': {'pixel': 551.5, 'value': 1e9}, 'unit': 'CFU_per_mL'},
        'mean': feature(mean, 'top_edge'), 'upper_error': feature(cap, 'run_center'),
        'lower_error': None}


def source(store, original, *, provider, text=None, parents=(), version=None):
    return store.put('source', {'provider': provider, 'accession': 'PMC4664914',
        'uri': None, 'artifact_ref': store.artifact(original, 'application/octet-stream'),
        'text_ref': None if text is None else store.artifact(text, 'text/plain'),
        'request_ref': None, 'version': version, 'retrieved_at': None,
        'parent_source_refs': list(parents)}, origin='caller')


def witness(ref, body, quote, representation='text'):
    quoted = quote.encode()
    start = body.rindex(quoted)
    return {'source_ref': ref, 'representation': representation,
        'start': start, 'end': start + len(quoted), 'quote': quote}


def setup(output, scenario, *, legacy_without_basis=False):
    store = Store(output / 'state')
    # The caller binding is an engineering-only sequence fixture, NOT a YeaG sequence
    # or target annotation. Scientific reference identity comes solely from the paper.
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    text = TEXT.read_bytes()
    paper = source(store, XML.read_bytes(), provider='retained_primary_article', text=text)
    image = source(store, IMAGE.read_bytes(), provider='retained_primary_figure6', parents=[paper['id']])
    supplement = source(store, PDF.read_bytes(), provider='retained_primary_supplement',
        text=SUPPLEMENT.read_bytes(), parents=[paper['id']])
    ref = paper['id']
    w = lambda quote: witness(ref, text, quote)
    # Short labels also occur in Salmonella panel6C. Retain the FIRST relevant
    # arm occurrence strictly within the final complete panel6B caption span.
    caption_start = text.rindex(b'(B) The viability of wild-type')
    caption_end = text.index(b'Statistical analyses were performed by one-way ANOVA', caption_start)
    def wb(quote):
        start = text.index(quote.encode(), caption_start, caption_end)
        return {'source_ref': ref, 'representation': 'text', 'start': start,
            'end': start + len(quote.encode()), 'quote': quote}
    arm_witnesses = {'W': wb('wild-type'), 'K': wb('∆yeaG'), 'R': wb('∆yeaG pBAD18-yeaG')}
    caption = w('colony-forming unit (CFU) count after 20\u2009min, 72\u2009h & 120\u2009h in N starvation. Error bars represent sd (n\u2009=\u20093).')
    replication = w('Unless specified otherwise, data is represented as the mean average of 3 independent experiments or more and')
    data = {'version': 'a106_source_measurements_v2', 'endpoint_unit': 'CFU_per_mL',
        'exposure_unit': 'molecules_per_cell', 'origin': 'graph_derived',
        'uncertainty_basis': 'per_measurement', 'measurements': {}, 'covariances': []}
    for role in ROLES:
        measured = role in ('W', 'K', 'R')
        conditional = scenario == 'conditional_raw_arithmetic'
        data['measurements'][role] = {'value': None,
            'measurement_id': EXPERIMENT + '_' + role if measured else None,
            'value_scale': 'endpoint',
            'summary_kind': 'arithmetic_mean' if measured and conditional else 'unknown',
            'summary_scale': 'endpoint' if measured and conditional else 'unknown',
            'uncertainty': {'kind': 'sd' if measured else 'unreported', 'value': None,
                'lower': None, 'upper': None, 'coverage': None,
                'scale': 'endpoint' if measured and conditional else 'unknown',
                'variance_status': 'estimated' if measured else 'unknown'},
            'count': {'n': 3 if measured else None, 'unit_kind': 'other' if measured else 'unknown',
                'independence': 'independent' if measured else 'unknown'},
            'raw_units': None, 'graph': {'source_ref': image['id'], 'selection': selection(role)} if measured else None,
            'digitization': None, 'meaning_witnesses': [arm_witnesses[role], caption, replication] if measured else []}
        if not legacy_without_basis:
            data['measurements'][role]['interpretation_basis'] = {
                'summary_kind': 'conditional_assumption' if measured and conditional else 'unresolved',
                'summary_scale': 'conditional_assumption' if measured and conditional else 'unresolved',
                'spread_kind': 'source_reported' if measured else 'unresolved',
                'spread_scale': 'conditional_assumption' if measured and conditional else 'unresolved',
                'count_n': 'source_reported' if measured else 'unresolved',
                'count_unit': 'source_supported_inference' if measured else 'unresolved',
                'count_independence': 'source_reported' if measured else 'unresolved'}
    retained = source(store, canonical(data), provider='explicit_retained_graph_recipe',
        parents=[paper['id'], image['id'], supplement['id']], version=scenario)
    literals = dict.fromkeys(LITERAL_FIELDS)
    for field, quote in {'molecule': 'YeaG', 'recipient': 'E. coli',
        'experiment': 'The absence of yeaG reduces bacterial cell viability during sustained N starvation.',
        'reference_arm': 'wild-type', 'perturbed_arm': '∆yeaG',
        'restored_arm': '∆yeaG pBAD18-yeaG', 'endpoint': 'colony-forming unit (CFU) count',
        'condition': '120\u2009h in N starvation', 'intended_change': 'absence of yeaG'}.items():
        literals[field] = w(quote)
    for field, role in [('reference_arm', 'W'), ('perturbed_arm', 'K'), ('restored_arm', 'R')]:
        literals[field] = arm_witnesses[role]
    args = {'source_ref': ref, 'data_source_ref': retained['id'], 'source_kind': 'graph_extraction',
        'literals': literals, 'design': 'native_deletion_restoration',
        'measurement_status': 'validated_ratio_scale', 'same_endpoint_scope': 'yes',
        'amount_role': 'nuisance', 'orientation': 1,
        'interpretation_witnesses': [caption, w('Measurement of bacterial growth and viability')]}
    refs = [paper['id'], image['id'], supplement['id'], retained['id']]
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_perturbation_summary_components': REQUESTED}
    save(output / 'RECIPE.json', data)
    save(output / 'SELECTED_ARGUMENTS.json', args)
    save(output / 'SOURCE_IDENTITIES.json', {'experiment_id': EXPERIMENT, 'scenario': scenario,
        'source_refs': refs, 'source_files': [{ 'path': str(p), 'sha256': sha(p.read_bytes())}
            for p in (XML, IMAGE, PDF, SUPPLEMENT, TEXT)],
        'conditions': {'primary_unresolved': 'statistical mean and SD summary scales unresolved',
            'conditional_raw_arithmetic': 'ASSUMPTION: arithmetic mean and SD computed on raw CFU_per_mL; not source-established'},
        'exposure_unit_note': 'molecules_per_cell is an interface dimensional placeholder; no abundance observation supplied',
        'replication_note': 'n=3 independent experiments from caption+general methods; other unit, not invented culture/plate replicates',
        'manual_scope': 'Explicit retained recipe and calibration/ROIs chosen by investigator; not autonomous arbitrary-paper extraction',
        'caller_fixture': 'ATGGCT is engineering-only; not asserted to be the YeaG sequence or a biological target'})
    return store, args, refs, assignment


def run_scenario(output, scenario, *, legacy_without_basis=False):
    output.mkdir()
    store, args, refs, assignment = setup(output, scenario, legacy_without_basis=legacy_without_basis)
    received = []
    scope = store.validate_scope()
    commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
        'assignment': assignment, 'goal': 'Read retained primary Fig6B120h selected source recipe and return requested numerical cells',
        'scope': plain(scope), 'purpose': 'Populate source perturbation components with retained uncertainty distinctions',
        'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
    action = {'selection': {'kind': 'tool', 'tool': 'literature.perturbation.populate',
        'arguments': args}, 'report_update': {}}
    def receive(inputs):
        form, = inputs['child_reports']
        received.append(form)
        assert [r['component'] for r in form['measurements']] == REQUESTED
        row = store.get(args['source_ref'])
        raw = XML.read_bytes()
        start = raw.index(b'YeaG')
        commit = {name: [] for name in store.reasoning_schema()['required']}
        commit['source_subjects'] = [{'alias': 'retained_yeag_assay', 'reference_type': 'assay',
            'source_ref': row['id'], 'label': 'YeaG', 'anchor': {'source_ref': row['id'],
                'artifact_ref': row['artifact_ref'], 'start': start, 'end': start + 4, 'quote': 'YeaG'}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, action, receive]),
        run_dir=output / 'run', controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
        project_credit=scorer, initial_known_record_refs=refs,
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
        binding_definitions={'credit': scorer.as_record()}))
    assert len(received) == 1, 'selected operation must return through the ordinary child boundary'
    counts = {table: store.db.execute('select count(*) from ' + table).fetchone()[0] for table in
        ('runtime_observations', 'literature_perturbation_operations', 'literature_perturbation_summary_received')}
    assert counts == {'runtime_observations': 3, 'literature_perturbation_operations': 1,
        'literature_perturbation_summary_received': 1}, counts
    rows = received[0]['measurements']
    cells = {r['component']: r for r in rows}
    if not legacy_without_basis:
        assert tuple(cells['W_summary_value']['statistical_interpretation_basis']) == ('W',)
        assert set(cells['perturbation_difference']['statistical_interpretation_basis']) == {'W', 'K'}
        expected_scale_basis = 'conditional_assumption' if scenario == 'conditional_raw_arithmetic' else 'unresolved'
        assert cells['perturbation_difference']['statistical_interpretation_basis']['W']['summary_scale'] == expected_scale_basis
    assert cells['W_summary_value']['value'] > cells['K_summary_value']['value'] > 0
    assert cells['reference_restoration_index']['value'] is None
    assert cells['amount_comparability']['value'] is None and cells['effect_isolation']['value'] is None
    assert cells['perturbation_mean_variance']['value'] is None
    assert cells['shared_contrast_covariance']['value'] is None
    if scenario == 'primary_unresolved':
        assert cells['W_reported_spread']['value'] is None
        assert cells['W_reported_spread']['upper_error_cap'] is not None
        assert cells['W_mean_se']['value'] is None
    else:
        assert cells['W_mean_se']['value'] > 0
        assert cells['perturbation_variance_upper']['value'] > 0
    sheet = rows[0]['sheet_ref']
    repo = LiteraturePerturbationRepository(store, json.loads((output / 'run/run.json').read_text())['run_id'])
    saved = repo.read(sheet)
    save(output / 'POPULATED_SHEET.json', saved)
    save(output / 'TYPED_RETURN.json', received[0])
    manifest = json.loads((output / 'run/run.json').read_text())
    run = manifest['run_id']
    parent_row, = store.db.execute('select * from runtime_episodes where json_array_length(path)=1').fetchall()
    request = json.loads(parent_row['request'])
    parent = BindingContext(run, parent_row['episode_id'], 'annotation',
        tuple(tuple(p) for p in json.loads(parent_row['path'])), plain(scope),
        request['message'].get('episode_assignment', {}), request,
        tuple(EpisodeReceipts(store, run).known(parent_row['episode_id'])))
    source_artifacts = {store.get(ref)[key] for ref in refs for key in ('artifact_ref', 'text_ref') if store.get(ref).get(key)}
    store.close()
    reopened = Store.__new__(Store)
    reopened.path = (output / 'state').resolve(); reopened._savepoint = 0
    reopened.db = sqlite3.connect((reopened.path / 'state.sqlite3').as_uri() + '?mode=ro', uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row; reopened.db.execute('pragma query_only=ON')
    reopened.db.create_function('library_scope_record', 2, reopened._scope_filter_record)
    old_get = reopened.get_artifact
    def saved_only(ref):
        assert ref not in source_artifacts, 'replay must not reopen source/recipe/image bytes'
        return old_get(ref)
    def forbidden(*a, **kw):
        raise AssertionError('read-only reconstruction must not model, parse, calculate or mutate')
    with patch.object(reopened, 'get_artifact', saved_only), patch.object(reopened, 'put', forbidden), \
        patch.object(reopened, 'artifact', forbidden), patch.object(reopened, 'transaction', forbidden), \
        patch('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs', forbidden), \
        patch('gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration', forbidden), \
        patch('gene_annotation_episode.providers.ModelConnection', forbidden):
        from gene_annotation_episode.episode_composition import compose_episode_bindings
        from gene_annotation_episode.episode_journal import Journal
        services = WorkflowServices(SimpleNamespace(store=reopened, run_id=run))
        journal = Journal.__new__(Journal); journal.store = reopened; journal.db = reopened.db; journal.run_id = run
        composition = compose_episode_bindings(services, store=reopened, journal=journal, execution_backend=None,
            descriptors=manifest['episode_bindings'], job_episodes=None, resource_estimator=None, role_credit_bindings={})
        binding, = composition.bindings
        reconstructed = binding.received_report_facts(parent)['literature_perturbation_summary_cells']
        assert reconstructed == rows
        projection = services.literature_perturbation_repository().summary_projection()
        assert projection.fact_cells(parent, [sheet], components=['reference_endpoint']) == []
        assert reopened.db.total_changes == 0
    reopened.close()
    save(output / 'RECONSTRUCTION.json', {'exact_typed_rows': True, 'source_recipe_image_reopens': 0,
        'model_parser_calculator_mutation_allowed': False, 'database_mutations': 0,
        'unrequested_reference_endpoint_rows': 0, 'counts': counts, 'credit': result['credit'],
        'execution_kind': 'ordinary runtime with explicit scripted provider/test controller; no actual model science'})
    return {name: {k: row[k] for k in ('value', 'unit', 'lower_error_cap', 'upper_error_cap',
        'spread_reading', 'unavailable_reason', 'variance_scope')} for name, row in cells.items()}


def main():
    parser = argparse.ArgumentParser(parents=[_pre]); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--legacy-without-basis', action='store_true', help='Reproduce original119 engineering baseline only')
    options = parser.parse_args(); output = options.output.resolve(); output.mkdir()
    actual = {role: read_summary_figure(IMAGE.read_bytes(), selection(role)) for role in ('W', 'K', 'R')}
    for result in actual.values():
        assert result['image_sha256'] == sha(IMAGE.read_bytes())
        assert result['features']['mean']['status'] == 'populated'
        assert result['features']['upper_error']['status'] == 'populated'
    save(output / 'DIRECT_IMAGE_READINGS.json', actual)
    save(output / 'RETURN_SCHEMA.json', FORM)
    summary = {scenario: run_scenario(output / scenario, scenario, legacy_without_basis=options.legacy_without_basis)
        for scenario in ('primary_unresolved', 'conditional_raw_arithmetic')}
    save(output / 'NUMERICAL_SUMMARY.json', summary)
    modules = {}
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and name.startswith('gene_annotation_episode') and Path(filename).is_file():
            modules[name] = {'path': filename, 'sha256': sha(Path(filename).read_bytes())}
    assert all(Path(v['path']).is_relative_to(PIN) for v in modules.values())
    save(output / 'IMPORT_HASHES.json', modules)
    print(json.dumps({'output': str(output), 'status': 'PASS', 'scenarios': len(summary),
        'independent_experiments': 1, 'actual_model_calls': 0}))


if __name__ == '__main__':
    main()
