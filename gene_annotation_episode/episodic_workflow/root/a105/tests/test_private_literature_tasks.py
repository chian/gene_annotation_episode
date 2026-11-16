"""Connected private task construction and identity; provider/host ports are fixtures."""
from contextlib import nullcontext
from types import SimpleNamespace
from .test_private_literature_bindings import binding
from gene_annotation_episode.episodic_workflow.root.a105 import runtime

def test_runtime_build_selects_exact_private_task(binding, monkeypatch):
    role = binding.roles[0]
    identity = SimpleNamespace(episode_id='source')
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs: identity)
    monkeypatch.setattr(runtime, 'FeedbackEpisode', lambda grain, key, source, *args, **kwargs: source)
    workflow = SimpleNamespace(context=object(), grains={role: object()}, inprocess_completion_order=None, receipts=None, scientific_process_binding=None, episode_bindings=SimpleNamespace(roles=(role,), for_path=lambda path: binding), contract_information_profile=lambda source: None, specialist=lambda source: binding, journal=SimpleNamespace(row=lambda *args: None, save=lambda *args: None), run_id='private-task', store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *args: None)), source_credit_view=lambda source: {'credit': 0}, expose_assigned_job=lambda source: None, archive=SimpleNamespace(store=lambda value: value))
    source = runtime.Workflow.build(workflow, role, 'source', 'Investigate original question', {})
    assert type(source) is binding.decision_source_type
    assert runtime.DecisionSource not in type(source).__mro__
    assert type(source).__module__.rsplit('.', 1)[0] == binding.__module__.rsplit('.', 1)[0]
    assert source.path == ((role, 'source'),)
    assert source.report_values == {}
    workflow.episode_bindings.for_path = lambda path: object()
    assert type(runtime.Workflow.build(workflow, role, 'other', 'Original default', {})) is runtime.DecisionSource


def test_active_assay_reader_exception_is_an_original_invalid_result(binding):
    import asyncio
    from importlib import import_module
    package = binding.__module__.rsplit('.', 1)[0]
    if package.endswith('scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'):
        error_type = import_module(package + '.grading.literature_experimental_contracts').ExperimentalContractError
    else:
        error_type = import_module('gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts').ExperimentalContractError

    def invalid(*args):
        raise error_type('source_quote_mismatch', 'assay.molecule')
    binding._tool_arguments = lambda context, name, arguments: arguments
    binding._materialize_text_arguments = lambda context, arguments, repository, operation_key: arguments
    binding.literature_assay_repository = lambda: SimpleNamespace(populate=invalid)
    outcome = asyncio.run(binding.execute(SimpleNamespace(role=binding.roles[0]), 'literature.assay.populate', {}, 'original-assay-action'))
    assert outcome['status'] == 'invalid'
    assert outcome['record_refs'] == [] and outcome['changed_record_refs'] == []
    assert outcome['feedback']['code'] == 'source_quote_mismatch:assay.molecule'
    assert outcome['feedback']['field'] == 'assay.molecule'
