"""Constructed077 inputs and scripted ordinary episodes; no scientific model.

The test-only worker reconstructs actual Workflow/ToolRegistry/descriptors and
parent-owned forms. It is distinct from production open_commission coverage.
"""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from functools import partial
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw
from method_loop import EpisodeCompletion
from method_loop.durable import canonical, content_digest, validate_commission
from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.domain import obj
from gene_annotation_episode.independent_execution import _check_assignment, implementation_sha256
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_ratio_source_storage import ratio_source_cells_schema
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import ReleasingContext, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController

FORM = obj({'requested_signal': ratio_source_cells_schema()})


def put_source(store, data, parents=()):
    artifact = store.artifact(data)
    return store.put('source', {'provider': 'constructed077', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None,
        'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')['id']


def make_case(directory):
    store = Store(directory)
    store.create_problem(raw_sequence='MKWAA', molecule='protein')
    text = ('SyntheticProtein. K426A. tagged WT. Engineering bacterium. ΔgeneX::kan. '
        'His-tagged protein residues 1–253. tagged WT counterpart. '
        '37 °C; pH 7.4. immunoblot protein-band signal. same-blot tagged WT reference. '
        'Separate replacement arms. Common signal scale. '
        'Broad copied paragraph: K426A signal 128.000 and reference 200.000.').encode()
    root = put_source(store, text)
    image = Image.new('RGB', (280, 120), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 40), '128.000', fill='black')
    draw.text((140, 40), '200.000', fill='black')
    draw.text((10, 70), '224.000', fill='black')
    buffer = BytesIO()
    Image.new('RGB', image.size, 'white').save(buffer, format='TIFF', save_all=True, append_images=[image])
    figure = put_source(store, buffer.getvalue(), [root])
    jats = put_source(store, b'<article><body><sec id="constructed"><p>SyntheticProtein was expressed at 64% (K426A) of tagged WT levels.</p></sec></body></article>', [root])
    case = {'root': root, 'figure': figure, 'jats': jats, 'source_refs': [root, figure, jats], 'scope': store.validate_scope()}
    return store, case


def selection(store, case, view_ref, *, mode='point', broad_label=False):
    text = store.get_artifact(store.get(case['root'])['artifact_ref'])
    def witness(label):
        token = label.encode(); start = text.index(token)
        return {'kind': 'text', 'source_ref': case['root'], 'representation': 'original',
            'start': start, 'end': start + len(token), 'quote': label}
    def known(value):
        return {'status': 'known', 'value': value, 'witnesses': [witness(value)]}
    fields = ('subject','variant','reference','organism','genotype','construct_variant',
        'construct_reference','preparation_variant','preparation_reference','experiment','condition','endpoint','normalization',
        'signal_kind','reference_role','arrangement','signal_use')
    comparison = {key: {'status': 'unknown','value': None,'witnesses': []} for key in fields}
    labels = {'subject':'SyntheticProtein','variant':'K426A','reference':'tagged WT',
        'organism':'Engineering bacterium','genotype':'ΔgeneX::kan',
        'construct_variant':'His-tagged protein residues 1–253','construct_reference':'tagged WT counterpart',
        'condition':'37 °C; pH 7.4','endpoint':'immunoblot protein-band signal',
        'normalization':'same-blot tagged WT reference'}
    comparison.update({key:known(value) for key,value in labels.items()})
    if broad_label:
        comparison['condition'] = known('Broad copied paragraph: K426A signal 128.000 and reference 200.000.')
    for key,value in [('signal_kind','protein_band'),('reference_role','tagged_wt_complementation'),
            ('arrangement','replacement'),('signal_use','experimental_comparability')]:
        comparison[key] = {'status':'known','value':value,'witnesses':[witness('Separate replacement arms')]}
    n = {'kind':'image','view_ref':view_ref,'region':[10,40,110,65],'quote':'128.000'}
    d = {'kind':'image','view_ref':view_ref,'region':[140,40,240,65],'quote':'200.000'}
    row = {'representation_id':'printed_pair','kind':'visual_signal_pair','selection':{
        'reading_state':'exact','candidates':[{'numerator':n,'denominator':d}], 'fragments':[],
        'signal_scale':{'value':'supported','witnesses':[witness('Common signal scale')]}},
        'comparison_relation':{'value':'supported','witnesses':[witness('Common signal scale')]},
        'physical_measurement':{'status':'unknown','value':None,'witnesses':[]},
        'reference_measurement':{'status':'unknown','value':None,'witnesses':[]}}
    rows=[row]
    if mode == 'conflict':
        other=deepcopy(row);other['representation_id']='linked_alternative'
        other['selection']['candidates'][0]['numerator'].update(quote='224.000',region=[10,70,110,95])
        row['selection']['candidates'][0]['numerator'].update(quote='200.000',region=[140,40,240,65])
        rows.append(other)
    elif mode == 'unreadable':
        other=deepcopy(row);other['representation_id']='selected_unreadable'
        other['selection'].update(reading_state='unreadable',candidates=[],fragments=[{
            'view_ref':view_ref,'region':[10,70,110,95],'raw_fragment':None}]);rows.append(other)
    elif mode == 'different':
        other=deepcopy(row);other['representation_id']='different_quantity'
        other['comparison_relation']['value']='different';rows.append(other)
    elif mode == 'unknown':
        row['comparison_relation']={'value':'unknown','witnesses':[]}
    elif mode == 'jats':
        data=store.get_artifact(store.get(case['jats'])['artifact_ref'])
        quote='64% (K426A)';start=data.index(quote.encode())
        comparison['variant']['witnesses']=[{'kind':'text','source_ref':case['jats'],'representation':'original',
            'start':start,'end':start+len(quote.encode()),'quote':quote}]
        prose=deepcopy(row);prose.update(kind='jats_percent',selection={'source_ref':case['jats'],
            'section_id':'constructed','paragraph_index':0,'expected_subject':'SyntheticProtein',
            'variant':'K426A','reference_literal':'tagged WT levels'})
        rows=[prose]
    return {'version':'relative_signal_source_selection_v2','source_ref':case['root'],
        'comparison':comparison,'representations':rows}


def binding_factory(case):
    return partial(LiteratureEpisodes, rate_population=True, ratio_source_population=True,
        ratio_source_evidence_origin='synthetic_fixture', reference_parent_sources=case['source_refs'],
        contract_information_profile=CONTRACT_INFORMATION_PROFILE)


def child_assignment(case):
    return {'version':'literature_assignment_v1','question_context_refs':[],
        'source_refs':case['source_refs'],'requested_ratio_source_components':['reported_ratio']}


def action(tool, arguments):
    return {'response':{'response_type':'select_action','selection':{'kind':'tool','tool':tool,
        'arguments':arguments},'report_update':{}}}


def commission(case):
    compact = obj({'requested_signal':{'$ref':'episode-fact:literature_ratio_source_cells'}})
    return {'response':{'response_type':'select_action','selection':{
        'kind':'episode_child','role':'literature','assignment':child_assignment(case),
        'goal':'Evaluate the constructed protein-signal comparison in separate replacement arms.',
        'scope':plain(case['scope']),'purpose':'Return only the requested source signal comparison and its scientific qualifications.',
        'schema_json':json.dumps(compact),'initial_report_json':'{}'},'report_update':{}}}


def lookup(operation, arguments):
    return {'response':{'response_type':'request_context','lookup':{
        'view':'composition_information','operation':operation,'arguments':arguments}}}


class Provider:
    """Scripted choices through actual presentation, without model transport."""
    def __init__(self, store, case, *, mode='point', broad_label=False, durable_child=False):
        self.store,self.case,self.mode,self.broad_label=store,case,mode,broad_label
        self.durable_child=durable_child
        self.presenter=_SessionConnection.__new__(_SessionConnection)
        self.presenter.scientific_prompt_states={}
        self.states={};self.contexts=[];self.presented=[];self.released=[]

    def conversation_key(self, episode_id, role):
        return (episode_id,0)

    async def complete(self, episode_id, role, instructions, context, output_schema):
        text,_=self.presenter._presentation(episode_id,role,instructions,context)
        state=deepcopy(self.presenter.scientific_prompt_states[(episode_id,role)])
        self.contexts.append(deepcopy(state));self.presented.append(text)
        if 'literature_assignment' not in state:
            if state['child_reports']:
                commit={field:[] for field in self.store.reasoning_schema()['required']}
                source=self.store.get(self.case['root'])
                commit['source_subjects']=[{'alias':'constructed_reference','reference_type':'assay',
                    'source_ref':source['id'],'label':'SyntheticProtein','anchor':{'source_ref':source['id'],
                        'artifact_ref':source['artifact_ref'],'start':0,'end':16,'quote':'SyntheticProtein'}}]
                return {'response':{'response_type':'select_action','selection':{'kind':'reason','commit':commit},'report_update':{}}}
            if state.get('pending_work',{}).get('items'):
                handle=state['pending_work']['items'][0]['handle']
                return {'response':{'response_type':'select_action','selection':{'kind':'wait','condition':{
                    'version':'event_condition_v1','events':[{'handle':handle,'event':'returned','after_cursor':0}],
                    'reconsider_at':None}},'report_update':{}}}
            stage=self.states.get(episode_id,0);self.states[episode_id]=stage+1
            if stage==0:return lookup('episode.return_contract',{'role':'literature','source':'literature_ratio_source_cells'})
            return commission(self.case)
        stage=self.states.get(episode_id,0);self.states[episode_id]=stage+1
        if stage==0:
            if self.durable_child:
                # Test synchronization only: no scientific selection is made
                # here. Wait for the parent's actually selected durable wait.
                deadline=asyncio.get_running_loop().time()+30
                while not self.store.db.execute('SELECT 1 FROM episode_waits WHERE outcome IS NULL').fetchone():
                    if asyncio.get_running_loop().time()>deadline:raise AssertionError('fixture parent never selected wait')
                    await asyncio.sleep(.01)
            return action('image.view',{'source_ref':self.case['figure'],'frame':1,'colour_conversion':'preserve'})
        if stage==1:return lookup('episode.operation_contract',{'operation':'literature.ratio.source.populate'})
        result=state['last_local_outcome']['result']
        return action('literature.ratio.source.populate',selection(self.store,self.case,result['view_ref'],
            mode=self.mode,broad_label=self.broad_label))

    async def release(self, episode_id):self.released.append(episode_id)


class Controllers:
    def __init__(self, root_actions=2):self.root_actions=root_actions;self.values=[]
    def __call__(self,path,initial):
        value=FixtureController(str(path),initial,self.root_actions if len(path)==1 else 2)
        self.values.append(value);return value


def scorer():return ScientificFindingProgress(FindingProgressPolicy(1))


async def run_case(store,case,directory,*,durable=False,mode='point',broad_label=False,resume=False):
    provider=Provider(store,case,mode=mode,broad_label=broad_label)
    controllers=Controllers(3 if durable else 2)
    binding=None
    if durable:
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        configuration={'workspace':str(store.path.resolve()),'directory':str(directory.resolve()),
            'case':plain(case),'mode':mode,'broad_label':broad_label}
        path=directory/'constructed077.json'
        if path.exists():assert path.read_text()==canonical(configuration)
        else:path.write_text(canonical(configuration))
        binding={'factory_module':__name__,'factory_name':'open_commission',
            'arguments':{'configuration_file':str(path)},'implementation_sha256':fixture_implementation_sha256(),
            'settings_sha256':content_digest(configuration)}
    result=await run_workflow(store,ToolRegistry(store),provider=provider,run_dir=directory,resume=resume,
        controller_factory=controllers,project_credit=scorer(),
        initial_known_record_refs=case['source_refs'],episode_binding_factories=(binding_factory(case),),
        episode_record_receipts=True,decision_protocol='decision_exchange_v1',execution_binding=binding,
        binding_definitions={'credit':scorer().as_record(),
            'controller':{'kind':'explicit_constructed077_fixture_controller','root_actions':controllers.root_actions}})
    return result,provider,controllers


def fixture_implementation_sha256():
    return content_digest({'runtime':implementation_sha256(),
        'fixture':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


@asynccontextmanager
async def open_commission(spec):
    """Test-only C1 factory; runs the original ordinary child, no private loop."""
    spec=validate_commission(spec)
    binding=spec['runtime_binding'];configuration=json.loads(Path(binding['arguments']['configuration_file']).read_text())
    assert binding['implementation_sha256']==fixture_implementation_sha256()
    assert binding['settings_sha256']==content_digest(configuration)
    with Store(configuration['workspace']) as store:
        parent_goal,scope=_check_assignment(store,spec)
        settings=json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',(spec['run_id'],)).fetchone()[0])
        provider=Provider(store,configuration['case'],mode=configuration['mode'],
            broad_label=configuration['broad_label'],durable_child=True)
        workflow=assemble_workflow(store,ToolRegistry(store),provider,Path(configuration['directory']),spec['run_id'],settings,
            controller_factory=Controllers(3),project_credit=scorer(),
            initial_known_record_refs=configuration['case']['source_refs'],episode_record_receipts=True,
            episode_binding_descriptors=settings['episode_bindings'],execution_binding=binding)
        child=spec['child'];message=child['request']['message'];contract=workflow.returned_request(spec).report_contract
        episode=workflow.build(child['role'],child['key'],child['request']['goal']['objective'],scope,
            parent=parent_goal,parent_path=tuple(tuple(p) for p in spec['parent']['path']),contract=contract,
            initial=message['initial_report'],episode_assignment=message['episode_assignment'],
            report_contract_declaration=message['report_contract_declaration'])
        assert episode.request.as_record()==child['request']
        context=ReleasingContext.from_commission(tree=workflow.tree,run_id=spec['run_id'],
            parent_path=spec['parent']['path'],parent_goal_id=parent_goal.goal_id,
            child_goal_id=episode.goal.goal_id,grain=child['role'],key=child['key'])
        workflow.context=context
        def pack(record,result):
            saved=workflow.journal.row('runtime_forms',child['episode_id']);facts=json.loads(saved['facts']);facts.pop('interpretations',None)
            return {'completion':EpisodeCompletion.from_record(record).as_record(),
                'episode_archive':(record.archived_record or workflow.archive.store(record)).descriptor(),
                'result_archive':workflow.archive.store(result).descriptor(),'form':result.as_record()['form'],
                'facts_archive':workflow.archive.store(facts).descriptor(),'pending_handles':workflow.pending_handles(episode.source)}
        try:yield {'episode':episode,'context':context,'pack_result':pack}
        finally:
            await workflow.release(child['episode_id'])
            Path(configuration['directory'],'worker077-presentation.json').write_text(json.dumps(provider.presented))
