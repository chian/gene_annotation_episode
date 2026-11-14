"""Scientific completion operands at all three authentic fresh-report sites.

Real parent/source/Store/Journal state plus declared report projection ports
exercise the late identity predicate. No Scientific tool operation is run.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from ...tests.test_a104_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, own, root,
)


@pytest.mark.parametrize('route', ('fallback', 'annotation', 'improvement'))
@pytest.mark.parametrize('failure', (False, True))
def test_late_scientific_identity_keeps_snapshot_and_failure_order(tmp_path, route, failure):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = (workflow.build('improvement', 'root', 'Existing improvement', workflow.store.validate_scope())
                  if route == 'improvement' else root(workflow)).source
        events, delivered = [], []
        class JournalError(Exception): pass
        def report(context, snapshot):
            events.append('specialist.facts')
            delivered.append(deepcopy(snapshot))
            return {}
        binding = SimpleNamespace(facts=report)
        workflow.specialist = lambda _source: binding
        workflow.is_job_source = lambda _source: False
        workflow.project_annotation_score = None
        def credit(_source):
            events.append('credit')
            # The original identity condition occurs after this callback. Its
            # old value cannot justify deleting the later Scientific branch.
            workflow.scientific_process_binding = binding
            return {'credit': 2.0}
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
        workflow.journal.row = row
        candidate = (runtime.Workflow.facts if route == 'fallback' else
                     own('report_facts' if route == 'annotation' else 'annotation_improvement.report_facts').facts)
        outcomes = []
        for function in (original_function('Workflow', 'facts'), candidate):
            workflow.scientific_process_binding = None
            events.clear(); delivered.clear()
            if failure:
                with pytest.raises(JournalError, match='original initial-credit read') as error:
                    function(workflow, source, completion_record=None)
                result = (type(error.value), error.value.args)
                assert events == ['credit', 'episode_row'] and delivered == []
            else:
                result = function(workflow, source, completion_record=None)
                assert events == ['credit', 'episode_row', 'controller_credit', 'parent_invocation', 'specialist.facts']
                assert len(delivered) == 1
                assert delivered[0]['credit'] == 2.0
                assert delivered[0]['controller_credit'] == 3.0
                assert delivered[0]['initial_credit'] == original_row('runtime_episodes', source.episode_id)['initial_credit']
                assert delivered[0]['parent_invocation_ref'] is None
                assert result['episode_yield'] == delivered[0]['episode_yield']
            outcomes.append((result, deepcopy(events), deepcopy(delivered)))
        assert outcomes[0] == outcomes[1]
