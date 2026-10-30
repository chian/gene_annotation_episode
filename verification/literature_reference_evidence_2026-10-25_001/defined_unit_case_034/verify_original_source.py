"""Controlled actual-source verification; no model, production edits, or live state."""
from pathlib import Path
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
import sys
from types import SimpleNamespace

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = BASE.parents[1]
PIN = BASE / 'literature_model_run_030/pin_001'
INPUT = BASE / 'literature_model_run_024/pin_001/inputs'
sys.path.insert(0, str(PIN))
sys.path.insert(1, str(PIN / 'tests'))
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_native_inputs import read_rate_source_inputs, validate_native_selection
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository, COMPONENTS, rate_source_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

sha = lambda raw: hashlib.sha256(raw).hexdigest()
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

RAW = (INPUT / 'PRIMARY_ARTICLE_TEXT_001.txt').read_bytes()
HTML = (INPUT / 'PRIMARY_PMC_001.html').read_bytes()
META = json.loads((INPUT / 'SOURCE_INPUT_METADATA.json').read_bytes())
assert sha(RAW) == META['sources'][0]['text']['sha256']
assert sha(HTML) == META['sources'][0]['original']['sha256']

def w(text, source='controlled_source', *, after=0):
    token = text.encode(); start = RAW.index(token, after)
    return dict(source_ref=source, representation='text', start=start, end=start+len(token), quote=text)

def inside(outer, text):
    offset = outer['quote'].index(text)
    start = outer['start'] + len(outer['quote'][:offset].encode())
    return {**outer, 'start':start, 'end':start+len(text.encode()), 'quote':text}

def selector(witness, token):
    index = witness['quote'].index(token)
    return dict(witness=witness, number_start=index, number_end=index+len(token))

TABLE_START = RAW.index(b'TABLE 2.')
CAPTION = 'Crotonyl-CoA-dependent NADH oxidation and ferredoxin reduction catalyzed by purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri'
NOTE = 'For NADH oxidation each 1-ml assay mixture incubated at 25°C contained 50 mM Tris-HCl (pH 7.5), 0.1 mM NADH, 0.1 mM crotonyl-CoA, 5 μM FAD, 2 mM DTT, 0.01 mg purified butyryl-CoA dehydrogenase/Etf complex, and, where indicated, 20 μM ferredoxin (Fd), 0.4 U hydrogenase (Hyd) from C. pasteurianum, and/or 1 mM methyl viologen.'
BRIDGE_TABLE = 'One unit was equivalent to 1 μmol of NADH oxidized per min, 1 μmol of TTC reduced per min, or 1 μmol of H2 formed per min.'
BRIDGE_METHOD = 'One unit was defined as the oxidation of 1 μmol NADH per min.'

def arguments(source='controlled_source', definition='table'):
    W = lambda text, after=TABLE_START: w(text, source, after=after)
    endpoint = W('NADH oxidation (measured photometrically)')
    header = W('Sp act (U/mg)')
    normal = header
    note = W(NOTE)
    bridge = W(BRIDGE_TABLE if definition == 'table' else BRIDGE_METHOD)
    clause = inside(bridge, '1 μmol of NADH oxidized per min' if definition == 'table' else '1 μmol NADH per min')
    unit = dict(kind='source_defined_rate_unit', witness=inside(header, 'U/mg'), definition=dict(
        bridge=bridge, clause=clause, amount=selector(clause, '1'), amount_unit=inside(clause,'μmol'),
        time_unit=inside(clause,'min'), endpoint=endpoint, endpoint_entity=inside(endpoint,'NADH'),
        definition_entity=inside(clause,'NADH')))
    relation = lambda value: dict(value=value, witnesses=[W(CAPTION),note])
    args=dict(input_mode='native_source_spans', source_ref=source, source_kind='primary_source',
        experiment=W(CAPTION), comparison=dict(subject_relation=relation('same'),endpoint_relation=relation('same'),
        normalization_relation=dict(value='same', witnesses=[header,note]), intended_change=inside(note,'20 μM ferredoxin (Fd)')),
        dependence=dict(value='unknown',witnesses=[]), observation_model=dict(value='none',witnesses=[]), arms={})
    for role, row_text, token in [('reference','Fd + Hyd\n7 (14)a','7'),('test','Hyd\n0.1','0.1')]:
        row=W(row_text); label=inside(row,row_text.split('\n')[0])
        args['arms'][role]=dict(subject=inside(W(CAPTION),'butyryl-CoA dehydrogenase/Etf complex'), construct=None,
            preparation=inside(note,'0.01 mg purified butyryl-CoA dehydrogenase/Etf complex'), experiment=W(CAPTION),
            label=label, condition=note, endpoint=endpoint, normalization=normal, measurement_identity=None,
            rate=dict(number=selector(row,token),unit=deepcopy(unit)), uncertainty=dict(kind='unreported',magnitude=None,
            unit=None,kind_witnesses=[],count=None,sampling_basis=dict(value='unspecified',witnesses=[])))
    return args

def read(args):
    def source(ref,representation):
        assert ref==args['source_ref']
        return dict(artifact_ref='artifact_'+sha(HTML if representation=='original' else RAW),
            content=HTML if representation=='original' else RAW)
    return read_rate_source_inputs(args,read_source=source)

def calculate(extraction):
    rows={r['arm']:r for r in extraction['rows']};model=extraction['native_context']['model']
    return populate_rate_contrast(extraction,reference_arm='reference',test_arm='test',
        reference_condition=rows['reference']['condition'],test_condition=rows['test']['condition'],
        dependence=model['dependence']['value'], observation_model=model['observation_model']['value'])

def direct_checks():
    results={}
    for choice in ('table','methods'):
        args=arguments(definition=choice)
        save('SELECTION_'+choice.upper()+'.json',args)
        extraction=read(args);validate_native_selection(args,extraction);sheet=calculate(extraction)
        save('EXTRACTION_'+choice.upper()+'.json',extraction);save('SHEET_'+choice.upper()+'.json',sheet)
        expected=dict(reference_rate=7,test_rate=.1,rate_difference=6.9,retained_fraction=.1/7,fractional_decrease=1-.1/7)
        for name,value in expected.items():assert abs(sheet['cells'][name]['value']-value)<1e-14
        for name in set(COMPONENTS)-set(expected):assert sheet['cells'][name]['value'] is None
        results[choice]={'status':'passed','cells':sheet['cells']}
    assert results['table']['cells']==results['methods']['cells']
    args=arguments()
    for arm in args['arms'].values():arm['rate']['unit']=arm['rate']['unit']['witness']
    missing=calculate(read(args));assert all(c['value'] is None for c in missing['cells'].values())
    results['undefined_unit']={'status':'preserved_unavailable','cells':missing['cells']}
    invalid=arguments();d=invalid['arms']['reference']['rate']['unit']['definition'];d['definition_entity']=inside(d['bridge'],'TTC')
    try:read(invalid)
    except ExperimentalContractError as exc:results['foreign_branch_entity']={'code':exc.code,'field':exc.field}
    else:raise AssertionError('foreign branch accepted')
    invalid=arguments();d=invalid['arms']['reference']['rate']['unit']['definition'];d['endpoint_entity']=inside(d['endpoint'],'oxidation')
    try:read(invalid)
    except ExperimentalContractError as exc:results['wrong_endpoint_entity']={'code':exc.code,'field':exc.field}
    else:raise AssertionError('different endpoint entity accepted')
    invalid=arguments();invalid['arms']['reference']['rate']['unit']['definition']['bridge']['quote']+=' '
    try:read(invalid)
    except ExperimentalContractError as exc:results['quote_mismatch']={'code':exc.code,'field':exc.field}
    else:raise AssertionError('changed quote accepted')
    bound=arguments();row=w('Fd + Hyd − crotonyl-CoA\n<0.01',after=TABLE_START)
    bound['arms']['test']['label']=inside(row,'Fd + Hyd − crotonyl-CoA')
    bound['comparison']['intended_change']=inside(row,'− crotonyl-CoA')
    save('CENSORED_SELECTION_002.json',bound)
    bound['arms']['test']['rate']['number']=selector(row,'0.01')
    limited=calculate(read(bound));assert limited['cells']['test_rate']['value'] is None
    assert limited['cells']['test_rate']['threshold']==.01 and limited['cells']['test_rate']['bound']=='lt'
    assert limited['cells']['rate_difference']['value'] is None
    results['censored_test']={'status':'limit_preserved','cells':limited['cells']}
    save('DIRECT_CHECKS.json',results)
    return results

def controlled_workflow():
    path=OUT/'controlled_001';assert not path.exists();path.mkdir()
    store=Store(path/'state');store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    original=store.artifact(HTML,'text/html');text=store.artifact(RAW,'text/plain')
    source=store.put('source',dict(provider=META['sources'][0]['provider'],accession='PMC2223550',
        uri=META['sources'][0]['uri'],artifact_ref=original,text_ref=text,request_ref=None,
        version=META['sources'][0]['version'],retrieved_at=None,parent_source_refs=[]),origin='caller')
    args=arguments(source['id']);form=obj({'requested_source_rate_cells':rate_source_cells_schema()})
    wanted=['reference_rate','test_rate','rate_difference','retained_fraction','fractional_decrease','difference_se','source_signed_index']
    assignment=dict(version='literature_assignment_v1',question_context_refs=[],source_refs=[source['id']],requested_rate_components=wanted)
    received=[];controllers=[]
    def integrate(inputs):
        report,=inputs['child_reports'];received.append(report)
        assert [r['component'] for r in report['requested_source_rate_cells']]==wanted
        anchor=inside(w(CAPTION,source['id'],after=TABLE_START),'butyryl-CoA dehydrogenase/Etf complex')
        anchor={k:v for k,v in anchor.items() if k not in ('representation',)};anchor['artifact_ref']=text
        commit={name:[] for name in store.reasoning_schema()['required']}
        commit['source_subjects']=[dict(alias='examined_complex',reference_type='assay',source_ref=source['id'],
            label=anchor['quote'],anchor=anchor)]
        return dict(selection=dict(kind='reason',commit=commit),report_update={})
    provider=ScriptedProvider([
        dict(selection=dict(kind='episode_child',role='literature',assignment=assignment,
            goal='Compare Table 2 NADH oxidation with ferredoxin plus hydrogenase against hydrogenase alone using endpoint-specific activity units.',
            scope=plain(store.validate_scope()),purpose='Return the requested native rate components with unavailable uncertainty preserved.',
            schema_json=json.dumps(form),initial_report_json='{}'),report_update={}),
        dict(selection=dict(kind='tool',tool='literature.rate.source.populate',arguments=args),report_update={}),integrate])
    def controller(path,initial):
        c=FixtureController(str(path),initial,2 if len(path)==1 else 1);controllers.append(c);return c
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=path/'run',
        controller_factory=controller,project_credit=scorer,initial_known_record_refs=[source['id']],
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True),),binding_definitions={'credit':scorer.as_record()}))
    assert len(received)==1
    assert [c.scores for c in controllers]==[[0,0],[0]]
    counts={name:store.db.execute('select count(*) from '+name).fetchone()[0] for name in
        ('runtime_actions','runtime_observations','literature_rate_operations','literature_rate_source_received','literature_rate_received','runtime_report_attempts')}
    assert counts['runtime_observations']==3 and counts['literature_rate_operations']==1
    assert counts['literature_rate_source_received']==1 and counts['literature_rate_received']==0
    assert not store.list('observation') and not store.list('assessment')
    row,=store.db.execute("select * from runtime_actions where json_extract(action,'$.tool')='literature.rate.source.populate'")
    sheet_ref=received[0]['requested_source_rate_cells'][0]['sheet_ref']
    repo=LiteratureRateRepository(store,result['run_id']);saved=repo.read(sheet_ref)
    save('CONTROLLED_RETURN.json',received[0]);save('CONTROLLED_SAVED_SHEET.json',saved)
    manifest={'kind':'controlled_actual_source_scripted_choices','actual_model_backed':False,'source_ref':source['id'],
        'original_artifact_ref':original,'text_artifact_ref':text,'counts':counts,'controller_deltas':[c.scores for c in controllers],
        'summary':result,'sheet_ref':sheet_ref,'selected_action_credit':row['credit'],
        'native_selection_contains_actual_source_numbers_only':True}
    store.close()
    reopened=Store(path/'state');repo=LiteratureRateRepository(reopened,result['run_id'])
    assert repo.read(sheet_ref)==saved
    projected=repo.source_projection().project_cells([sheet_ref],permitted_record_refs=[sheet_ref],components=wanted)
    assert projected==received[0]['requested_source_rate_cells']
    reopened.close();manifest['saved_only_reopen_equal']=True
    save('CONTROLLED_RECEIPT.json',manifest)
    return manifest

if __name__=='__main__':
    if '--output-subdirectory' in sys.argv:
        name=sys.argv[sys.argv.index('--output-subdirectory')+1]
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in name):
            raise ValueError('simple_new_output_subdirectory_required')
        OUT=OUT/name
        OUT.mkdir(exist_ok=False)
    direct_checks()
    if '--direct-only' in sys.argv:
        print(json.dumps({'direct_checks':'passed','workflow_reran':False}))
        raise SystemExit(0)
    receipt=controlled_workflow()
    imported=[]
    for name,module in sorted(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if path and (name.startswith('gene_annotation_episode') or name.startswith('method_loop') or name=='test_runtime'):
            p=Path(path).resolve();assert p.is_relative_to(PIN), (name,path)
            imported.append(dict(module=name,path=str(p),sha256=sha(p.read_bytes())))
    save('IMPORTED_GENERATION.json',dict(pin=str(PIN),manifest_sha256=sha((PIN/'SOURCE_MANIFEST.json').read_bytes()),imports=imported))
    print(json.dumps({'direct_checks':'passed','controlled':receipt['counts'],'saved_only_reopen_equal':True}))
