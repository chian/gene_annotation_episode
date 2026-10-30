"""Independent unbalanced synthetic design through real operations and RO factory."""
from pathlib import Path
import asyncio,json,math,sqlite3,sys
from copy import deepcopy
from fractions import Fraction
from functools import partial
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
PIN=HERE/'pin_001'
sys.dont_write_bytecode=True
sys.path[:0]=[str(PIN),str(PIN/'tests')]
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_replicate_storage import rate_replicate_cells_schema,NAMESPACE
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_rate_replicate_binding_163 import setup
from test_runtime import FixtureController,ScriptedProvider

async def main():
    dest=HERE/'controlled_001';dest.mkdir(exist_ok=False)
    selected=['reference_rate','test_rate','rate_difference','retained_fraction','fractional_decrease','paired_sample_sd','difference_se','reference_sample_sd']
    readings={'reference':{'A':[9,10,11],'B':[20],'C':[30]},'test':{'A':[8],'B':[19],'C':[25]}}
    rows=[{'arm':role,'sampling_unit':unit,'observation_id':f'{role}-{unit}-{index}', 'value':str(value)}
        for role,units in readings.items() for unit,values in units.items() for index,value in enumerate(values)]
    store,template,args=setup(dest/'state',rows=rows,requested=selected)
    captured={};schema=obj({'raw_components':rate_replicate_cells_schema()})
    with store:
        assert not store.targets()
        source=store.get(args['source_ref']);original_artifact=source['artifact_ref']
        text=store.get_artifact(original_artifact).decode();start=text.index('Measured construct')
        anchor={'source_ref':args['source_ref'],'artifact_ref':original_artifact,'start':start,'end':start+len('Measured construct'),'quote':'Measured construct'}
        commission={'selection':{'kind':'episode_child','role':'literature','assignment':plain(template.assignment),
            'goal':'Summarize the declared synthetic unbalanced technical readings and paired preparation comparison.',
            'scope':plain(template.scope),'purpose':'Return only the requested raw numerical components and design qualifications.',
            'schema_json':json.dumps(schema),'initial_report_json':'{}'},'report_update':{}}
        work={'selection':{'kind':'tool','tool':'literature.rate.replicates.populate','arguments':args},'report_update':{}}
        def parent(inputs):
            form,=inputs['child_reports'];captured['form']=deepcopy(form)
            assert [row['component'] for row in form['raw_components']]==selected
            commit={field:[] for field in store.reasoning_schema()['required']}
            commit['source_subjects']=[{'alias':'examined','reference_type':'assay','source_ref':args['source_ref'],'label':'Measured construct','anchor':anchor}]
            return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        result=await run_workflow(store,ToolRegistry(store),provider=ScriptedProvider([commission,work,parent]),
            run_dir=dest/'run',controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 else 1),
            project_credit=scorer,initial_known_record_refs=list(template.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=[args['source_ref']]),),
            binding_definitions={'credit':scorer.as_record()})
        assert result['credit']==0 and not store.list('assessment') and not store.list('observation')
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3
        attempt,=store.db.execute('SELECT * FROM runtime_report_attempts WHERE failure IS NULL').fetchall()
        assert json.loads(attempt['form'])==captured['form']
        expected=json.loads((HERE/'ROOT_ORACLE_001.json').read_text())
        by_component={row['component']:row for row in captured['form']['raw_components']}
        for name,rational in expected['expected_exact'].items():
            if name not in by_component:continue
            value=Fraction(int(rational['numerator']),int(rational['denominator']))
            assert math.isclose(by_component[name]['value'],float(value),rel_tol=1e-15),(name,by_component[name])
        for name,value in expected['expected_float'].items():
            assert math.isclose(by_component[name]['value'],value,rel_tol=1e-15),(name,by_component[name])
        first=by_component['reference_rate']
        assert first['groups']['reference']['observed']['measurement_count']==5
        assert first['groups']['reference']['observed']['sampling_unit_count']==3
        assert first['groups']['test']['observed']['measurement_count']==3
        assert first['value']==20 and first['value']!=16
        assert by_component['difference_se']['conditional_on']==['iid_unit_pairs']
        assert all('cells' not in group['observed'] and all('cells' not in unit for unit in group['observed']['units'])
            for group in first['groups'].values())
        root,=store.db.execute('SELECT episode_id,path,request FROM runtime_episodes WHERE json_array_length(path)=1').fetchall()
        run_id=attempt['run_id']
        receiver=BindingContext(run_id,root['episode_id'],'annotation',tuple(tuple(p) for p in json.loads(root['path'])),
            plain(template.scope),{},json.loads(root['request']),tuple(EpisodeReceipts(store,run_id).known(root['episode_id'])))
        descriptor=LiteratureEpisodes(None,rate_population=True,reference_parent_sources=[args['source_ref']]).as_record()
        sheet_source=store.get(first['sheet_ref']);allowed_artifacts={sheet_source['artifact_ref'],sheet_source['request_ref']}
        (dest/'original_typed_return.json').write_text(json.dumps(captured['form'],indent=2)+'\n')
        (dest/'original_descriptor.json').write_text(json.dumps(descriptor,indent=2)+'\n')
    reopened=Store.__new__(Store);reopened.path=(dest/'state').resolve();reopened._savepoint=0
    reopened.db=sqlite3.connect((reopened.path/'state.sqlite3').as_uri()+'?mode=ro',uri=True,isolation_level=None)
    reopened.db.row_factory=sqlite3.Row;reopened.db.execute('PRAGMA query_only=ON')
    reopened.db.create_function('library_scope_record',2,reopened._scope_filter_record)
    with reopened as store:
        get=store.get_artifact
        def saved_only(reference):
            assert reference in allowed_artifacts,'cold reconstruction read scientific source bytes'
            return get(reference)
        def forbidden(*a,**k):raise AssertionError('cold factory/projector repeated source parsing/statistical analysis')
        store.get_artifact=saved_only
        import gene_annotation_episode.literature_rate_replicate_storage as storage
        import gene_annotation_episode.literature_rate_replicate_inputs as inputs
        import gene_annotation_episode.literature_rate_replicate_calculations as calc
        storage.read_rate_replicate_table=storage.populate_rate_replicate_contrast=forbidden
        inputs.read_rate_replicate_table=inputs.validate_rate_replicate_extraction=forbidden
        calc.summarize_rate_replicates=calc.populate_rate_replicate_contrast=calc.validate_rate_replicate_extraction=forbidden
        services=WorkflowServices(SimpleNamespace(store=store,run_id=run_id,tools=ToolRegistry(store)))
        changes=store.db.total_changes
        restored,=compose_episode_bindings(services,store=store,journal=SimpleNamespace(store=store,run_id=run_id),
            execution_backend=None,descriptors=[descriptor],job_episodes=None,resource_estimator=None,role_credit_bindings={}).bindings
        assert restored.received_report_facts(receiver)[NAMESPACE]==captured['form']['raw_components']
        assert store.db.total_changes==changes==0
    imported={name:str(Path(module.__file__).resolve()) for name,module in list(sys.modules.items())
        if name.startswith(('gene_annotation_episode','method_loop','test_')) and getattr(module,'__file__',None)}
    assert all(Path(path).is_relative_to(PIN) for path in imported.values())
    proof={'scope':'Synthetic independent unbalanced design and real existing episode/return/RO reconstruction; not primary scientific coverage.',
        'source_only_targets':0,'source_measurement_rows':8,'experimental_units_per_arm':3,'reference_physical_measurements':5,
        'selected_population_operations':1,'original_typed_rows':len(selected),'runtime_observations':3,'annotation_credit':0,
        'mean_reference':by_component['reference_rate']['value'],'mean_test':by_component['test_rate']['value'],
        'difference':by_component['rate_difference']['value'],'conditional_paired_difference_se':by_component['difference_se']['value'],
        'cold_reconstruction':'Exact actual admitted rows; newly opened SQLite mode=ro; scientific artifacts and all raw readers/statistics blocked before first factory.',
        'imported_modules':imported}
    with (dest/'RESULT.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps({key:value for key,value in proof.items() if key!='imported_modules'},indent=2))
if __name__=='__main__':asyncio.run(main())
