"""The one actual A101 Scientific snapshot definer, after live credit callbacks.

Real parent/source/Store/Journal; explicit projection ports. No Scientific
constructor, scientific tool invocation or whole-workflow evidence is claimed.
"""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from ...tests.test_a101_parent_policy_owners import policy_original
from ...tests.test_a101_implicit_parent_protocol import actual_workflow, no_external_execution, own, root


@pytest.mark.parametrize('role', ('annotation', 'improvement'))
@pytest.mark.parametrize('failure', (False, True))
def test_actual_report_keeps_late_scientific_identity_and_failure_order(tmp_path, role, failure):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = (root(workflow) if role == 'annotation' else workflow.build(
            'improvement', 'root', 'Existing iterative question', workflow.store.validate_scope())).source
        events, delivered = [], []
        class JournalError(Exception): pass
        def report(context, snapshot):
            events.append('specialist.facts'); delivered.append(deepcopy(snapshot)); return {}
        binding = SimpleNamespace(facts=report)
        workflow.specialist = lambda _source: binding
        workflow.is_job_source = lambda _source: False
        workflow.project_annotation_score = None
        workflow.resource_estimator = None
        def credit(_source):
            events.append('credit'); workflow.scientific_process_binding = binding; return {'credit': 2.0}
        workflow.source_credit_view = credit
        workflow.source_controller_credit = lambda _source: (events.append('controller_credit'), 3.0)[1]
        workflow.pending_handles = lambda _source: []
        workflow.services.scientific_parent_invocation = lambda context: (events.append('parent_invocation'), None)[1]
        original_row = workflow.journal.row
        def row(table, *args):
            if table == 'runtime_episodes':
                events.append('episode_row')
                if failure: raise JournalError('original initial-credit read')
            return original_row(table, *args)
        workflow.journal.row = row; observations = []
        for function in (policy_original(None, 'facts'), runtime.Workflow.facts):
            workflow.scientific_process_binding = None; events.clear(); delivered.clear()
            if failure:
                with pytest.raises(JournalError, match='original initial-credit read') as error:
                    function(workflow, source, completion_record=None)
                result = (type(error.value), error.value.args)
                assert events == ['credit', 'episode_row'] and delivered == []
            else:
                result = function(workflow, source, completion_record=None)
                assert events == ['credit', 'episode_row', 'controller_credit', 'parent_invocation', 'specialist.facts']
                assert len(delivered) == 1
                assert delivered[0]['credit'] == 2.0 and delivered[0]['controller_credit'] == 3.0
                assert delivered[0]['initial_credit'] == original_row('runtime_episodes', source.episode_id)['initial_credit']
                assert delivered[0]['parent_invocation_ref'] is None
                assert result['episode_yield'] == delivered[0]['episode_yield']
            observations.append((result, deepcopy(events), deepcopy(delivered)))
        assert observations[0] == observations[1]
        assert runtime.Workflow.facts is own('library.source_report_records').facts
        assert own('scientific_process.completion_report').enrich_completion_snapshot.__globals__ is vars(runtime)

