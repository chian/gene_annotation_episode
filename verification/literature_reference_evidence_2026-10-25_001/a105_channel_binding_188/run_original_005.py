"""Controlled original-source execution, typed admission and cold-factory proof.

Scientific selections were inspected with this agent's post-packet reset002.
The provider and continuation counts below are engineering fixtures, not an
actual model investigation or an implemented production stopping rule.
"""
from copy import deepcopy
from dataclasses import replace
from functools import partial
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_channel_prompt import CHANNEL_TASK
from gene_annotation_episode.literature_channel_storage import LiteratureChannelRepository, channel_cells_schema, NAMESPACE
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController
from test_contract_information_runtime_059 import PresentedProvider, information
from test_runtime_decision_exchanges import select


REQUEST = ['chord_conductance', 'charge_equivalent_rate', 'chord_conductance_variance']
FORM = obj({'electrical_sections': channel_cells_schema()})


def write(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def hashes(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in path.rglob('*') if p.is_file()}


def main():
    proof = HERE/'original_runtime_005'
    proof.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('original_channel_selections_187',
        HERE.parent/'a105_channel_primary_application_187/apply_original_001.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    raw, correction = module.SOURCE.read_bytes(), module.CORRECTION.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == module.EXPECTED
    assert hashlib.sha256(correction).hexdigest() == module.EXPECTED_CORRECTION
    store = Store(proof/'state'); store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    def source(content, version, accession, parents=()):
        artifact=store.artifact(content,'application/xml')
        return store.put('source', {'provider':'retained_original_elife_xml','accession':accession,
            'uri':None,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,
            'version':version,'retrieved_at':None,'parent_source_refs':list(parents)},origin='caller')['id']
    original = source(raw,'eLife.01084.v1','10.7554/eLife.01084')
    corrected = source(correction,'eLife.01700.v1','10.7554/eLife.01700',[original])
    original_records={ref:store.get(ref) for ref in (original,corrected)}
    choices = module.build_selections(raw, original)
    assignment={'version':'literature_assignment_v1','question_context_refs':[],
        'source_refs':[original,corrected],'requested_channel_components':REQUEST}
    child={'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
        'goal':'Evaluate the source electrical measurements and applicability of the two reversal arrangements.',
        'scope':store.validate_scope(),'purpose':'Return only the requested conditional electrical numerical sections with source meanings and unresolved uncertainty.',
        'schema_json':json.dumps(obj({'electrical_sections':{'$ref':'episode-fact:'+NAMESPACE}})),'initial_report_json':'{}'},'report_update':{}}
    prompts=[]; forms=[]; controllers=[]
    def selected(which):
        def action(inputs):
            inputs=provider.views[provider.current_episode]
            prompt=render_literature_experimental_prompt(inputs,'Evaluate the source electrical evidence.')
            assert CHANNEL_TASK in prompt.split('\n\nSTEERING\n')[0]
            prompts.append(prompt)
            return select({'selection':{'kind':'tool','tool':'literature.channel.populate',
                'arguments':json.dumps(choices[which])},'report_update':{}})
        return action
    def integrate(inputs):
        inputs=provider.views[provider.current_episode]
        form,=inputs['child_reports']; forms.append(deepcopy(form))
        rows=form['electrical_sections']; assert len(rows)==6
        assert rows[0]['value']==7.1146245059288535
        assert rows[3]['unavailable_reason']=='different_electrical_arrangements'
        assert rows[2]['value'] is None and rows[5]['value'] is None
        assert all(o['reading'] is None and o['spread_reading'] is None for r in rows for o in r['operands'])
        prompt=render_literature_experimental_prompt(inputs,'Evaluate the returned measurements for the supplied sequence.')
        task,steering=prompt.split('\n\nSTEERING\n')
        assert CHANNEL_TASK in task and 'Requested electrical numerical sections' in steering
        assert 'source_meanings' not in task and 'J*covariance*J_transpose; J=[' not in task
        assert all(token not in steering for token in ('1.8 pA','−200 mV','53 ± 1 mV','119 ± 3 mV','artifact_','source_'))
        prompts.append(prompt)
        molecule=rows[0]['source_meanings']['molecule']['witness']
        commit={name:[] for name in store.reasoning_schema()['required']}
        commit['source_subjects']=[{'alias':'source_fluc_ec2','reference_type':'assay',
            'source_ref':original,'label':'Fluc-Ec2','anchor':{k:molecule[k] for k in
                ('source_ref','artifact_ref','start','end','quote')}}]
        return select({'selection':{'kind':'reason','commit':commit},'report_update':{}})
    def controller(path,initial):
        c=FixtureController(str(path),initial,2); controllers.append(c); return c
    class FixtureProvider(PresentedProvider):
        # Cache only these controlled public decision frames, as the existing
        # ConversationProvider fixture does; no private model history is read.
        async def complete(self,episode_id,role,instructions,context,output_schema):
            self.current_episode=episode_id
            return await super().complete(episode_id,role,instructions,context,output_schema)
    provider=FixtureProvider([information('episode.return_contract',role='literature',source=NAMESPACE),
        select(child),information('episode.operation_contract',operation='literature.channel.populate'),
        selected('salt_gradient'),selected('incompatible_biionic_pairing'),integrate])
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=proof/'run',
        controller_factory=controller,project_credit=scorer,decision_protocol='decision_exchange_v1',initial_known_record_refs=[original,corrected],
        episode_binding_factories=(partial(LiteratureEpisodes.reference_evidence,channel_population=True,
            source_refs=[original,corrected]),),binding_definitions={'credit':scorer.as_record()}))
    assert len(forms)==1 and summary['credit']==0
    assert [c.scores for c in controllers]==[[0,0],[0,0]]
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==4
    assert store.db.execute('SELECT count(*) FROM literature_channel_operations').fetchone()[0]==2
    run_id,parent=store.db.execute('SELECT run_id,episode_id FROM literature_channel_received').fetchone()
    descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',(run_id,)).fetchone()[0])['episode_bindings']
    rows=forms[0]['electrical_sections']; refs=list(dict.fromkeys(r['sheet_ref'] for r in rows))
    repo=LiteratureChannelRepository(store,run_id); saved={ref:repo.read(ref) for ref in refs}
    assert saved[refs[0]]['extraction']['measurement_keys']['reversal_voltage']!=saved[refs[1]]['extraction']['measurement_keys']['reversal_voltage']
    assert saved[refs[0]]['sheet']['cells']['reported_conductance']['value']==7
    assert saved[refs[1]]['sheet']['cells']['reversal_voltage']['value']==119
    receiver=BindingContext(run_id,parent,'annotation',(('annotation',parent),),store.validate_scope(),{}, {},
        tuple(dict.fromkeys([original, corrected, *refs, *repo.cell_record_refs(rows)])))
    allowed={s[field] for s in store.list('source') if s['origin']=='tool' for field in ('artifact_ref','request_ref')}
    assert all(store.get(ref)==record for ref,record in original_records.items())
    write('ORIGINAL_ADMITTED_FORM_005.json',forms[0]);write('ORIGINAL_SAVED_SHEETS_005.json',saved)
    write('ORIGINAL_BINDING_DESCRIPTOR_005.json',descriptors);write('ORIGINAL_PROMPTS_005.json',prompts)
    write('ACTUAL_PROVIDER_PRESENTATIONS_005.json',provider.rendered)
    assert any('Requested recorded return declaration' in p for p in provider.rendered)
    assert any('Requested operation/return information: literature.channel.populate' in p for p in provider.rendered)
    assert all('J*covariance*J_transpose; J=[' not in p.split('\n\nSTEERING\n')[0] and 'source_meanings' not in p.split('\n\nSTEERING\n')[0] for p in provider.rendered)
    task_sizes=[len(p.split('\n\nSTEERING\n')[0]) for p in prompts]
    assert max(task_sizes)<100000
    assert all('source_meanings' not in p.split('\n\nSTEERING\n')[0] and 'J*covariance*J_transpose; J=[' not in p.split('\n\nSTEERING\n')[0] for p in prompts)
    write('ORIGINAL_SOURCE_CUSTODY_005.json',original_records)
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close(); before=hashes(proof/'state')
    def forbidden(*_a,**_k):raise AssertionError('cold reconstruction must not reacquire, parse, convert or calculate science')
    for name,functions in {
        'literature_channel_storage':('read_channel_inputs','channel_calculation_inputs','populate_channel_components'),
        'literature_channel_inputs':('read_channel_inputs','channel_calculation_inputs','_number','_read_unit','_explicit_unit','_covariance'),
        'literature_channel_calculations':('populate_channel_components','_validate','_fraction'),
        'literature_partner_source_fields':('read_source_number','convert_source_number'),
    }.items():
        imported=__import__('gene_annotation_episode.'+name,fromlist=['x'])
        for function in functions:setattr(imported,function,forbidden)
    cold=Store.__new__(Store);cold.path=proof/'state';cold._savepoint=0
    cold.db=sqlite3.connect((cold.path/'state.sqlite3').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    cold.db.row_factory=sqlite3.Row;cold.db.execute('PRAGMA query_only=ON')
    with cold:
        original_get=cold.get_artifact
        def saved_only(ref):
            assert ref in allowed,'cold factory cannot read original scientific bytes'
            return original_get(ref)
        cold.get_artifact=saved_only
        host=SimpleNamespace(store=cold,run_id=run_id,tools=None);services=WorkflowServices(host)
        restored=compose_episode_bindings(services,store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),
            execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        binding,=restored.bindings;host.episode_bindings=EpisodeBindingRegistry(restored.bindings)
        assert binding.received_report_facts(receiver)[NAMESPACE]==rows
        assert {ref:binding._channel_repository().read(ref) for ref in refs}==saved
        assert binding.as_record()==descriptors[0]
        state=binding.initial_decision_context(receiver)
        state['child_reports']=[{'electrical_sections':binding.received_report_facts(receiver)[NAMESPACE]}]
        prompt=render_literature_experimental_prompt(state,'Evaluate the returned measurements for the supplied sequence.')
        assert CHANNEL_TASK in prompt.split('\n\nSTEERING\n')[0]
        assert 'closed channel' in prompt.split('\n\nSTEERING\n')[1]
        assert cold.db.total_changes==0
    assert before==hashes(proof/'state')
    write('ORIGINAL_PROOF_RESULT_005.json',{'provider':'controlled PresentedProvider/ConversationProvider fixture','actual_model_science':False,
        'original_source_hash':module.EXPECTED,'correction_hash':module.EXPECTED_CORRECTION,
        'selected_channel_populations':2,'ordinary_runtime_observations':4,'parent_nonempty_reasoning':True,
        'typed_sections':len(rows),'conditional_chord':7.1146245059288535,'biionic_chord':'different_electrical_arrangements',
        'covariance':'unknown','native_spread':'unspecified','original_measurement_identities_distinct':True,
        'original_source_records_unchanged':True,'saved_exact_form':True,'full_task_recurred':True,
        'raw_source_and_science_disabled_before_factory':True,'cold_sqlite_writes':0,'closed_state_byte_preservation':True,
        'task_chars':task_sizes,'no_whole_numerical_template_in_task':True,'profile':'operation_contract_information_v1','metadata_lookups':2,'provider_calls':len(provider.rendered),'a105_adequacy_claim':False})
    print('Original-source selected episode, typed admission, parent reasoning and cold factory passed.')


if __name__=='__main__':main()
