"""Fixed-role request declarations retain original dynamic predicate evaluation."""
from importlib import import_module
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]


@pytest.mark.parametrize('home,expected', [
    ('execution_job_submission', ('execution_handoff_refs',)),
    ('execution_job_submission/api_job_execution', ()),
    ('execution_result_acquisition', ('execution_result_refs',)),
])
@pytest.mark.parametrize('parent_role', ['sequence_homology_evidence', 'annotation', None])
def test_original_request_predicate_evaluates_even_when_fixed_child_returns_nothing(home,expected,parent_role):
    cls=import_module(AXIS+'.'+home.replace('/','.')+'.episode').ExecutionEpisode
    binding=object.__new__(cls)
    calls=[]
    binding.services=SimpleNamespace(annotation_task_required=lambda:calls.append('original-query') or True)
    parent=None if parent_role is None else SimpleNamespace(path=((parent_role,'original-parent'),))
    result=binding.required_return_sources(parent,binding.roles[0])
    assert result==(expected if parent_role=='sequence_homology_evidence' else ())
    assert calls==(['original-query'] if parent_role=='sequence_homology_evidence' else [])


def test_dynamic_predicate_failure_is_not_erased_for_native_child():
    cls=import_module(AXIS+'.execution_job_submission.api_job_execution.episode').ExecutionEpisode
    binding=object.__new__(cls)
    def original_failure():
        raise LookupError('original-commission-query-failed')
    binding.services=SimpleNamespace(annotation_task_required=original_failure)
    parent=SimpleNamespace(path=(('sequence_homology_evidence','original-parent'),))
    with pytest.raises(LookupError,match='original-commission-query-failed'):
        binding.required_return_sources(parent,'launch_api')
