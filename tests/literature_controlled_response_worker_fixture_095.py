"""Constructed source bytes and scripted ordinary episodes, never a live model."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

from method_loop import EpisodeCompletion
from method_loop.durable import canonical, content_digest, validate_commission
from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.domain import obj
from gene_annotation_episode.independent_execution import _check_assignment, implementation_sha256
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import ReleasingContext, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController
from test_literature_controlled_response_v3_inputs import Fixture

OPERATION = 'literature.controlled_response.source_v3.populate'
SOURCE = 'literature_controlled_response_component_cells'


def make_case(directory, *, unresolved=False, names=None, views=None, keys=None, alter_fixture=None):
    fixture = Fixture(companion=unresolved, joints=unresolved)
    if unresolved:
        # Two explicit scientific alternatives with equal values must survive.
        fixture.args['companion_readings'][0]['reading'] = deepcopy(fixture.args['arms']['protein_condition1'])
        old = fixture.args['companion_readings'][0]['reading_key']
        new = 'same:reading / α'
        fixture.args['companion_readings'][0]['reading_key'] = new
        for row in fixture.args['joint_reading_assignments']:
            if row['assignment']['protein_condition1'] == old:
                row['assignment']['protein_condition1'] = new
    if alter_fixture is not None:alter_fixture(fixture)
    store = Store(directory)
    store.create_problem(raw_sequence='MKWAA', molecule='protein')
    mapping = {}
    for ref, data in fixture.data.items():
        artifact = store.artifact(data)
        mapping[ref] = store.put('source', {'provider': 'constructed095', 'accession': ref, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None,
            'retrieved_at': None, 'parent_source_refs': []}, origin='caller')['id']
    def remap(value):
        if isinstance(value, dict):return {k: remap(v) for k,v in value.items()}
        if isinstance(value, list):return [remap(v) for v in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    arguments = remap(fixture.args)
    selection = {'requested_controlled_response_components': names or ['controlled_response_difference'],
        'requested_controlled_response_views': views or ['conditional' if unresolved else 'final']}
    if names == []:selection['requested_controlled_response_components'] = []
    if views == []:selection['requested_controlled_response_views'] = []
    if keys is not None:selection['requested_controlled_response_component_keys'] = keys
    return store, {'root': arguments['source_ref'], 'source_refs': list(mapping.values()),
        'scope': store.validate_scope(), 'arguments': arguments, 'selection': selection}


def binding_factory(case):
    return partial(LiteratureEpisodes, rate_population=True, controlled_response_population=True,
        controlled_response_evidence_origin='synthetic_fixture',
        reference_parent_sources=case['source_refs'], contract_information_profile=CONTRACT_INFORMATION_PROFILE)


def child_assignment(case):
    return {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': case['source_refs'], **case['selection']}


def lookup(operation, arguments):
    return {'response': {'response_type': 'request_context', 'lookup': {
        'view': 'composition_information', 'operation': operation, 'arguments': arguments}}}


def action(tool, arguments):
    return {'response': {'response_type': 'select_action', 'selection': {
        'kind': 'tool', 'tool': tool, 'arguments': arguments}, 'report_update': {}}}


def commission(case):
    compact = obj({'requested_response': {'$ref': 'episode-fact:' + SOURCE}})
    return {'response': {'response_type': 'select_action', 'selection': {
        'kind': 'episode_child', 'role': 'literature', 'assignment': child_assignment(case),
        'goal': 'Evaluate the supplied constructed protein-present and protein-free controlled comparison.',
        'scope': plain(case['scope']), 'purpose': 'Return the requested source response components with their original scientific qualifications.',
        'schema_json': json.dumps(compact), 'initial_report_json': '{}'}, 'report_update': {}}}


class Provider:
    def __init__(self, store, case, *, durable_child=False):
        self.store, self.case, self.durable_child = store, case, durable_child
        self.presenter = _SessionConnection.__new__(_SessionConnection)
        self.presenter.scientific_prompt_states = {}
        self.states, self.contexts, self.presented, self.released = {}, [], [], []

    def conversation_key(self, episode_id, role):return episode_id, 0

    def reason(self):
        commit = {field: [] for field in self.store.reasoning_schema()['required']}
        witness = self.case['arguments']['arms']['protein_condition1']['context']['subject']
        source = self.store.get(witness['source_ref'])
        commit['source_subjects'] = [{'alias':'constructed095_reference','reference_type':'assay',
            'source_ref':source['id'],'label':witness['quote'],'anchor':{
                'source_ref':source['id'],'artifact_ref':source['artifact_ref'],
                'start':witness['start'],'end':witness['end'],'quote':witness['quote']}}]
        return {'response': {'response_type': 'select_action', 'selection': {
            'kind': 'reason', 'commit': commit}, 'report_update': {}}}

    async def complete(self, episode_id, role, instructions, context, output_schema):
        text,_ = self.presenter._presentation(episode_id, role, instructions, context)
        state = deepcopy(self.presenter.scientific_prompt_states[(episode_id,role)])
        self.contexts.append(state); self.presented.append(text)
        if (state.get('last_local_outcome') or {}).get('status') == 'invalid':
            raise AssertionError('scripted fixture selected an invalid action: '+str(state['last_local_outcome']))
        if 'literature_assignment' not in state:
            if state['child_reports']:
                return self.reason()
            if state.get('pending_work',{}).get('items'):
                handle = state['pending_work']['items'][0]['handle']
                return {'response': {'response_type': 'select_action', 'selection': {'kind': 'wait',
                    'condition': {'version': 'event_condition_v1', 'events': [
                        {'handle': handle, 'event': 'returned', 'after_cursor': 0}],
                        'reconsider_at': None}}, 'report_update': {}}}
            stage = self.states.get(episode_id,0); self.states[episode_id] = stage+1
            if stage == 0:return lookup('episode.return_contract', {'role': 'literature', 'source': SOURCE})
            return commission(self.case)
        stage = self.states.get(episode_id,0); self.states[episode_id] = stage+1
        if stage == 0:
            if self.durable_child:
                deadline = asyncio.get_running_loop().time()+30
                while not self.store.db.execute('SELECT 1 FROM episode_waits WHERE outcome IS NULL').fetchone():
                    if asyncio.get_running_loop().time()>deadline:raise AssertionError('parent never selected wait')
                    await asyncio.sleep(.01)
            return action('source.read', {'source_ref': self.case['root'], 'representation': 'original', 'offset': 0, 'limit': 32})
        if stage == 1:return lookup('episode.operation_contract', {'operation': OPERATION})
        return action(OPERATION, self.case['arguments']) if stage==2 else self.reason()

    async def release(self, episode_id):self.released.append(episode_id)


class Controllers:
    def __init__(self, root_actions=2, child_actions=2):self.root_actions, self.child_actions, self.values = root_actions, child_actions, []
    def __call__(self,path,initial):
        value = FixtureController(str(path),initial,self.root_actions if len(path)==1 else self.child_actions)
        self.values.append(value); return value


def scorer():return ScientificFindingProgress(FindingProgressPolicy(1))


async def run_case(store,case,directory,*,durable=False,resume=False,child_actions=2):
    provider = Provider(store,case); controllers = Controllers(3 if durable else 2,child_actions)
    binding = None
    if durable:
        directory = Path(directory); directory.mkdir(parents=True,exist_ok=True)
        configuration = {'workspace': str(store.path.resolve()), 'directory': str(directory.resolve()),
            'case': plain(case), 'child_actions':child_actions}
        path = directory/'constructed095.json'
        if path.exists():assert path.read_text()==canonical(configuration)
        else:path.write_text(canonical(configuration))
        binding = {'factory_module': __name__, 'factory_name': 'open_commission',
            'arguments': {'configuration_file': str(path)}, 'implementation_sha256': fixture_implementation_sha256(),
            'settings_sha256': content_digest(configuration)}
    result = await run_workflow(store,ToolRegistry(store),provider=provider,run_dir=directory,resume=resume,
        controller_factory=controllers,project_credit=scorer(),initial_known_record_refs=case['source_refs'],
        episode_binding_factories=(binding_factory(case),),episode_record_receipts=True,
        decision_protocol='decision_exchange_v1',execution_binding=binding,
        binding_definitions={'credit': scorer().as_record(), 'controller': {
            'kind': 'explicit_constructed095_fixture_controller', 'root_actions': controllers.root_actions}})
    return result,provider,controllers


def fixture_implementation_sha256():
    return content_digest({'runtime': implementation_sha256(),
        'fixture': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def module_imports():
    """Actual repository modules in this process, for engineering provenance."""
    root=Path(__file__).resolve().parents[1];rows={}
    for name,module in sorted(sys.modules.items()):
        location=getattr(module,'__file__',None)
        if not location:continue
        path=Path(location).resolve()
        if path.suffix=='.py' and path.is_relative_to(root) and '.venv' not in path.parts:
            rows[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return {'evidence_class':'actual scripted095 process imports; no live-model claim',
        'python':sys.version,'runtime_implementation_sha256':implementation_sha256(),'modules':rows}


@asynccontextmanager
async def open_commission(spec):
    spec = validate_commission(spec); binding = spec['runtime_binding']
    configuration = json.loads(Path(binding['arguments']['configuration_file']).read_text())
    assert binding['implementation_sha256']==fixture_implementation_sha256()
    assert binding['settings_sha256']==content_digest(configuration)
    with Store(configuration['workspace']) as store:
        parent_goal,scope = _check_assignment(store,spec)
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',(spec['run_id'],)).fetchone()[0])
        provider = Provider(store,configuration['case'],durable_child=True)
        workflow = assemble_workflow(store,ToolRegistry(store),provider,Path(configuration['directory']),spec['run_id'],settings,
            controller_factory=Controllers(3,configuration['child_actions']),project_credit=scorer(),initial_known_record_refs=configuration['case']['source_refs'],
            episode_record_receipts=True,episode_binding_descriptors=settings['episode_bindings'],execution_binding=binding)
        child = spec['child']; message = child['request']['message']; contract = workflow.returned_request(spec).report_contract
        episode = workflow.build(child['role'],child['key'],child['request']['goal']['objective'],scope,
            parent=parent_goal,parent_path=tuple(tuple(p) for p in spec['parent']['path']),contract=contract,
            initial=message['initial_report'],episode_assignment=message['episode_assignment'],
            report_contract_declaration=message['report_contract_declaration'])
        assert episode.request.as_record()==child['request']
        context = ReleasingContext.from_commission(tree=workflow.tree,run_id=spec['run_id'],
            parent_path=spec['parent']['path'],parent_goal_id=parent_goal.goal_id,
            child_goal_id=episode.goal.goal_id,grain=child['role'],key=child['key'])
        workflow.context = context
        def pack(record,result):
            facts = json.loads(workflow.journal.row('runtime_forms',child['episode_id'])['facts']);facts.pop('interpretations',None)
            return {'completion': EpisodeCompletion.from_record(record).as_record(),
                'episode_archive': (record.archived_record or workflow.archive.store(record)).descriptor(),
                'result_archive': workflow.archive.store(result).descriptor(), 'form': result.as_record()['form'],
                'facts_archive': workflow.archive.store(facts).descriptor(), 'pending_handles': workflow.pending_handles(episode.source)}
        try:yield {'episode': episode, 'context': context, 'pack_result': pack}
        finally:
            await workflow.release(child['episode_id'])
            Path(configuration['directory'],'worker095-presentation.json').write_text(json.dumps(provider.presented))
            Path(configuration['directory'],'worker095-imports.json').write_text(json.dumps(module_imports(),indent=2))
