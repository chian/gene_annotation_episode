"""One controlled existing AP native+precision boundary; no production edits."""
from pathlib import Path
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
import os
import sys
from types import SimpleNamespace

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[1]
PIN = REPO/'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_integration_review_256/joined_pin_008'
sys.dont_write_bytecode = True
sys.path[:] = [str(PIN), str(PIN/'tests'), *[p for p in sys.path
    if p and Path(p).resolve() not in (REPO, OWN)]]
os.chdir(PIN)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value): (OWN/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
pin_before = {str(p.relative_to(PIN)): digest(p) for p in PIN.rglob('*')
    if p.is_file() and p.name != 'GOAL.md'}
save('PIN_INPUT_HASHES_001.json', pin_before)
from test_literature_kinetic_summary_precision_binding_251 import setup, block_science, forbid
from test_literature_compiled_assay_185 import readonly
from test_runtime import FixtureController, ScriptedProvider
from gene_annotation_episode.communication import plain, validate_form, reference_resolver
from gene_annotation_episode.domain import obj, canonical
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, kinetic_cells_schema
from gene_annotation_episode.literature_kinetic_summary_precision_storage import LiteratureKineticSummaryPrecisionRepository, summary_precision_cells_schema, NAMESPACE, REQUESTED
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
import gene_annotation_episode.communication as communication
import pytest

ATTEMPT = OWN/'joint_existing_boundary_001'
ATTEMPT.mkdir(exist_ok=False)
requested = ['source_reported_parameter', 'source_reported_sd',
    'source_independent_preparation_count', 'source_statistical_estimator_count',
    'source_mean_standard_error', 'scenario_mean_variance', 'scenario_mean_standard_error']
store, ctx, args, _, _ = setup(ATTEMPT/'state', requested, actual_source=True)
for name in ('molecule', 'construct'):
    w = args['selection']['kinetic_selection']['numerator']['subject'][name]
    args['return_context'][name] = [{'start': w['start'], 'end': w['end']}]
native_args = deepcopy(args['selection']['kinetic_selection'])
assert native_args['denominator'] is None
assignment = {**plain(ctx.assignment), 'requested_kinetic_components': ['numerator_parameter']}
sources = list(ctx.received_record_refs)
literal = obj({'native_parameter': kinetic_cells_schema(), 'precision': summary_precision_cells_schema(),
    'qualification': {'type':'string','enum':['systematics_unknown']}})
captured = []
def integrate(view):
    form, = view['child_reports']; captured.append(deepcopy(form))
    assert [r['component'] for r in form['native_parameter']] == ['numerator_parameter']
    assert [r['component'] for r in form['precision']] == requested
    n = form['native_parameter'][0]; cells = {r['component']:r['cell'] for r in form['precision']}
    assert n['value'] == cells['source_reported_parameter']['value'] == .000186
    assert n['numerator']['uncertainty_values']['magnitude'] == cells['source_reported_sd']['value'] == .000006
    assert cells['source_independent_preparation_count']['value'] == 2
    assert cells['source_statistical_estimator_count']['value'] is None
    assert cells['source_mean_standard_error']['value'] is None
    assert cells['scenario_mean_variance']['value'] == 1.8e-11
    assert cells['scenario_mean_standard_error']['value'] == pytest.approx(4.242640687119285e-6)
    assert cells['scenario_mean_standard_error']['qualification'] == 'conditional_on_stipulated_assumptions'
    save('ADMITTED_JOINT_FORM_001.json', form)
    (OWN/'RECEIVING_PARENT_PROMPT_001.txt').write_text(render_literature_experimental_prompt(view, 'Evaluate these two views of the same source-reported parameter.'))
    commit = {key: [] for key in store.reasoning_schema()['required']}
    w = native_args['numerator']['subject']['construct']; artifact = store.get(w['source_ref'])['text_ref']
    commit['source_subjects'] = [{'alias':'studied_construct261','reference_type':'assay',
        'source_ref':w['source_ref'],'label':w['quote'],'anchor':{'source_ref':w['source_ref'],
            'artifact_ref':artifact,'start':w['start'],'end':w['end'],'quote':w['quote']}}]
    return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
script = [
    {'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
        'goal':'Evaluate the selected source-reported AP catalytic efficiency and its preparation/estimator precision.',
        'scope':plain(ctx.scope),'purpose':'Return both selected numerical sections, preserving source/scenario and shared-report meanings.',
        'schema_json':json.dumps(literal),'initial_report_json':json.dumps({'qualification':'systematics_unknown'})},'report_update':{}},
    {'selection':{'kind':'tool','tool':'literature.kinetic.populate','arguments':native_args},'report_update':{'qualification':'systematics_unknown'}},
    {'selection':{'kind':'tool','tool':'literature.kinetic.populate','arguments':args},'report_update':{'qualification':'systematics_unknown'}},
    integrate,
]
provider = ScriptedProvider(script)
progress = ScientificFindingProgress(FindingProgressPolicy(1))
try:
    asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=ATTEMPT/'run',
        controller_factory=lambda path,initial:FixtureController(str(path), initial, 2),
        project_credit=progress,binding_definitions={'credit':progress.as_record()},initial_known_record_refs=sources,
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=sources),)))
    assert len(captured)==1
    observations = [dict(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
    actions = [dict(r) for r in store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid')]
    assert len(observations)==4 and len(actions)==4
    assert store.db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0]==1
    assert store.db.execute('SELECT count(*) FROM literature_kinetic_summary_precision_operations').fetchone()[0]==1
    run_id,parent = store.db.execute('SELECT run_id,episode_id FROM literature_kinetic_summary_precision_received ORDER BY rowid DESC LIMIT 1').fetchone()
    original=captured[0]; nr=original['native_parameter'][0]['sheet_ref']; sr=original['precision'][0]['sheet_ref']
    native=LiteratureKineticRepository(store,run_id); summary=LiteratureKineticSummaryPrecisionRepository(store,run_id)
    ns,ss=native.read(nr),summary.read(sr)
    assert ns['selection']==ss['extraction']['selection']['kinetic_selection']==native_args
    # Prove common report ownership from exact originally selected measurement,
    # not equal floats, sheet IDs, report counts, or a fabricated preparation ID.
    nanchor=store.get(original['native_parameter'][0]['numerator']['measurement_ref'])['anchor']
    pdeps=next(r for r in original['precision'] if r['component']=='source_reported_parameter')['dependency_locations']
    assert any(all(nanchor[k]==loc[k] for k in ('source_ref','artifact_ref','start','end')) for loc in pdeps)
    descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
    receiver=replace(ctx,run_id=run_id,episode_id=parent,role='annotation',path=(('annotation',parent),),assignment={},
        received_record_refs=tuple(dict.fromkeys([*summary.cell_record_refs(original['precision']),nr,*sources,
            *(r['ref'] for r in original['native_parameter'][0]['numerator']['numeric_tokens'])])))
    allowed={store.get(ref)[key] for ref in (nr,sr) for key in ('artifact_ref','request_ref')}
    for name,value in [('ORIGINAL_SCHEMA_001.json',literal),('ORIGINAL_DESCRIPTOR_001.json',descriptors),
        ('ORIGINAL_NATIVE_SHEET_001.json',ns),('ORIGINAL_PRECISION_SHEET_001.json',ss),
        ('ORIGINAL_SELECTED_ARGUMENTS_001.json',{'native':native_args,'precision':args}),
        ('ORDINARY_OBSERVATIONS_001.json',observations),('ORDINARY_ACTIONS_001.json',actions)]: save(name,value)
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
    before={str(p.relative_to(ATTEMPT/'state')):digest(p) for p in (ATTEMPT/'state').rglob('*') if p.is_file()}
    monkeypatch=pytest.MonkeyPatch()
    try:
        block_science(monkeypatch)
        from gene_annotation_episode import literature_kinetic_storage as nstorage
        monkeypatch.setattr(nstorage,'read_kinetic_inputs',forbid)
        monkeypatch.setattr(nstorage,'populate_kinetic_contrast',forbid)
        monkeypatch.setattr(type(provider),'complete',forbid)
        communication._compiled_schema_content.cache_clear()
        with readonly(ATTEMPT/'state') as cold:
            get=cold.get_artifact
            def saved_only(ref):
                assert ref in allowed,'Original source/science bytes forbidden in cold read'
                return get(ref)
            monkeypatch.setattr(cold,'get_artifact',saved_only)
            host=SimpleNamespace(store=cold,run_id=run_id,tools=None)
            restored=compose_episode_bindings(WorkflowServices(host),store=cold,
                journal=SimpleNamespace(store=cold,run_id=run_id),execution_backend=None,
                descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
            host.episode_bindings=EpisodeBindingRegistry(restored.bindings);binding,=restored.bindings
            assert binding.as_record()==descriptors[0]
            got=binding.received_report_facts(receiver)
            assert got[NAMESPACE]==original['precision']
            assert got['literature_kinetic_cells']==original['native_parameter']
            assert binding.services.literature_kinetic_repository().read(nr)==ns
            assert binding._summary_precision_repository().read(sr)==ss
            validate_form(original,literal,reference_resolver(cold.references(ctx.scope)))
            assert cold.db.total_changes==0
        after={str(p.relative_to(ATTEMPT/'state')):digest(p) for p in (ATTEMPT/'state').rglob('*') if p.is_file()}
        assert before==after
    finally:monkeypatch.undo()
    imported=[]
    for name,module in sorted(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file:continue
        p=Path(file).resolve()
        if not p.is_file():continue
        if name.startswith(('gene_annotation_episode','method_loop','test_')):assert p.is_relative_to(PIN),(name,str(p))
        imported.append({'module':name,'path':str(p),'sha256':digest(p)})
    save('ACTUAL_IMPORTS_001.json',imported)
    assert pin_before=={str(p.relative_to(PIN)):digest(p) for p in PIN.rglob('*') if p.is_file() and p.name!='GOAL.md'}
    save('JOINT_BOUNDARY_RESULT_001.json',{'status':'passed','controlled_responses':True,'actual_model_backed_science':False,
        'pin':str(PIN),'pin_unchanged':True,'imported_modules':len(imported),'observations':len(observations),'actions':len(actions),
        'native_selected_operations':1,'summary_selected_operations':1,'new_assembly_operations':0,
        'same_original_kinetic_selection':True,'same_reported_parameter_anchor':True,'independent_verifications_inferred':False,
        'cold_first_composer':True,'cold_source_io':False,'cold_scientific_calculation':False,'cold_writes':0,
        'cold_state_byte_identical':True,'limitation':'Current native schema factory remains available for exact legacy form validation; cold reference payload validation uses the existing scoped record registry. Original actual admission was through the ordinary runtime.'})
finally:
    try:store.close()
    except Exception:pass
