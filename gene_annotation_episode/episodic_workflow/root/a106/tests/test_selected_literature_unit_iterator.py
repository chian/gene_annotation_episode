"""Every returned operation status enters the original numerical iterator."""
import json
from types import SimpleNamespace

import pytest

from ..domain import ContractError
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from ..episode_services import WorkflowServices
from ..method_loop.identities import UnitRef
from ..published_evidence_assessment.episode import LiteratureEpisode
from ..state import Store
from .selected_literature_unit_fixtures import run_selected_literature_unit


@pytest.mark.parametrize('status',['completed','partial','invalid','failed','unavailable'])
def test_actual_selected_unit_keeps_returned_outcome_identity_and_original_credit(tmp_path,status):
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='ATGGCT',molecule='dna')
        context=BindingContext('selected-unit-run','replaced-with-typed-identity','literature',
            (('literature','original-source-unit'),),store.validate_scope(),{}, {},())
        host=SimpleNamespace(store=store,run_id=context.run_id)
        services=WorkflowServices(host)
        binding=LiteratureEpisode(services)
        async def returned(name,arguments,**kwargs):
            return {'status':status,'record_refs':[],'changed_record_refs':[],
                'result':{'fixture':'explicit returned operation status'}}
        services.execute_tool=returned
        if status=='invalid':
            def invalid(*args):raise ContractError('explicit_invalid_selected_operand')
            binding._tool_arguments=invalid
        else:
            binding._tool_arguments=lambda context,name,arguments:arguments
        selected={'kind':'tool','tool':'source.locate','arguments':{'offset':3}}
        result=run_selected_literature_unit(store,context,binding,selected,decision_index=7)
        row=store.db.execute('SELECT action,result,credit FROM runtime_actions WHERE episode_id=?',
            (result.context.episode_id,)).fetchone()
        assert json.loads(row['action'])==selected
        assert json.loads(row['result'])['status']==status
        assert result.outcome['status']==status
        assert row['credit']==result.unit.controller_input.as_record()['credit']==0
        assert result.unit.unit_ref==UnitRef(result.context.episode_id,7)
        assert result.controller.estimator.scores==(0.,)
        item,contribution,view=result.hooks[0]
        assert len(result.hooks)==1 and item.unit==selected
        assert contribution.controller_input is view.controller_input is result.unit.controller_input
        assert view.unit_ref==result.unit.unit_ref
        clock=result.unit.controller_input.as_record()['estimation_context']['progress_time']
        assert clock['status']=='unavailable' and clock['unavailable_reason']=='episode_origin_clock_unavailable'
        assert store.db.execute('SELECT COUNT(*) FROM runtime_model_calls').fetchone()[0]==0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_episodes').fetchone()[0]==0
