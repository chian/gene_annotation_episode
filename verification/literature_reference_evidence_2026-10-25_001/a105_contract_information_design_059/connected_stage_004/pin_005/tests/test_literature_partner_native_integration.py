"""Native text spans populate the same partner cells through ordinary episodes."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_partner_calculations import COMPONENTS
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_integration import source, witness
from test_runtime import FixtureController, ScriptedProvider

BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001'
PRIMARY = BASE/'primary_pdx_partner_015'
CASES = ('primary_native', 'matched_native', 'censored_native', 'reused_native', 'unknown_identity_native', 'mixed_spread_native')
FORM = obj({'measurements': partner_cells_schema()})


def number(selected, token):
    start = selected['quote'].index(token)
    return {'witness': deepcopy(selected), 'number_start': start, 'number_end': start+len(token)}


def setup_case(path, *, case='primary_native', components=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    fields = ('subject', 'partner', 'experiment', 'endpoint', 'normalization',
              'reference_condition', 'omitted_condition', 'addback_condition', 'function')
    primary = case == 'primary_native'
    if primary:
        raw = (PRIMARY/'PUBLISHER_RESULTS_RENDERING_001.txt').read_bytes()
        method_raw = (PRIMARY/'PUBLISHER_METHODS_RENDERING_001.txt').read_bytes()
        paper = source(store, raw)
        methods = source(store, method_raw, parents=[paper['id']])
        refs = [paper['id'], methods['id']]
        w = lambda q: witness(paper['id'], raw, q)
        mw = lambda q: witness(methods['id'], method_raw, q)
        literals = dict.fromkeys(fields)
        literals.update(subject=w('Pdx1 (Rv2606c)'), partner=w('Pdx2 (Rv2604c)'),
            experiment=w('functional PLP synthase'), endpoint=mw('formation of PLP'),
            reference_condition=w('glutamine (10 mM)'),
            omitted_condition=w('Ammonium sulphate can substitute for glutamine in the absence of Pdx2.'),
            function=w('functional PLP synthase'))
        interpretations = [literals['omitted_condition']]
        identities = dict(subject=literals['subject'], partner=literals['partner'],
                          endpoint=literals['endpoint'], normalization=None)
        arms = {}
        text = raw.decode()
        for role, mean, spread, nitrogen in (('reference', '774', '58', 'glutamine'),
                                             ('omitted', '284', '33', 'Ammonium sulphate')):
            expression = f'{mean} \x02 {spread} pmol min-1 mg-1'
            start = text.index(expression)
            selected = w(expression)
            unit_start = text.index('pmol min-1 mg-1', start)
            unit = w(text[unit_start:unit_start+len('pmol min-1 mg-1')])
            arms[role] = {**deepcopy(identities), 'partner_state': 'present' if role=='reference' else 'absent',
                'conditions': {'coverage': 'partial', 'factors': [
                    {'factor': 'nitrogen_source', 'level': {'kind': 'literal', 'witness': w(nitrogen)}}]},
                'measurement_identity': None, 'origin': 'reported', 'rate': {
                    'value': number(selected, mean), 'unit': unit,
                    'spread': {'kind': 'unspecified', 'magnitude': number(selected, spread), 'witnesses': [], 'unit': None}}}
        arms['addback'] = None
    else:
        raw = (b'Tagged subject S; Partner P; product formation; per mg subject; glutamine; '
               b'All nonpartner protocol conditions are matched. W preparation; O preparation; A preparation. '
               b'Temperature 37 degC. W: 0.1 nmol/min/mg +/- 0.01 (SD). '
               b'O: 0.02 nmol/min/mg. Limit: <0.005 nmol/min/mg. A: 0.09 nmol/min/mg.')
        if case == 'mixed_spread_native':
            raw = raw.replace(b'+/- 0.01 (SD)', b'+/- 10 pmol/min/mg (SD)')
        paper = source(store, raw)
        refs = [paper['id']]
        w = lambda q: witness(paper['id'], raw, q)
        literal_quotes = ('Tagged subject S', 'Partner P', 'All nonpartner protocol conditions are matched.',
            'product formation', 'per mg subject', 'glutamine', 'glutamine', 'glutamine', 'product formation')
        literals = {field: w(q) for field, q in zip(fields, literal_quotes)}
        interpretations = [literals['experiment']]
        identities = {name: literals[name] for name in ('subject', 'partner', 'endpoint', 'normalization')}
        arms = {}
        reference_phrase = ('0.1 nmol/min/mg +/- 10 pmol/min/mg (SD)' if case == 'mixed_spread_native'
                            else '0.1 nmol/min/mg +/- 0.01 (SD)')
        for role, label, value, phrase in (('reference', 'W', '0.1', reference_phrase),
                ('omitted', 'O', '0.02', '0.02 nmol/min/mg'),
                ('addback', 'A', '0.09', '0.09 nmol/min/mg')):
            selected = w(phrase)
            spread = {'kind': 'unreported', 'magnitude': None, 'witnesses': [], 'unit': None}
            if role == 'reference':
                spread = {'kind': 'SD', 'magnitude': number(selected, '10' if case == 'mixed_spread_native' else '0.01'),
                    'witnesses': [w('SD')], 'unit': w('pmol/min/mg') if case == 'mixed_spread_native' else None}
            arms[role] = {**deepcopy(identities), 'partner_state': 'absent' if role=='omitted' else 'present',
                'conditions': {'coverage': 'complete', 'factors': [
                    {'factor': 'nitrogen_source', 'level': {'kind': 'literal', 'witness': w('glutamine')}},
                    {'factor': 'temperature', 'level': {'kind': 'number',
                        'selector': number(w('Temperature 37 degC'), '37'), 'unit_witness': w('degC')}}]},
                'measurement_identity': w(label+' preparation'), 'origin': 'synthetic',
                'rate': {'value': number(selected, value), 'unit': w('nmol/min/mg'), 'spread': spread}}
        if case == 'censored_native':
            arms['omitted']['rate']['value'] = number(w('<0.005 nmol/min/mg'), '0.005')
        elif case == 'reused_native':
            arms['addback']['rate'] = deepcopy(arms['reference']['rate'])
            arms['addback']['measurement_identity'] = deepcopy(arms['reference']['measurement_identity'])
        elif case == 'unknown_identity_native':
            for arm in arms.values():
                arm['measurement_identity'] = None
    args = {'source_ref': paper['id'], 'data_source_ref': paper['id'],
        'source_kind': 'primary_source' if primary else 'synthetic_fixture',
        'input_mode': 'native_source_spans', 'literals': literals,
        'interpretation_witnesses': interpretations, 'arms': arms}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_partner_components': list(COMPONENTS if components is None else components)}
    context = BindingContext('native-partner-run', 'native-partner-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def check_rows(rows, case):
    assert [r['component'] for r in rows] == list(COMPONENTS)
    if case == 'primary_native':
        assert [r['value'] for r in rows] == [774, 284, None, None, None, None, None, None]
        assert rows[3]['unavailable_reason'] == 'nonpartner_conditions_differ'
        assert rows[0]['arm_metadata']['reference']['spread'] == {'kind':'unspecified', 'magnitude':58}
        assert rows[0]['arm_metadata']['omitted']['spread'] == {'kind':'unspecified', 'magnitude':33}
    elif case in ('matched_native', 'mixed_spread_native'):
        assert [r['value'] for r in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
    elif case == 'censored_native':
        assert rows[1]['value'] is None and rows[1]['upper'] == 5
        assert rows[6]['lower'] == pytest.approx(85/95) and rows[6]['upper'] == pytest.approx(.9)
    elif case == 'reused_native':
        assert rows[4]['value'] == .8
        assert rows[6]['unavailable_reason'] == 'role_measurement_not_distinct'
    else:
        assert [r['value'] for r in rows[:3]] == [100,20,90]
        assert all(r['unavailable_reason']=='measurement_identity_unreported' for r in rows[3:])
    assert all(r['unit']=='pmol/min/mg' for r in rows[:2])
    assert all(r['partner_necessity']=='not_inferred' for r in rows)
    assert all(r['statistical_uncertainty']=='not_evaluated' for r in rows)
    if case != 'primary_native':
        assert rows[0]['arm_metadata']['reference']['spread'] == {'kind':'SD', 'magnitude':10}


@pytest.mark.parametrize('case', CASES)
def test_native_selected_and_saved_only_reconstruction_without_prepared_json(tmp_path, monkeypatch, case):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    store, context, args = setup_case(tmp_path, case=case)
    with store:
        assert all(not store.get_artifact(store.get(ref)['artifact_ref']).lstrip().startswith(b'{')
                   for ref in context.received_record_refs)
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.partner.source.populate', args, 'native'))
        assert outcome['status']=='completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs,*outcome['record_refs']))
        selected = {'committed_record_refs':[outcome['result']['sheet_ref']]}
        form = form_with_facts({}, FORM, binding.facts(current, selected))
        binding.validate_report(current, form, FORM)
        check_rows(form['measurements'], case)
        repo = LiteraturePartnerRepository(store, context.run_id)
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['version']=='literature_partner_inputs_extraction_v2'
        if case != 'primary_native':
            evidence = saved['extraction']['native_evidence']['reference']['rate']
            assert evidence['value']['raw_number']=='0.1'
            assert evidence['unit']['raw_unit']=='nmol/min/mg'
            assert evidence['canonical_value']==100
        restored, = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None, descriptors=[binding.as_record()],
            job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        # Capture complete original operation map before disabling source helpers.
        catalog = restored.catalog(context)
        restored.catalog = lambda _: deepcopy(catalog)
        sheet = store.get(outcome['result']['sheet_ref'])
        allowed = {sheet['artifact_ref'],sheet['request_ref']}
        read = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return read(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError('native source work must not rerun during saved replay')
        monkeypatch.setattr(store,'get_artifact',saved_only)
        import gene_annotation_episode.literature_partner_storage as storage
        import gene_annotation_episode.literature_partner_inputs as dispatch
        import gene_annotation_episode.literature_partner_native_inputs as native
        import gene_annotation_episode.literature_partner_source_fields as fields
        import gene_annotation_episode.literature_partner_calculations as core
        import gene_annotation_episode.literature_assay_inputs as sources
        monkeypatch.setattr(storage,'read_partner_inputs',forbidden)
        for module in (dispatch,native,fields,core):
            for name,value in list(vars(module).items()):
                if callable(value) and getattr(value,'__module__',None) in (native.__name__,fields.__name__,core.__name__):
                    monkeypatch.setattr(module,name,forbidden)
        monkeypatch.setattr(sources._Sources,'source',forbidden)
        monkeypatch.setattr(sources._Sources,'witness',forbidden)
        store.db.execute('PRAGMA query_only=ON')
        assert asyncio.run(restored.execute(context,'literature.partner.source.populate',args,'native'))==outcome
        assert form_with_facts({},FORM,restored.facts(current,selected))==form


@pytest.mark.parametrize('case', CASES)
def test_native_ordinary_typed_parent_receives_actual_source_bindings(tmp_path, case):
    store,context,args = setup_case(tmp_path/'state',case=case)
    received=[]
    with store:
        commission={'selection':{'kind':'episode_child','role':'literature','assignment':plain(context.assignment),
            'goal':'Read experimental partner rates directly from source spans','scope':plain(context.scope),
            'purpose':'Return the requested source partner components','schema_json':json.dumps(FORM),
            'initial_report_json':'{}'},'report_update':{}}
        action={'selection':{'kind':'tool','tool':'literature.partner.source.populate','arguments':args},'report_update':{}}
        def receive(inputs):
            form,=inputs['child_reports']
            check_rows(form['measurements'],case)
            refs={r['id']:r for r in inputs['working_state']['references']}
            assert refs[form['measurements'][0]['subject_ref']]['label']==('Pdx1 (Rv2606c)' if case=='primary_native' else 'Tagged subject S')
            received.append(form)
            commit={k:[] for k in store.reasoning_schema()['required']}
            paper=store.get(args['source_ref']);raw=store.get_artifact(paper['artifact_ref'])
            label='Pdx1' if case=='primary_native' else 'Tagged subject S'
            anchor=witness(paper['id'],raw,label);anchor.pop('representation');anchor['artifact_ref']=paper['artifact_ref']
            commit['source_subjects']=[{'alias':'studied_molecule','reference_type':'assay',
                'source_ref':paper['id'],'label':label,'anchor':anchor}]
            return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=ScriptedProvider([commission,action,receive]),
            run_dir=tmp_path/'run',controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 else 1),
            project_credit=scorer,initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True),),binding_definitions={'credit':scorer.as_record()}))
        assert len(received)==1 and result['credit']==0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0]==1
        assert store.db.execute('SELECT count(*) FROM literature_partner_received').fetchone()[0]==1
        assert not store.list('observation') and not store.list('assessment')


def test_native_task_repeats_across_lookup_and_restoration(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire,snapshot,complete
    first=snapshot();first['goal']['objective']='Read native partner values and preserve physical measurement identity'
    first['requested_form']=FORM
    second=deepcopy(first);second['last_local_outcome']={'status':'completed','result':{'cells':{
        'reference_rate':{'value':100,'unit':'pmol/min/mg','origin':'synthetic','status':'populated'}}}}
    lookup={'version':'decision_context_v1','kind':'decision_lookup_result','decision_index':2,'exchange_index':1,
        'result':{'status':'completed','text':'The physical measurement identity remains unresolved.'}}
    wire,reopened=LiteratureWire(tmp_path/'wire'),LiteratureWire(tmp_path/'reopened')
    async def exercise():
        await complete(wire,state_frame(first));await complete(wire,state_frame(second,first))
        await complete(wire,lookup);await complete(reopened,state_frame(second))
    asyncio.run(exercise())
    tasks=[]
    for transport in (wire,reopened):
        for turn in transport.turns_sent():
            task,_=turn['input'][0]['text'].split('\n\nSTEERING\n',1)
            assert PARTNER_TASK in task and 'Select complete numerical tokens' in task
            tasks.append(task)
    assert all(task==tasks[0] for task in tasks)
