"""Run one retained-paper conversion through ordinary typed literature returns.

Only the recipe's selectors and method meanings are authored here. Reported
numeric operands are read by the native reader from the original JATS bytes.
"""
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
CANDIDATE=HERE/'candidate_001'
sys.path[:0]=[str(CANDIDATE),str(CANDIDATE/'tests')]
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
from gene_annotation_episode.literature_context_storage import context_semantic_cells_schema
from gene_annotation_episode.literature_context_native_storage import native_observations_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_context_native_primary_126 import primary_fixture,PAPER,PAPER_HASH
from test_literature_context_meanings import reopen_read_only
from test_runtime import FixtureController,ScriptedProvider

RUN=HERE/'primary_run_001'
RUN.mkdir(exist_ok=False)
summary=[]
for host in (False,True):
    name='host_quantitative_mapping' if host else 'nominal_culture_condition'
    case=RUN/name;case.mkdir()
    store,context,args,sources,recipe=primary_fixture(case/'state',host=host)
    with store:
        assignment=dict(version='literature_assignment_v1',question_context_refs=[],source_refs=list(context.received_record_refs),
            requested_context_components=['selected_point','coverage_point'],requested_context_native_positions=[0])
        form=obj(dict(context_credit=context_semantic_cells_schema(),native_context=native_observations_schema()))
        captured={};empty={name:[] for name in store.reasoning_schema()['required']}
        root=sources['root'];anchor=next(iter(args['interpretation_witnesses']))
        def next_action(inputs,kind):
            captured[kind]=deepcopy(inputs)
            prompt=render_literature_experimental_prompt(inputs,'Assess the defined source context and preserve uncertainty')
            (case/(kind+'_prompt.txt')).write_text(prompt)
            steering=prompt.split('\n\nSTEERING\n',1)[1]
            assert 'Native context observations' in steering
            assert 'source-reported setting' in steering if not host else 'unresolved' in steering
            assert 'context_literal_' not in steering and 'context_native_measurement_' not in steering
            if kind=='parent':
                report,=inputs['child_reports'];rows=report['context_credit'];native,=report['native_context']
                points={row['component']:row['value'] for row in rows}
                assert points==dict(selected_point=None if host else 1,coverage_point=None)
                assert native['lower']==(None if host else 40) and native['reported_count'] is None
                assert native['reported_sd'] is None and native['reported_sem'] is None
                assert native['context_kind']==('sample' if host else 'growth_condition')
            commit=deepcopy(empty)
            commit['source_subjects']=[dict(alias=kind,reference_type='assay',source_ref=root['id'],label='context' if kind=='own' else 'experiment',
                anchor={k:anchor[k] for k in ('source_ref','start','end','quote')}|dict(artifact_ref=root['artifact_ref']))]
            return dict(selection=dict(kind='reason',commit=commit),report_update={})
        provider=ScriptedProvider([
            dict(selection=dict(kind='episode_child',role='literature',assignment=assignment,
                goal=('Assess quantitative mapping from cecal exposure to the culture setting' if host else
                      'Assess whether the demonstrated nominal anaerobic mucin culture condition supplies a conditional context witness'),
                scope=plain(context.scope),purpose='Return defined context components and the explicitly requested native observation',
                schema_json=json.dumps(form),initial_report_json='{}'),report_update={}),
            dict(selection=dict(kind='tool',tool='literature.context.populate',arguments=args),report_update={}),
            lambda inputs:next_action(inputs,'own'),lambda inputs:next_action(inputs,'parent')])
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=case/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,2),project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                reference_parent_sources=[root['id']]),),binding_definitions={'credit':scorer.as_record()}))
        assert set(captured)=={'own','parent'}
        observations=[dict(r) for r in store.db.execute('select * from runtime_observations')];assert len(observations)==4
        assert store.db.execute('select count(*) from literature_context_operations').fetchone()[0]==1
        assert not store.list('observation') and not store.list('assessment')
        attempt,=store.db.execute('select * from runtime_report_attempts').fetchall()
        report=captured['parent']['child_reports'][0];assert json.loads(attempt['form'])==report
        child=store.db.execute('select request from runtime_episodes where episode_id=?',(attempt['child_episode_id'],)).fetchone()
        assert json.loads(child['request'])['report_contract']['measurements']['schema']==form
        parent_row=store.db.execute('select * from runtime_episodes where json_array_length(path)=1').fetchone()
        parent=BindingContext(result['run_id'],parent_row['episode_id'],'annotation',tuple(tuple(p) for p in json.loads(parent_row['path'])),
            plain(context.scope),{},json.loads(parent_row['request']),tuple(captured['parent']['literature_received_fact_display']['received_refs']))
        sheet_ref=report['native_context'][0]['sheet_ref'];saved=store.get(sheet_ref)
        sheet=json.loads(store.get_artifact(saved['artifact_ref']))
        (case/'recipe.json').write_text(json.dumps(recipe,indent=2))
        (case/'sheet.json').write_text(json.dumps(sheet,indent=2))
        (case/'original_parent_form.json').write_text(json.dumps(form,indent=2))
        (case/'actual_typed_return.json').write_text(json.dumps(report,indent=2))
        (case/'runtime_observations.json').write_text(json.dumps(observations,indent=2))
        allowed={saved['artifact_ref'],saved['request_ref']};read=store.get_artifact;reads=[]
        def saved_only(ref):
            assert ref in allowed;reads.append(ref);return read(ref)
        def forbidden(*a,**kw):raise AssertionError('source bytes, parser, calculator, model or mutation during read-only reconstruction')
        reopen_read_only(store);store.get_artifact=saved_only
        for attr in ('artifact','put','transaction','commit_reasoning'):setattr(store,attr,forbidden)
        import gene_annotation_episode.literature_context_storage as cs
        import gene_annotation_episode.providers as providers
        old_reader,old_calc,old_model=cs.read_context_inputs,cs.populate_context_compatibility,providers.ModelConnection
        cs.read_context_inputs=cs.populate_context_compatibility=providers.ModelConnection=forbidden
        try:
            binding=LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=store,run_id=result['run_id'])),rate_population=True,
                reference_parent_sources=[root['id']])
            facts=binding.received_report_facts(parent)
            assert facts['literature_context_native_observations']==report['native_context']
            display=binding._received_fact_display_context(parent)
            assert display['literature_received_fact_display']['records']==captured['parent']['literature_received_fact_display']['records']
            assert store.db.total_changes==0
            assert [dict(r) for r in store.db.execute('select * from runtime_observations')]==observations
            assert json.loads(store.db.execute('select form from runtime_report_attempts').fetchone()[0])==report
        finally:cs.read_context_inputs,cs.populate_context_compatibility,providers.ModelConnection=old_reader,old_calc,old_model
        proof=dict(case=name,status='passed',paper_sha256=PAPER_HASH,original_source_bytes_retained=True,
            scalar_reader_from_original_selectors=True,actual_runtime_observations=len(observations),completed_population_operations=1,
            scientific_observation_records=0,assessment_records=0,original_parent_form_preserved=True,
            native_observations_received=1,read_only_reconstruction=True,read_only_database_changes=store.db.total_changes,
            reconstruction_artifact_reads=len(reads),reconstruction_original_source_reads=0,
            expected_selected_point=None if host else 1,expected_coverage_point=None,
            scope='quantitative host mapping unresolved' if host else 'single demonstrated nominal culture setting only')
        (case/'proof.json').write_text(json.dumps(proof,indent=2));summary.append(proof)
(RUN/'summary.json').write_text(json.dumps(dict(paper_path=str(PAPER),cases=summary,claim='Scripted ordinary-boundary engineering verification using one real retained primary paper; no target annotation/model investigation'),indent=2))
print(json.dumps(dict(status='passed',cases=len(summary),runtime_observations=sum(r['actual_runtime_observations'] for r in summary),
    original_typed_returns=2,read_only_reconstructions=2)))
