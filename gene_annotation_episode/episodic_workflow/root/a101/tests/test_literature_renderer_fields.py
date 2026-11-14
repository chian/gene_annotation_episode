"""Exact own admitted source-field projection and real binding configuration."""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
import pytest
from .literature_delivery_controls import AX,record

FIELDS=(('literature_assignment','Parent assignment and selected source operands'),
        ('literature_source_custody','Representations available for selected sources'),
        ('own_literature_outcomes','Recorded own source acquisition and reading outcomes'),
        ('literature_history_meaning','Meaning of retained source-reading history'))

def renderer():return import_module(AX+'.library.literature_source_prompt').render_literature_source_prompt

@pytest.mark.parametrize('key,title',FIELDS)
@pytest.mark.parametrize('value',[None,{},[],False,0,{'claim':'Measured only in source organism α',
    'source_subject':'strain-one','target_correspondence':'unresolved','status':'failed',
    'result_ref':'original-returned-result','qualification':'No target support inferred'}])
def test_supplied_field_preserves_qualified_values_and_empty_kinds(key,title,value):
    receiver=import_module(AX+'.receiver_prompt');scientific=import_module(AX+'.scientific_process_prompt')
    state={'goal':{'objective':'Read actual sequence and coverage evidence'},key:deepcopy(value)}
    old=deepcopy(state);lookups=[{'status':'invalid','qualification':'original missing correspondence'}];original=deepcopy(lookups)
    text=renderer()(state,'Keep original requested return',lookup_results=lookups)
    assert receiver._task(state,'Keep original requested return') in text
    assert scientific.render_episode_steering(state,lookup_results=lookups) in text
    assert title+'\n\n'+scientific._values(value) in text
    assert state==old and lookups==original
    for other,heading in FIELDS:
        if other!=key:assert heading not in text

@pytest.mark.parametrize('home',record()['homes'])
def test_each_actual_private_binding_declares_own_renderer_without_changing_science(home):
    cls=import_module(AX+'.'+home.replace('/','.')+'.episode').LiteratureEpisode
    binding=cls(SimpleNamespace(),outcome_page_size=3)
    assert vars(cls)['decision_prompt_renderer'].__func__ is renderer()
    assert binding.decision_prompt_renderer is renderer() and binding.outcome_page_size==3
    assert binding.binding_path==home
    context=SimpleNamespace(role=binding.roles[0],path=((binding.roles[0],'original'),))
    assert binding.credit_projector(context) is None
    assert binding.continuation_task(context) is None
    assert binding.yield_controller(context,0.,'original-epoch') is None
    with pytest.raises(ValueError,match='positive_a101_literature_outcome_page_size_required'):
        cls(SimpleNamespace(),outcome_page_size=0)

@pytest.mark.parametrize('tree',['published_evidence_assessment','scientific_process.published_evidence_assessment'])
def test_real_tree_construction_preserves_seven_distinct_callback_owners(tree,tmp_path):
    state=import_module(AX+'.state');journal=import_module(AX+'.episode_journal');services=import_module(AX+'.episode_services')
    with state.Store(tmp_path/'state') as store:
        host=SimpleNamespace(store=store,journal=journal.Journal(store,'literal-family'),run_id='literal-family')
        bindings=import_module(AX+'.'+tree+'.episode').create_binding_tree(services.WorkflowServices(host),outcome_page_size=3)
        registry=import_module(AX+'.episode_bindings').EpisodeBindingRegistry(bindings);host.episode_bindings=registry
        assert len(bindings)==len({type(b) for b in bindings})==len({b.binding_path for b in bindings})==7
        assert all(b.decision_prompt_renderer is renderer() for b in bindings)
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==0


def test_real_declared_presenter_retains_frame_errors_and_pending_lookups():
    providers=import_module(AX+'.providers');frames=import_module(AX+'.decision_context')
    session=object.__new__(providers._SessionConnection);session.scientific_prompt_states={}
    key=('original-presenter','REASONING')
    initial={'literature_assignment':{'source_ref':'original-source','qualification':'unresolved'},
             'contract_information_profile':'operation_contract_information_v1'}
    updated={**initial,'literature_history_meaning':'Failed reads do not imply evidence absence'}
    frame=frames.state_frame(updated,initial)
    with pytest.raises(TypeError,match='previous_model_state_requires_object'):
        providers._ORIGINAL_DECLARED_PRESENTATION(session,*key,'Original',frame,renderer())
    assert session.scientific_prompt_states=={}
    bootstrap=frames.state_frame(initial)
    text,_=providers._ORIGINAL_DECLARED_PRESENTATION(session,*key,'Original',bootstrap,renderer())
    assert 'unresolved' in text and session.scientific_prompt_states[key]==initial
    bad=deepcopy(frame);bad['base_revision']='0'*64
    with pytest.raises(ValueError,match='decision_frame_base_conflict'):
        providers._ORIGINAL_DECLARED_PRESENTATION(session,*key,'Original',bad,renderer())
    assert session.scientific_prompt_states[key]==initial
    providers._ORIGINAL_DECLARED_PRESENTATION(session,*key,'Original',frame,renderer())
    assert session.scientific_prompt_states[key]==updated
    pending={'status':'invalid','qualification':'original pending qualification'}
    result={'status':'failed','qualification':'original lookup failure'}
    lookup={'version':frames.VERSION,'kind':'decision_lookup_result','result':result,'pending_contract_information':[pending]}
    seen=[]
    def actual_projection(state,instructions,*,lookup_results=()):
        seen.append(deepcopy(lookup_results));return renderer()(state,instructions,lookup_results=lookup_results)
    before=deepcopy(lookup)
    providers._ORIGINAL_DECLARED_PRESENTATION(session,*key,'Original',lookup,actual_projection)
    assert seen==[[pending,result]] and lookup==before and session.scientific_prompt_states[key]==updated
