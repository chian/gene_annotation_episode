"""Controlled, source-grounded example of frozen native005; no model inference.

Ordinary selected blocking run and separate original-C4 engineering fixture
are deliberately reported separately. No production or historical run is edited.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass, replace
from functools import partial
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import patch

PIN = Path(__file__).resolve().parent
sys.path.insert(0, str(PIN))
from PIL import Image
from method_loop import ClosedRecord, EpisodeGoal
from method_loop.archive import JsonArchive
from method_loop.durable import content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_binding_interaction_storage import (
    LiteratureBindingInteractionRepository, COMPONENTS, binding_interaction_cells_schema)
from gene_annotation_episode.literature_binding_interaction_inputs import ROLES
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import run_workflow, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

OUT = PIN.parent / 'run_003'
FORM = obj({'numbers': binding_interaction_cells_schema()})
QUESTION = ('Determine what the retained IscR Table 3 competition experiment establishes about '
            '7C-to-G and 8C-to-G recognition by apo-WT and apo-E43A. Return the eight native '
            'components for each comparison, with reported-protocol and uncertainty qualifications.')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def verify_pin():
    manifest = json.loads((PIN / 'PIN_MANIFEST.json').read_bytes())
    for name, row in manifest.items():
        path = PIN / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__name__', '')
        path = getattr(module, '__file__', None)
        if name.split('.')[0] in {'gene_annotation_episode', 'method_loop'} and path:
            assert Path(path).resolve().is_relative_to(PIN), (name, path)
    return {'manifest_sha256': sha(PIN / 'PIN_MANIFEST.json'), 'files_verified': len(manifest),
            'imports': {name: {'path': str(Path(module.__file__).resolve()), 'sha256': sha(Path(module.__file__))}
                        for name, module in sorted(sys.modules.items())
                        if name.split('.')[0] in {'gene_annotation_episode', 'method_loop'} and getattr(module, '__file__', None)}}

class Article(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside = False; self.parts = []; self.images = []
    def handle_starttag(self, tag, attrs):
        if tag == 'article': self.inside = True
        if tag == 'img': self.images.append(dict(attrs).get('src', ''))
    def handle_endtag(self, tag):
        if tag == 'article': self.inside = False
    def handle_data(self, value):
        if self.inside: self.parts.append(value)

def source_proof():
    parser = Article(); parser.feed((PIN / 'inputs/primary.html').read_text())
    normalized = ''.join(''.join(parser.parts).split())
    assert normalized == ''.join((PIN / 'inputs/primary_text.txt').read_text().split())
    image, = [value for value in parser.images if 'nihms-454929-t0001.jpg' in value]
    assert len(normalized) == 51567
    proof = {'article_text_equal_ignoring_whitespace': True, 'nonwhitespace_characters': len(normalized),
             'actual_original_table_image_uri': image,
             'source_files': {name: {'sha256': sha(PIN / 'inputs' / name), 'bytes': (PIN / 'inputs' / name).stat().st_size}
                              for name in ('primary.html', 'primary_text.txt', 'table3.jpg')}}
    write('SOURCE_PROOF.json', proof)
    return image

def setup(path, image_uri):
    store = Store(path)
    store.create_problem(input_path=PIN / 'inputs/target.fna', molecule='dna')
    html = store.artifact((PIN / 'inputs/primary.html').read_bytes(), 'text/html')
    text = store.artifact((PIN / 'inputs/primary_text.txt').read_bytes(), 'text/plain')
    image = store.artifact((PIN / 'inputs/table3.jpg').read_bytes(), 'image/jpeg')
    primary = store.put('source', {'provider': 'retained_primary_058', 'accession': 'PMC3676455',
        'uri': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3676455/', 'artifact_ref': html, 'text_ref': text,
        'request_ref': None, 'version': 'retained_primary_html_and_article_text_058', 'retrieved_at': None,
        'parent_source_refs': []}, origin='caller')
    table = store.put('source', {'provider': 'retained_primary_asset_058', 'accession': None,
        'uri': image_uri, 'artifact_ref': image, 'text_ref': None, 'request_ref': None,
        'version': 'original_retained_table3_image_058', 'retrieved_at': None,
        'parent_source_refs': [primary['id']]}, origin='caller')
    refs = [primary['id'], table['id']]
    def bind(value):
        if isinstance(value, dict): return {key: bind(child) for key, child in value.items()}
        if isinstance(value, list): return [bind(child) for child in value]
        if value == 'source_primary_058_proposal': return primary['id']
        if value == 'source_table3_058_proposal': return table['id']
        return value
    args = bind(json.loads((PIN / 'inputs/PROPOSED_SOURCE_NOMINATIONS_001.json').read_bytes())['cases'])
    return store, refs, args, {html, text, image}

def assignment(refs, components=COMPONENTS):
    return {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': refs,
            'requested_binding_interaction_components': list(components)}

class FixtureController:
    """Controlled two-action continuation, not the configured scientific estimator."""
    def __init__(self, epoch, initial):
        self.epoch = epoch; self.current = initial; self.scores = []
    def observe(self, label, value, *, is_root):
        credit = value.as_record()['credit']; self.scores.append(credit-self.current); self.current = credit
        return SimpleNamespace(stop=len(self.scores) >= 2, requests_transition=False,
                               as_record=lambda: {'stop': len(self.scores) >= 2, 'requests_transition': False, 'delta': self.scores[-1]})
    def state(self):
        scores = list(self.scores); credit = self.current; stop = len(scores) >= 2
        return SimpleNamespace(decision=SimpleNamespace(stop=stop),
                               as_record=lambda: {'scores': scores, 'credit': credit, 'decision': {'stop': stop}})
    def transitioned(self, epoch): raise AssertionError('No fixture epoch transition')

class ScriptedProvider:
    """Controlled choices and source interpretations; not actual configured-model science."""
    def __init__(self, script): self.script = iter(script); self.contexts = []; self.released = []
    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING'
        self.contexts.append(deepcopy(context)); response = next(self.script)
        return response(context) if callable(response) else deepcopy(response)
    async def release(self, episode_id): self.released.append(episode_id)

def service_binding(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    services = WorkflowServices(host)
    binding = LiteratureEpisodes(services, rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return services, binding

def assert_science(rows):
    assert len(rows) == 16
    expected = json.loads((PIN / 'inputs/EXPECTED_ARITHMETIC_001.json').read_bytes())
    compact = []
    for index, exp in enumerate(expected):
        group = rows[index*8:(index+1)*8]
        assert [row['component'] for row in group] == list(COMPONENTS)
        for row in group:
            name = row['component']
            if name in exp:
                want = exp[name]
                assert row['relation'] == want['relation'], row
                field = 'threshold' if 'threshold' in want else 'value'
                assert math.isclose(row[field], want[field], rel_tol=1e-13), row
                if field == 'threshold':
                    assert row['value'] is None and row['bound_kind'] == 'reported_limit_arithmetic'
            assert row['model_reader_capability'] == 'unimplemented'
            assert row['model_input_status'] == 'not_supplied_by_native_operation'
            compact.append({key: row.get(key) for key in ('sheet_ref', 'component', 'value', 'threshold', 'relation', 'bound_kind', 'unavailable_reasons')})
    return compact

def context_from_saved(store, run, row, refs):
    request = json.loads(row['request']); path = tuple(tuple(part) for part in json.loads(row['path']))
    return BindingContext(run, row['episode_id'], path[-1][0], path, request['message']['scope'],
                          request['message'].get('episode_assignment', {}), request, tuple(refs))

def ordinary_run(image_uri):
    store, refs, args, artifacts = setup(OUT / 'selected_state', image_uri)
    received = []
    def use(context):
        form, = context['child_reports']; rows = form['numbers']; assert_science(rows); received.extend(deepcopy(rows))
        source = store.get(refs[0]); raw = store.get_artifact(source['text_ref']); token = b'IscR'; start = raw.index(token)
        commit = {key: [] for key in store.reasoning_schema()['required']}
        commit['source_subjects'] = [{'alias': 'assayed_IscR_reference', 'reference_type': 'assay', 'source_ref': refs[0],
            'label': 'IscR', 'anchor': {'source_ref': refs[0], 'artifact_ref': source['text_ref'], 'start': start,
                                      'end': start+len(token), 'quote': 'IscR'}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
    commission = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment(refs),
        'goal': QUESTION, 'scope': store.validate_scope(), 'purpose': QUESTION,
        'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
    provider = ScriptedProvider([commission, *[{'selection': {'kind': 'tool',
        'tool': 'literature.binding.interaction.populate', 'arguments': value}, 'report_update': {}}
        for value in args.values()], use])
    controllers = []
    def controller(path, initial):
        value = FixtureController(str(path), initial); controllers.append(value); return value
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=OUT / 'selected_episode',
        controller_factory=controller, project_credit=scorer, initial_known_record_refs=refs,
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=refs),),
        binding_definitions={'credit': scorer.as_record()}, goal=QUESTION))
    assert summary['credit'] == 0 and len(provider.contexts) == 4
    assert [controller.scores for controller in controllers] == [[0, 0], [0, 0]]
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
    assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 2
    assert store.db.execute('SELECT count(*) FROM literature_binding_interaction_operations').fetchone()[0] == 2
    assert store.db.execute('SELECT count(*) FROM literature_binding_interaction_received').fetchone()[0] == 1
    assert not store.list('observation') and not store.list('assessment')
    write('SELECTED_NATIVE_ROWS.json', received)
    write('SELECTED_COMPONENTS.json', assert_science(received))
    # Save only actual public result/receipt state; this fixture has no private model history.
    root, = [row for row in store.db.execute('SELECT * FROM runtime_episodes') if len(json.loads(row['path'])) == 1]
    run = root['run_id']
    parent_refs = [row['record_ref'] for row in store.db.execute(
        'SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=?', (run, root['episode_id']))]
    parent = context_from_saved(store, run, root, parent_refs)
    saved = []
    for row in store.db.execute('SELECT outcome FROM literature_binding_interaction_operations ORDER BY rowid'):
        outcome = json.loads(row[0]); saved.append(LiteratureBindingInteractionRepository(store, run).read(outcome['result']['sheet_ref']))
    write('SAVED_EXTRACTION_AND_CALCULATION.json', saved)
    physical = {}
    for item in saved:
        for role in ROLES:
            uncertainty = item['extraction']['roles'][role]['uncertainty']
            assert uncertainty['minimum_count']['literal']['status'] == 'exact'
            assert uncertainty['minimum_count']['status'] == 'unsupported_literal'
            assert uncertainty['canonical']['minimum_count'] is None
            assert uncertainty['canonical']['basis'] == 'fit_to_averaged_curve'
            assert uncertainty['canonical']['statistic'] == 'sd'
        assert item['calculation']['model'] is None
    for role in (ROLES[0], ROLES[2]):
        a, b = [item['extraction']['roles'][role] for item in saved]
        assert a['physical_fit'] == b['physical_fit']
        assert a['uncertainty']['minimum_count']['status'] == 'unsupported_literal'
        assert a['uncertainty']['canonical']['minimum_count'] is None
        assert saved[0]['calculation']['operand_keys'][role] == saved[1]['calculation']['operand_keys'][role]
        physical[role] = {'physical_fit': a['physical_fit'], 'operand_key': saved[0]['calculation']['operand_keys'][role]}
    write('SHARED_CONTROLS.json', physical)
    before = list(store.db.iterdump()); path = store.path; store.close()
    ro = reconstruct(path, run, parent, received, artifacts, before)
    display_receipt = provider_display(provider.contexts[-1], received)
    result = {'kind': 'controlled_selected_blocking_shared_method_loop', 'actual_configured_model': False,
        'native_populations': 2, 'native_parent_rows': 16, 'episodes': 2, 'ordinary_actual_observations': 4,
        'controller_action_deltas': [[0, 0], [0, 0]], 'annotation_credit': None, 'scientific_credit': 0,
        'typed_parent_receipts': 1, 'read_only_reconstruction': ro, 'provider_display': display_receipt,
        'target_binding': 'Fixed original 762 nt target only; source IscR is an assayed reference, no correspondence claimed',
        'completion': 'Controlled fixture yield stop; not scientific A105 completion'}
    write('SELECTED_RECEIPT.json', result)
    return result

def forbidden(*args, **kwargs):
    raise AssertionError('Read-only reconstruction cannot access original source/image, reader, calculator, receive or reprice')

def reconstruct(path, run, parent, expected, artifacts, before, replay=None):
    reopened = Store.__new__(Store); reopened.path = path; reopened._savepoint = 0
    reopened.db = sqlite3.connect((path / 'state.sqlite3').resolve().as_uri()+'?mode=ro', uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row
    try:
        try: reopened.db.execute('CREATE TABLE forbidden_write058(n)')
        except sqlite3.OperationalError as exc: assert 'readonly' in str(exc).lower()
        else: raise AssertionError('Read-only connection unexpectedly accepted write')
        original_get = reopened.get_artifact
        original_open = Path.open
        denied_paths = {(PIN / 'inputs' / name).resolve() for name in ('primary.html', 'primary_text.txt', 'table3.jpg')}
        denied_paths.update((path / 'artifacts' / ref.removeprefix('artifact_')[:2] / ref.removeprefix('artifact_')).resolve() for ref in artifacts)
        def guarded_open(file, *args, **kwargs):
            if file.resolve() in denied_paths: return forbidden()
            return original_open(file, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'open', guarded_open))
            stack.enter_context(patch.object(reopened, 'get_artifact', lambda ref: forbidden() if ref in artifacts else original_get(ref)))
            for name in ('read_binding_interaction_inputs', 'populate_binding_interaction'):
                stack.enter_context(patch('gene_annotation_episode.literature_binding_interaction_storage.'+name, forbidden))
            stack.enter_context(patch.object(Image, 'open', forbidden))
            stack.enter_context(patch.object(LiteratureBindingInteractionRepository, 'receive_cells', forbidden))
            stack.enter_context(patch.object(ScientificFindingProgress, '__call__', forbidden))
            # This is the FIRST reconstructed parent projection on this new mode=ro connection.
            _, rebuilt = service_binding(reopened, parent)
            actual = rebuilt.received_report_facts(parent)['literature_binding_interaction_cells']
            assert actual == expected
            if replay:
                spec, returned, receiver, admitted = replay
                bound = replace(receiver, store=reopened, journal=Journal(reopened, run),
                    validate_semantics=forbidden, receive_references=forbidden, project_received_credit=forbidden,
                    make_controller_input=forbidden)
                with reopened.read_snapshot(): assert admit_return(spec, returned, bound) == admitted
            assert list(reopened.db.iterdump()) == before
        return {'mode_ro_before_first_projection': True, 'original_source_image_reader_calculator_receive_reprice_forbidden': True,
                'whole_sql_unchanged': True, 'native_rows_equal': len(actual), 'original_C4_replay': bool(replay)}
    finally: reopened.db.close()

class LiteratureWire(_SessionConnection):
    """Real complete/presentation implementation with explicit controlled RPC, no server."""
    def __init__(self, directory):
        config = {'connection': {'command': ['controlled-no-process']},
                  'FAST': {'model': 'controlled-fixture', 'reasoning_effort': 'low'},
                  'REASONING': {'model': 'controlled-fixture', 'reasoning_effort': 'low'}, 'routing': {}}
        super().__init__(config, directory, directory.parent); self.turns = []
    async def _rpc(self, method, params):
        if method == 'thread/start':
            return {'thread': {'id': 'controlled-thread'}, 'model': params['model'],
                    'reasoningEffort': params['config']['model_reasoning_effort']}
        assert method == 'turn/start'; self.turns.append(deepcopy(params)); turn = str(len(self.turns))
        self.pending.extend([{'method': 'item/completed', 'params': {'threadId': 'controlled-thread',
            'item': {'type': 'agentMessage', 'text': '{"fixture":true}'}}},
            {'method': 'turn/completed', 'params': {'threadId': 'controlled-thread',
            'turn': {'id': turn, 'status': 'completed'}}}])
        return {'turn': {'id': turn}}

def provider_display(parent_state, rows):
    receipts = []
    for label, components in [('all_native', list(COMPONENTS)), ('derived_only', ['interaction_ratio', 'log_interaction'])]:
        state = deepcopy(parent_state)
        subset = [deepcopy(row) for row in rows if row['component'] in components]
        if label == 'derived_only':
            # Reproject through the actual native repository contract rather than editing numeric fields.
            # Rows used here already contain raw expansions from original all-eight request; the renderer
            # must honor the current requested form and mask those expansions.
            state['requested_form'] = obj({'numbers': binding_interaction_cells_schema()})
        state['child_reports'] = [{'numbers': subset}]
        wire = LiteratureWire(OUT / ('provider_'+label))
        asyncio.run(wire.complete('controlled-parent-'+label, 'REASONING',
            'Evaluate the assigned retained reference experiment.\n'+INSTRUCTIONS, state_frame(state), obj({'fixture': {'const': True}})))
        rendered = wire.turns[0]['input'][0]['text']
        assert 'Admitted requested binding interaction components' in rendered
        assert '10.3125' in rendered and '36.339285714285715' in rendered
        if label == 'derived_only':
            for value in ('32 ± 2', '17 ± 3', '11 ± 1', '>510', '>740'):
                assert value not in rendered, value
        (OUT / ('PROVIDER_TEXT_'+label+'.txt')).write_text(rendered)
        receipts.append({'requested_display': label, 'actual_complete_and_turn_boundary': True,
                         'configured_model_called': False, 'text_sha256': hashlib.sha256(rendered.encode()).hexdigest()})
    return receipts

@dataclass(frozen=True)
class Value(ClosedRecord):
    value: dict
    def as_record(self): return self.value

def c4_fixture(image_uri):
    store, refs, args, artifacts = setup(OUT / 'c4_state', image_uri); run = 'controlled-original-c4-058'
    root_goal = EpisodeGoal.root(objective=QUESTION, result_contract={})
    child_goal = EpisodeGoal.child(root_goal, objective=QUESTION, result_contract={})
    ppath = [['annotation', 'root']]; cpath = [*ppath, ['literature', 'binding_interaction']]
    pid, cid = EpisodeRef(run, ppath).episode_id, EpisodeRef(run, cpath).episode_id
    scope = store.validate_scope(); assign = assignment(refs, ['interaction_ratio'])
    child = BindingContext(run, cid, 'literature', tuple(map(tuple, cpath)), scope, assign, {}, tuple(refs))
    parent = BindingContext(run, pid, 'annotation', tuple(map(tuple, ppath)), scope, {}, {}, tuple(refs))
    repo = LiteratureBindingInteractionRepository(store, run)
    outcome = repo.populate(child, args['7C_to_G'], 'separate-engineering-fixture-population')
    child = replace(child, received_record_refs=(*refs, *outcome['record_refs']))
    _, binding = service_binding(store, child)
    rows = binding.facts(child, {'committed_record_refs': [outcome['result']['sheet_ref']]})['literature_binding_interaction_cells']
    assert len(rows) == 1 and rows[0]['component'] == 'interaction_ratio'
    form = {'numbers': rows}
    def resolves(ref, namespace):
        return ref in store.reference_subset([ref], scope) and (namespace is None or store.get(ref)['record_type'] == namespace)
    contract = TypedReportContract(QUESTION, FORM, resolves)
    prequest = {'goal': root_goal.as_record(), 'message': {'scope': scope}, 'report_contract': None}
    request = {'goal': child_goal.as_record(), 'message': {'scope': scope, 'episode_assignment': assign}, 'report_contract': contract.as_record()}
    journal = Journal(store, run)
    for eid, path, req, state in ((pid, ppath, prequest, 'active'), (cid, cpath, request, 'yielded')):
        journal.save('runtime_episodes', {'episode_id': eid, 'path': canonical(path), 'request': canonical(req),
            'initial_credit': 0, 'state': state, 'completion': None, 'archive': None})
    spec = {'version': 'episode_commission_v1', 'handle': 'controlled-original-binding-handle-058',
        'operation_key': 'original-commission', 'run_id': run,
        'parent': {'episode_id': pid, 'goal_id': root_goal.goal_id, 'path': ppath},
        'child': {'episode_id': cid, 'role': 'literature', 'key': 'binding_interaction', 'path': cpath,
                  'request': request, 'scope': scope}, 'input_versions': [],
        'runtime_binding': {'factory_module': 'controlled_fixture', 'factory_name': 'open_commission', 'arguments': {},
                            'implementation_sha256': sha(Path(__file__)), 'settings_sha256': content_digest(assign)},
        'constraints': {}, 'resource_selection': None, 'expectation_snapshot_refs': []}
    journal.save('runtime_actions', {'episode_id': pid, 'decision_index': 7,
        'action': canonical({'kind': 'episode_child', 'role': 'literature'}),
        'result': canonical({'status': 'pending', 'pending_handle': spec['handle']}), 'credit': None})
    journal.save('runtime_forms', {'episode_id': cid, 'facts': canonical({'literature_binding_interaction_cells': rows,
        'changed_record_refs': outcome['changed_record_refs']}), 'form': canonical(form)})
    archive = JsonArchive(OUT / 'c4_archive')
    returned = {'version': 'returned_episode_v1', 'handle': spec['handle'], 'return_id': '',
        'commission_sha256': content_digest(spec), 'returned_at': '2026-10-26T12:00:00+00:00', 'outcome': 'closed',
        'completion': {'ended_by': 'yield_stop', 'end_reason': '', 'units_consumed': 1},
        'episode_archive': archive.store({'controlled_engineering_fixture': True}).descriptor(),
        'result_archive': archive.store({'form': form}).descriptor(), 'form': form,
        'facts_archive': archive.store({'literature_binding_interaction_cells': rows}).descriptor(),
        'pending_handles': [], 'failure': None}
    returned['return_id'] = content_digest({key: value for key, value in returned.items() if key != 'return_id'})
    key = run+':'+pid+':7:typed_form'
    def receive(value):
        binding.received_form_references(parent, value, FORM, key); return outcome['record_refs']
    receiver = ReceiverBindingV1(store, journal, 7, contract, lambda value: binding.validate_report(child, value, FORM),
        receive, lambda: 0, lambda index, credit: Value({'credit': credit, 'estimation_action_index': index}))
    bound = binding.services.literature_binding_interaction_repository(); original = bound.receive_cells
    def interrupted(*a, **kw): original(*a, **kw); raise OSError('controlled interrupt after receipt')
    before_rollback = list(store.db.iterdump())
    with patch.object(bound, 'receive_cells', interrupted):
        try: admit_return(spec, returned, receiver)
        except OSError: pass
        else: raise AssertionError('Expected interruption')
    # The interrupted admission, including its new table installation, rolls back in full.
    assert repo.received_cells(parent) == []
    assert list(store.db.iterdump()) == before_rollback
    assert journal.row('runtime_actions', pid, 7)['credit'] is None
    admitted = admit_return(spec, returned, receiver)
    assert admitted['state'] == 'admitted' and admitted['report'] == form
    parent = replace(parent, received_record_refs=tuple(dict.fromkeys([*refs, *admitted['received_record_refs']])))
    assert binding.received_report_facts(parent)['literature_binding_interaction_cells'] == rows
    # Authentic source sheet has all native cells; explicit raw projection is deliberately outside original return.
    forged = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=['parameter_rr'])
    store.db.execute('UPDATE literature_binding_interaction_received SET cells=?', (canonical(forged),))
    store.db.execute('UPDATE literature_binding_interaction_delivery_bindings SET cells_digest=?', (repo._delivery_digest(forged),))
    try: repo.received_cells(parent)
    except ContractError as exc: assert 'delivery_binding_mismatch' in str(exc)
    else: raise AssertionError('Expanded raw subset admitted')
    store.db.execute('UPDATE literature_binding_interaction_received SET cells=?', (canonical(rows),))
    store.db.execute('UPDATE literature_binding_interaction_delivery_bindings SET cells_digest=?', (repo._delivery_digest(rows),))
    write('C4_ORIGINAL_COMMISSION.json', spec); write('C4_ORIGINAL_RETURN.json', returned); write('C4_ADMISSION.json', admitted)
    before = list(store.db.iterdump()); path = store.path; store.close()
    readonly = reconstruct(path, run, parent, rows, artifacts, before, (spec, returned, receiver, admitted))
    receipt = {'kind': 'separate_controlled_original_C4_engineering_fixture', 'actual_detached_model_run': False,
        'actual_shared_method_loop_observations': 0, 'original_typed_parent_decision_index': 7,
        'interrupt_after_receipt_transaction_rollback': True, 'authentic_original_admission': True,
        'expanded_subset_recomputed_digest_rejected': True, 'read_only_replay': readonly,
        'scientific_credit': 0, 'meaning': 'Admission/reconstruction engineering fixture, distinct from selected blocking run'}
    write('C4_RECEIPT.json', receipt)
    return receipt

def main():
    OUT.mkdir(exist_ok=False)
    write('IMPORT_PROVENANCE_BEFORE.json', verify_pin())
    image_uri = source_proof()
    selected = ordinary_run(image_uri)
    c4 = c4_fixture(image_uri)
    write('IMPORT_PROVENANCE_AFTER.json', verify_pin())
    write('TERMINAL_RECEIPT.json', {'passed': True, 'selected': selected, 'separate_C4': c4,
        'limits': ['Controlled provider choices and continuation; no actual configured-model science',
                   'IC50 competition discrimination under two reported protein inputs 22/20 nM',
                   'No intrinsic Kd, common-condition mutation-only, physiological or annotation-transfer claim',
                   'Fit SD is not independent parameter SD/covariance; word count reader unsupported remains null',
                   'Existing eight native components only; not full A105, router, W05 or new scoring sheet']})
    print(json.dumps({'passed': True, 'native_rows': 16, 'observations': 4, 'scientific_credit': 0,
                      'read_only': True, 'original_C4_fixture': True}))

if __name__ == '__main__':
    main()
