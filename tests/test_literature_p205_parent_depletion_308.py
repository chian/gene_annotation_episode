"""Selected A105 P205 parent-removal section from an original author workbook."""
import asyncio
from copy import deepcopy
from functools import partial
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a105_worksheet import a105_worksheet_template, VERSION
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt, EXPERIMENTAL_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.literature_parent_depletion_inputs import (
    VERSION as INPUT_VERSION, read_parent_depletion_inputs)
from gene_annotation_episode.literature_parent_depletion_calculations import populate_parent_depletion_components
from gene_annotation_episode.literature_parent_depletion_prompt import PARENT_DEPLETION_TASK
from gene_annotation_episode.literature_parent_depletion_storage import (
    LiteratureParentDepletionRepository, NAMESPACE, COMPONENTS)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController

SOURCE=Path(__file__).resolve().parents[1]/'verification/a105_matched_control_primary_306/source/amidase-paper/data/PLA55254_P205_subtrate_specificity_screening.xlsx'
ARTICLE=Path(__file__).resolve().parents[1]/'verification/a105_matched_control_primary_306/source/PMC11741061.xml'
PIN='24d5734e8a8643ab20306a1725843686460761362cb85a9ef0c1e6c25304a2ae'
TEMPLATE=a105_worksheet_template([{'field':'depletion','source':NAMESPACE,'components':list(COMPONENTS)}])
FORM=TEMPLATE['submitted_form']
EMPTY={'version':VERSION,'assertion_refs':[],'quantity_links':[],'assertion_links':[]}


def _selection(source_ref):
    return {'version':INPUT_VERSION,'source_ref':source_ref,'expected_sha256':PIN,
        'sheet_name':'summary','compound':'Capecitabine','submix':'Sub7','time_hours':24}


def _source(store,raw):
    artifact=store.artifact(raw,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return store.put('source',{'provider':'author_workbook','accession':'10.1021/acsenvironau.4c00066',
        'uri':None,'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,
        'retrieved_at':None,'parent_source_refs':[]},origin='caller')['id']


def test_original_workbook_reader_and_difference_check():
    raw=SOURCE.read_bytes()
    assert sha256(raw).hexdigest()==PIN
    extracted=read_parent_depletion_inputs(_selection('source_test'),raw)
    assert extracted['row_number']==5
    assert extracted['values']['active']['address']=='B5'
    assert extracted['values']['reported_active_minus_abiotic']['value_origin']=='formula_cache'
    sheet=populate_parent_depletion_components(extracted)
    assert sheet['cells']['active_parent_removal']['value']==pytest.approx(.688006297783288)
    assert sheet['cells']['inactive_parent_removal']['value']==pytest.approx(.0987152898299202)
    assert sheet['cells']['abiotic_parent_removal']['value']==pytest.approx(-.0387430560522613)
    assert sheet['cells']['active_minus_inactive']['value']==pytest.approx(.589291007953367)
    assert sheet['cells']['active_minus_abiotic']['value']==pytest.approx(.726749353835549)
    assert sheet['cells']['active_minus_inactive']['input_measurement_keys'][0]==sheet['cells']['active_minus_abiotic']['input_measurement_keys'][0]
    assert sheet['cells']['active_minus_inactive']['standard_error_of_difference'] is None
    assert sheet['product_coupling_factor'] is None
    with pytest.raises(ContractError,match='parent_depletion_workbook_hash_mismatch'):
        read_parent_depletion_inputs({**_selection('source_test'),'expected_sha256':'0'*64},raw)
    with pytest.raises(ContractError,match='parent_depletion_unique_matching_row_required'):
        read_parent_depletion_inputs({**_selection('source_test'),'submix':'Sub8'},raw)
    # An internally inconsistent original workbook is not silently trusted.
    output=BytesIO()
    with zipfile.ZipFile(BytesIO(raw)) as source,zipfile.ZipFile(output,'w') as target:
        for member in source.infolist():
            content=source.read(member.filename)
            if member.filename=='xl/worksheets/sheet1.xml':
                root=ET.fromstring(content)
                namespace={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                cell=root.find('.//m:c[@r="K5"]/m:v',namespace)
                assert cell is not None
                cell.text='0.1'
                content=ET.tostring(root)
            target.writestr(member,content)
    altered=output.getvalue()
    bad=read_parent_depletion_inputs({**_selection('source_test'),'expected_sha256':sha256(altered).hexdigest()},altered)
    with pytest.raises(ContractError,match='parent_depletion_reported_difference_mismatch'):
        populate_parent_depletion_components(bad)


def test_selected_xlsx_read_population_typed_return_and_cold_reconstruction(tmp_path,monkeypatch):
    raw=SOURCE.read_bytes();assert sha256(raw).hexdigest()==PIN
    path=tmp_path/'state';store=Store(path);store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    source_ref=_source(store,raw)
    article=ARTICLE.read_bytes()
    assert sha256(article).hexdigest()=='1919a2a62baa2983b2bf9e9ccbde7c9631bdc2322c2951be68ecc1c798da4e1e'
    article_artifact=store.artifact(article,'application/xml')
    article_ref=store.put('source',{'provider':'original_article_xml','accession':'10.1021/acsenvironau.4c00066',
        'uri':None,'artifact_ref':article_artifact,'text_ref':article_artifact,'request_ref':None,
        'version':None,'retrieved_at':None,'parent_source_refs':[]},origin='caller')['id']
    assignment={'version':'literature_assignment_v1','question_context_refs':[],
        'source_refs':[source_ref,article_ref],**TEMPLATE['assignment_rosters']}
    def commission(role, selected_assignment):
        return {'selection':{'kind':'episode_child','role':role,'assignment':selected_assignment,
            'goal':'Assess purified P205 capecitabine parent depletion against S146A and abiotic controls',
            'scope':store.validate_scope(),
            'purpose':'Return requested source-bound A105 numerical parent-removal section',
            'schema_json':json.dumps(FORM),'initial_report_json':json.dumps({'assessment_context':EMPTY})},
            'report_update':{'assessment_context':EMPTY}}
    empty_commit={key:[] for key in store.reasoning_schema()['required']}
    start=article.index(b'P205')
    empty_commit['source_subjects']=[{'alias':'assayed_p205','reference_type':'assay',
        'source_ref':article_ref,'label':'P205','anchor':{'source_ref':article_ref,
            'artifact_ref':article_artifact,'start':start,'end':start+4,'quote':'P205'}}]
    class Provider:
        def __init__(self):self.calls={};self.contexts=[];self.prompts=[];self.released=[]
        async def complete(self,episode_id,role,instructions,context,output_schema):
            assert role=='REASONING'
            self.contexts.append(deepcopy(context))
            self.prompts.append((deepcopy(context),instructions))
            index=self.calls.get(episode_id,0);self.calls[episode_id]=index+1
            if 'reference_evidence_parent' in context:
                if index==0:return commission('literature',assignment)
                if context['child_reports']:
                    assert len(context['child_reports'][0]['depletion'])==len(COMPONENTS)
                    return {'selection':{'kind':'reason','commit':empty_commit},
                        'report_update':{'assessment_context':EMPTY}}
                if not context['pending_work']['items']:
                    raise AssertionError('closed_child_without_report '+repr({k:context.get(k) for k in ('feedback','child_reports','report_deliveries','report_lifecycle','literature_owned_population_sources')}))
                pending,=context['pending_work']['items']
                return {'selection':{'kind':'wait','condition':{'version':'event_condition_v1',
                    'events':[{'handle':pending['handle'],'event':'returned','after_cursor':0}],
                    'reconsider_at':None}},'report_update':{'assessment_context':EMPTY}}
            if index==0:
                return {'selection':{'kind':'tool','tool':'literature.parent_depletion.populate',
                    'arguments':_selection(source_ref)},'report_update':{'assessment_context':EMPTY}}
            return {'selection':{'kind':'reason','commit':empty_commit},
                'report_update':{'assessment_context':EMPTY}}
        async def release(self,episode_id):self.released.append(episode_id)
    provider=Provider()
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,
            run_dir=tmp_path/'run',controller_factory=lambda p,initial:FixtureController(str(p),initial,2),
            project_credit=scorer,initial_known_record_refs=[source_ref,article_ref],
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                parent_depletion_population=True,reference_parent_sources=[source_ref]),),
            binding_definitions={'credit':scorer.as_record()}))
        assert summary['credit']==0
        assert len(provider.contexts) in (4,5)
        child_prompts=[render_literature_experimental_prompt(context,instructions)
            for context,instructions in provider.prompts if 'literature_assignment' in context]
        assert child_prompts and all(text.startswith('TASK\n\n') and PARENT_DEPLETION_TASK in text
            and EXPERIMENTAL_TASK in text for text in child_prompts)
        parent_steering=[render_literature_experimental_prompt(context,instructions)
            for context,instructions in provider.prompts if context.get('child_reports')]
        assert parent_steering and any('Requested parent-removal numerical components' in text
            and 'Mutant protein amount equality' in text
            and 'Both active-control differences reuse the same active measurement' in text
            and all(component in text for component in COMPONENTS)
            and text.startswith('TASK\n\n' + REFERENCE_PARENT_TASK)
            for text in parent_steering)
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] in (4,5)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] in (4,5)
        operation=store.db.execute('SELECT run_id,outcome FROM literature_parent_depletion_operations').fetchone()
        assert operation is not None
        run_id=operation['run_id'];sheet_ref=json.loads(operation['outcome'])['result']['sheet_ref']
        repo=LiteratureParentDepletionRepository(store,run_id)
        saved=repo.read(sheet_ref)
        assert saved['extraction']['values']['active']['address']=='B5'
        assert saved['extraction']['values']['reported_active_minus_abiotic']['value_origin']=='formula_cache'
        received=store.db.execute('SELECT cells FROM literature_parent_depletion_received').fetchone()
        assert received is not None
        delivered=json.loads(received['cells'])
        assert delivered==repo.project_cells([sheet_ref],permitted_record_refs=[sheet_ref],components=COMPONENTS)
        values={r['component']:r['value'] for r in delivered}
        assert values['active_minus_inactive']==pytest.approx(.589291007953367)
        assert values['active_minus_abiotic']==pytest.approx(.726749353835549)
        assert all(r['product_identity_for_studied_enzyme']=='unknown' for r in delivered)
        assert all(r['standard_error_of_difference'] is None for r in delivered)
        before=list(store.db.iterdump());source_artifact=store.get(source_ref)['artifact_ref']
    finally:
        store.close()
    def forbidden(*_args,**_kwargs):raise AssertionError('cold read must use saved sheet only')
    monkeypatch.setattr('gene_annotation_episode.literature_parent_depletion_storage.read_parent_depletion_inputs',forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_parent_depletion_storage.populate_parent_depletion_components',forbidden)
    with Store(path) as reopened:
        original_get=reopened.get_artifact
        monkeypatch.setattr(reopened,'get_artifact',lambda ref:forbidden() if ref==source_artifact else original_get(ref))
        reopened.db.execute('PRAGMA query_only=ON')
        cold=LiteratureParentDepletionRepository(reopened,run_id)
        assert cold.read(sheet_ref)==saved
        assert cold.project_cells([sheet_ref],permitted_record_refs=[sheet_ref],components=COMPONENTS)==delivered
        assert list(reopened.db.iterdump())==before
