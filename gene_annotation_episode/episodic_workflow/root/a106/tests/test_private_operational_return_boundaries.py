"""Actual private methods with explicit controlled API completion boundaries.

No constructor, provider, native worker, scientific result or iterator is mocked
as an executed investigation. These controls preserve each retained live return.
"""
from importlib import import_module
from types import SimpleNamespace
import pytest

PACKAGE='gene_annotation_episode.episodic_workflow.root.a106'
PARENTS=('', 'published_evidence_assessment/', 'perturbation_evidence/',
         'perturbation_evidence/published_evidence_assessment/')


def binding(home):
    cls=import_module(PACKAGE+'.'+home.replace('/','.')+'.episode').ExecutionEpisode
    return object.__new__(cls)


@pytest.mark.parametrize('parent',PARENTS)
def test_launch_keeps_child_actions_capability_catalog_and_empty_initial_refs(parent):
    value=binding(parent+'execution_job_submission')
    context=SimpleNamespace(role='launch')
    assert value.permitted_common_actions(context)==('tool','reason','child','wait','redeliver_report')
    assert [entry['name'] for entry in value.catalog(context)]==['execution.capabilities']
    assert value.initial_references(context)==[]
    wrong=SimpleNamespace(role='results')
    for callback in (value.permitted_common_actions,value.catalog,value.initial_references):
        with pytest.raises(ValueError,match='^unknown_execution_episode_role$'):
            callback(wrong)


@pytest.mark.parametrize('parent',PARENTS)
def test_api_initial_refs_do_not_read_a_results_handoff(parent):
    value=binding(parent+'execution_job_submission/api_job_execution')
    assert value.initial_references(SimpleNamespace(role='launch_api'))==[]
    with pytest.raises(ValueError,match='^unknown_execution_episode_role$'):
        value.initial_references(SimpleNamespace(role='results'))


@pytest.mark.parametrize('parent',PARENTS)
@pytest.mark.parametrize('suffix,role',[
    ('execution_job_submission/api_job_execution','launch_api'),
    ('execution_result_acquisition','results')])
def test_completion_preserves_exact_api_result_key_and_exception(parent,suffix,role):
    value=binding(parent+suffix)
    context=SimpleNamespace(role=role)
    calls=[]
    result=object()
    def completion(actual,key):
        calls.append((actual,key))
        return result
    value.api_execution=SimpleNamespace(completion_for_action=completion)
    assert value.completion_for_action(context,'original:selected:key') is result
    assert calls==[(context,'original:selected:key')]
    with pytest.raises(ValueError,match='^unknown_execution_episode_role$'):
        value.completion_for_action(SimpleNamespace(role='launch'),'wrong-role')
    assert calls==[(context,'original:selected:key')]
    error=RuntimeError('controlled original completion failure')
    def failed(actual,key):
        assert actual is context and key=='original:selected:key'
        raise error
    value.api_execution.completion_for_action=failed
    with pytest.raises(RuntimeError) as caught:
        value.completion_for_action(context,'original:selected:key')
    assert caught.value is error


@pytest.mark.parametrize('parent',PARENTS)
@pytest.mark.parametrize('suffix,role',[
    ('execution_job_submission/api_job_execution','launch_api'),
    ('execution_result_acquisition','results')])
def test_native_and_results_guidance_keep_their_actual_endpoint(parent,suffix,role):
    value=binding(parent+suffix)
    context=SimpleNamespace(role=role,assignment={'fixture':'original request'})
    validated=[]
    def validate(assignment):
        validated.append(assignment)
        return {'service':'bvbrc_appservice'}
    value._validate_request=validate
    text=value.instructions(context)
    if role=='launch_api':
        assert text.startswith('Carry out the assigned work through bvbrc_appservice using one selected operation each turn.')
        assert 'verified original handoff completion gives exact zero future credit.' in text
        assert validated==[context.assignment]
    else:
        assert text.startswith('Acquire the original selected execution results through the original handoff.')
        assert 'Only actual complete acquisition establishes this endpoint.' in text
        assert validated==[]
    assert not text.startswith('Choose which permitted concrete execution request')
    with pytest.raises(ValueError,match='^unknown_execution_episode_role$'):
        value.instructions(SimpleNamespace(role='launch',assignment={}))
