"""Own commissioned state and explicit standalone compatibility are separate."""
from copy import deepcopy
from pathlib import Path

import pytest

from . import test_private_head_applicability as fixtures
from .test_scientific_task import make_task

AXIS=Path(__file__).resolve().parents[2].name


@pytest.mark.parametrize('timing',[False,True])
def test_commissioned_state_preserves_own_credit_source_findings_and_optional_timing(monkeypatch,timing):
    original=fixtures.make_task
    contributions=[{'source_ref':'actual-source','qualification':'unresolved_target_correspondence'}]
    credit={'credit':2.5,'source_contributions':contributions}
    if AXIS=='a101':
        credit.update(axis_components={'A101':2.5},a101_sheet={'original':'native-correspondence'})
    if timing:
        credit.update(monitoring_information_credit=0.25,monitoring_information_binding={'original':'native-timing'})
    retained=deepcopy(credit)
    def commissioned(outcome):
        task,saved,calls,events=original(outcome)
        task.path=(('annotation','original-parent'),('scientific_process','commissioned'))
        actual_state=task.decision_state
        def present(view):
            task.workflow.source_credit_view=lambda source:credit
            return actual_state(view)
        task.decision_state=present
        return task,saved,calls,events
    monkeypatch.setattr(fixtures,'make_task',commissioned)
    state=fixtures.head_state()
    assert state['current_credit']==2.5
    assert state['_completed_work_axis_results']['source_contributions']==contributions
    assert state['controller']=={'original':'scalar'}
    if AXIS=='a101':
        assert state['current_evidence_vector']=={'A101':2.5}
        assert state['_completed_work_axis_results']['a101_sheet']=={'original':'native-correspondence'}
    if timing:
        assert state['monitoring_information_credit']==0.25
        assert state['monitoring_information_binding']=={'original':'native-timing'}
    else:
        assert 'monitoring_information_credit' not in state
    assert credit==retained


