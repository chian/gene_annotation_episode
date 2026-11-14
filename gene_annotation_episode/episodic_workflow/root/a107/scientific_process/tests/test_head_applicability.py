"""Real saved-cell annotation equivalence and scientific edge applicability.

Source population uses the original deterministic synthetic recipes. Typed cell
delivery uses the repository's explicit trusted manual admission API; this is
not a claim of a completed workflow or autonomous science.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks
from .original_applicability_fixture import OriginalReceivedEvidence, OriginalRegistry, setup_case
from . import original_applicability_fixture as originals

AXIS='a107'
def own(name):return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+AXIS+'.'+name)


class TestHeadApplicability:
    axis=AXIS
    module=ScientificHeadBoundaryChecks.module
    scientific=ScientificHeadBoundaryChecks.scientific

    def test_original_annotation_typed_sheet_and_validation(self, scientific, tmp_path):
        kwargs={'case':'matched'} if AXIS=='a107' else {'primary':False,'incomplete':True}
        store, source_context, arguments=setup_case(tmp_path/'received-cell-state',**kwargs)
        with store:
            host=SimpleNamespace(store=store,run_id=source_context.run_id,tools=own('tools').ToolRegistry(store))
            services=own('episode_services').WorkflowServices(host)
            source=own('scientific_process.published_evidence_assessment.episode').LiteratureEpisode(services)
            host.episode_bindings=own('episode_bindings').EpisodeBindingRegistry((source,))
            kind='partner' if AXIS=='a107' else 'reaction'
            outcome=asyncio.run(source.execute(source_context,'literature.'+kind+'.populate',arguments,'original-synthetic-population'))
            assert outcome['status']=='completed',outcome
            sheet=outcome['result']['sheet_ref']
            reports=own('component_axis_reports')
            field=next(iter(reports.cell_views(AXIS.upper())))
            repository=reports.repository(services,AXIS.upper(),field)
            cells=repository.project_cells([sheet],permitted_record_refs=outcome['record_refs'])[:1]
            assert len(cells)==1
            path=(('annotation','legacy_parent'),)
            episode=own('method_loop.identities').EpisodeRef(host.run_id,path).episode_id
            request={'message':{'scope':dict(source_context.scope),'episode_assignment':{}}}
            known=tuple(dict.fromkeys([*source_context.received_record_refs,*outcome['record_refs']]))
            context=own('episode_bindings').BindingContext(host.run_id,episode,'annotation',path,source_context.scope,{},request,known)
            journal=own('episode_journal').Journal(store,host.run_id)
            journal.save('runtime_episodes',{'episode_id':episode,'path':json.dumps(path),'request':json.dumps(request),
                'initial_credit':0,'state':'active','completion':None,'archive':None})
            host.receipts=own('episode_receipts').EpisodeReceipts(store,host.run_id)
            host.receipts.bind(episode,None);host.receipts.receive(episode,known,kind='initial')
            host.record_selection=lambda episode_id:own('runtime').Workflow.record_selection(host,episode_id)
            repository.receive_cells(context,cells,'explicit-manual-received-cell-fixture')
            current=scientific.binding;current.services=services
            original_type=type('OriginalHead',(OriginalReceivedEvidence,type(current)),{})
            original=object.__new__(original_type);original.__dict__.update(current.__dict__)
            before=OriginalRegistry((original,));after=own('episode_bindings').EpisodeBindingRegistry((current,))
            expected=before.received_report_facts(context)
            actual=after.received_report_facts(context)
            assert actual==expected and actual[reports.SCORING_FACT][AXIS.upper()]['numerical_results']
            sheet_view=actual[reports.SCORING_FACT][AXIS.upper()]
            assert sheet_view['combined_scientific_score'] is None
            returned=[cell for row in sheet_view['numerical_results'] for view in row['returned_views'].values() for cell in view]
            assert returned==cells
            schema=reports.report_schema(AXIS.upper())
            form={name:deepcopy(node['const']) if 'const' in node else [] if node.get('type')=='array' else 0
                for name,node in schema['properties'].items()}
            form[field]=cells
            assert before.validate_received_report(context,form,schema) is None
            assert after.validate_received_report(context,form,schema) is None
            corrupted=deepcopy(form);corrupted[field][0]['component']='not_an_original_component'
            def observe(call):
                try:call()
                except Exception as error:return type(error),str(error),getattr(error,'code',None)
                raise AssertionError('original typed validation must reject changed component identity')
            assert observe(lambda:before.validate_received_report(context,corrupted,schema))==observe(lambda:after.validate_received_report(context,corrupted,schema))
            scientific_path=context.path+(('scientific_process','role_guard'),)
            scientific_episode=own('method_loop.identities').EpisodeRef(context.run_id,scientific_path).episode_id
            scientific_context=replace(context,role='scientific_process',path=scientific_path,episode_id=scientific_episode)
            assert before.received_report_facts(scientific_context)==after.received_report_facts(scientific_context)=={}
            compatibility=own('scientific_process.received_evidence').ScientificReceivedEvidence
            assert type(current).received_report_facts is compatibility.received_report_facts
            assert type(current).validate_received_report is compatibility.validate_received_report








@pytest.mark.parametrize('child',['scientific_process','hpc_work_planning','published_evidence_assessment'])
def test_no_receipts_short_circuits_original_job_predicate(child,monkeypatch):
    module=own('scientific_process.from_child_'+child)
    def forbidden(*args):raise AssertionError('scientific parent is already known')
    workflow=SimpleNamespace(receipts=None,progress_provider=None,is_job_source=forbidden)
    assert module.receive_report(workflow,object(),{}, {},0)==[]


