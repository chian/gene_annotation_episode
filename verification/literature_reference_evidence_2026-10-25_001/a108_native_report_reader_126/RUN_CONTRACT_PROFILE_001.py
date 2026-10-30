"""Constructed ordinary workflow proving the existing opt-in discovery profile.

No default, scientific TASK, production source or operation is changed here.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;CANDIDATE=HERE/'candidate_001'
sys.path[:0]=[str(CANDIDATE),str(CANDIDATE/'tests')]
from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE as PROFILE
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
from gene_annotation_episode.literature_context_inputs import context_population_schema
from gene_annotation_episode.literature_context_storage import context_semantic_cells_schema
from gene_annotation_episode.literature_context_native_storage import native_observations_schema
from gene_annotation_episode.literature_context_prompt import CONTEXT_TASK
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_contract_information_runtime_059 import PresentedProvider,information
from test_literature_context_native_observations import native_fixture
from test_runtime import FixtureController
from test_runtime_decision_exchanges import select

RUN=HERE/'contract_profile_run_001';RUN.mkdir(exist_ok=False)
store,context,args,sources,recipe=native_fixture(RUN/'state')
class ActualPresented(PresentedProvider):
    async def complete(self,episode_id,role,instructions,context,output_schema):
        self.presented_calls.append(dict(episode_id=episode_id,role=role,schema_chars=len(json.dumps(output_schema))))
        return await super().complete(episode_id,role,instructions,context,output_schema)
provider=ActualPresented([]);provider.presented_calls=[]
with store:
    value=Workflow(store,ToolRegistry(store),provider,RUN/'run',context.run_id,
        lambda path,initial:FixtureController(str(path),initial,2),ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=list(context.received_record_refs),episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
            reference_parent_sources=[sources['root']['id']],contract_information_profile=PROFILE),),decision_protocol='decision_exchange_v1')
    root=value.build('annotation','root','Investigate the constructed glucose context experiment',plain(context.scope))
    assignment=dict(version='literature_assignment_v1',question_context_refs=[],source_refs=list(context.received_record_refs),
        requested_context_components=['selected_point'],requested_context_native_positions=[0])
    compact=obj(dict(context_credit={'$ref':'episode-fact:literature_context_semantic_cells'},
        native_context={'$ref':'episode-fact:literature_context_native_observations'}))
    literal=obj(dict(context_credit=context_semantic_cells_schema(),native_context=native_observations_schema()))
    empty={name:[] for name in store.reasoning_schema()['required']}
    text=store.get_artifact(sources['root']['artifact_ref']).decode()
    def reason(label):
        commit=deepcopy(empty);commit['source_subjects']=[dict(alias=label,reference_type='assay',source_ref=sources['root']['id'],label=label,
            anchor=dict(source_ref=sources['root']['id'],artifact_ref=sources['root']['artifact_ref'],start=0,end=len(text.encode()),quote=text))]
        return select(dict(selection=dict(kind='reason',commit=commit),report_update={}))
    provider.script=iter([
        information('episode.return_contract',role='literature',source='literature_context_native_observations'),
        information('episode.return_contract',role='literature',source='literature_context_semantic_cells'),
        select(dict(selection=dict(kind='episode_child',role='literature',assignment=assignment,
            goal='Assess conditional glucose availability and retain exact source observations',scope=plain(context.scope),
            purpose='Return only the chosen context credit and native position',schema_json=json.dumps(compact),initial_report_json='{}'),report_update={})),
        information('episode.operation_contract',operation='literature.context.populate'),
        select(dict(selection=dict(kind='tool',tool='literature.context.populate',arguments=json.dumps(args)),report_update={})),
        reason('context'),reason('experiment')])
    result=asyncio.run(root.run_async(value.context))
    episodes=[dict(row) for row in store.db.execute('select * from runtime_episodes')]
    child,=[row for row in episodes if len(json.loads(row['path']))==2]
    assert result.units_consumed==2
    assert json.loads(child['request'])['report_contract']['measurements']['schema']==literal
    assert json.loads(child['request'])['message']['report_contract_declaration']['submitted_schema_json']==json.dumps(compact)
    forms=[json.loads(row['form']) for row in store.db.execute('select form from runtime_report_attempts')]
    report,=forms;assert report['context_credit'][0]['value']==.5
    native,=report['native_context'];assert native['observation_position']==0 and native['lower']==1
    root_rows=value.decision_exchanges.rows(root.source.episode_id,0)
    child_rows=value.decision_exchanges.rows(child['episode_id'],0)
    results=[row['lookup_result']['result'] for row in root_rows+child_rows if row.get('lookup_result') and row['lookup_result']['status']=='completed']
    native_contract,=[r for r in results if r.get('source')=='literature_context_native_observations']
    operation,=[r for r in results if r.get('operation')=='literature.context.populate']
    assert native_contract['report_schema']==native_observations_schema()
    assert operation['input_schema']==context_population_schema()
    assert len([r for r in results if r.get('information_kind') in ('operation_contract_information_v1','return_contract_information_v1')])==3
    observations=[dict(row) for row in store.db.execute('select * from runtime_observations')]
    assert len(observations)==4 and store.db.execute('select count(*) from runtime_actions').fetchone()[0]==4
    assert store.db.execute('select count(*) from literature_context_operations').fetchone()[0]==1
    assert not store.list('observation') and not store.list('assessment')
    sizes=[]
    for i,(call,text) in enumerate(zip(provider.presented_calls,provider.rendered)):
        task,steering=text.split('\n\nSTEERING\n',1)
        scientific=call['episode_id']==child['episode_id']
        if scientific:
            assert EXPERIMENTAL_TASK in task and CONTEXT_TASK in task
        assert len(task)<150000 and len(text)<200000
        sizes.append(dict(call=i,**call,task_chars=len(task),steering_chars=len(steering),total_chars=len(text),full_scientific_task_retained=scientific))
        (RUN/f'presentation_{i:02d}.txt').write_text(text)
    assert len(sizes)==7 and sum(r['full_scientific_task_retained'] for r in sizes)==3
    proof=dict(status='passed',configuration_profile=PROFILE,decision_protocol='decision_exchange_v1',
        complete_original_context_operation_contract=True,complete_new_native_return_contract=True,parent_chosen_compact_form_expanded_exactly=True,
        selected_information_lookups=3,actual_actions=4,actual_own_runtime_observations=4,completed_context_population_operations=1,
        added_observations_from_information_lookups=0,baseline_ordinary_actions=4,baseline_ordinary_observations=4,
        full_scientific_task_retained_each_child_presentation=True,default_profile_changed=False,scientific_task_trimmed=False,
        maximum_task_chars=max(r['task_chars'] for r in sizes),maximum_prompt_chars=max(r['total_chars'] for r in sizes),calls=sizes,
        scientific_observation_records=0,assessment_records=0)
    (RUN/'proof.json').write_text(json.dumps(proof,indent=2));(RUN/'actual_typed_return.json').write_text(json.dumps(report,indent=2))
    (RUN/'selected_contracts.json').write_text(json.dumps(results,indent=2));(RUN/'runtime_observations.json').write_text(json.dumps(observations,indent=2))
    print(json.dumps({k:proof[k] for k in ('status','selected_information_lookups','actual_actions','actual_own_runtime_observations','maximum_task_chars','maximum_prompt_chars')}))
