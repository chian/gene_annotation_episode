"""Physical owner relocation preserves actual runtime role and child identity."""
from importlib import import_module
from ..task import ImprovementTask
from .improvement_host_checks import improvement_host, host_workflow, build_host
from ...tests.improvement_exchange_checks import paired


def test_descriptive_owner_imports_preserve_runtime_role_and_counterparts(tmp_path):
    package = 'gene_annotation_episode.episodic_workflow.root.a102.annotation_improvement'
    names = ('child_message_owners', 'continuation', 'credit', 'decision_delivery',
        'decision_waiting', 'episode', 'from_child_annotation_improvement', 'from_parent',
        'goal', 'internal_summary', 'operations', 'received_outcomes', 'report_facts',
        'task', 'task_instructions', 'task_state', 'to_child_annotation_improvement',
        'to_parent', 'working_state')
    assert import_module(package).__name__ == package
    for name in names:
        assert import_module(package + '.' + name).__name__ == package + '.' + name
    with improvement_host(tmp_path, root_role='annotation') as host:
        workflow = host_workflow(host, [])
        episode = build_host(host, workflow)
        assert type(episode.source) is ImprovementTask
        assert ImprovementTask.__module__ == package + '.task'
        assert episode.source.path == (('improvement', 'parent'),)
        assert episode.request.goal.as_record()['result_contract'] == {'role': 'improvement'}
        for parent in ('annotation', 'improvement'):
            result = paired(host, parent, 'request-valid')
            expected_parent = package.rsplit('.', 1)[0] if parent == 'annotation' else package
            assert result['owners'][0] == (expected_parent + '.to_child_annotation_improvement', 'prepare_request')
            assert result['built'][0]['path'][-1][0] == 'improvement'
            assert result['has_unit'] and result['error'] is None
