"""Original synthetic operands retain their typed owner and missing commission."""
import pytest

from .perturbation_summary_fixtures import fixture, REQUESTED
from .literature_admission_fixtures import admit_original_literature_credit, selected_work_rows
from ..domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from ..state import Store


@pytest.mark.parametrize('paired,graph', [(False, False), (True, False), (False, True)])
def test_original_fixture_has_private_context_without_invented_task(tmp_path, paired, graph):
    store, context, arguments = fixture(tmp_path, paired=paired, graph=graph)
    with store:
        assert type(store) is Store and type(context) is BindingContext
        assert context.run_id == 'summary-fixture-run'
        assert context.episode_id == 'summary-child'
        assert context.role == 'literature' and context.path == (('literature', 'fixture'),)
        assert dict(context.request) == {}
        assert set(context.assignment) == {'version', 'question_context_refs', 'source_refs',
            'requested_perturbation_summary_components'}
        assert list(context.assignment['requested_perturbation_summary_components']) == REQUESTED
        assert len(context.received_record_refs) == (3 if graph else 2)
        assert set(context.received_record_refs) == set(context.assignment['source_refs'])
        original = canonical(context.as_record())
        before = selected_work_rows(store, context.run_id)
        with pytest.raises(ContractError, match='^literature_original_task_credit_required$'):
            admit_original_literature_credit(store, context)
        assert selected_work_rows(store, context.run_id) == before
        assert canonical(context.as_record()) == original
        assert 'literature_task' not in context.assignment
        assert 'proposed_annotation_ref' not in context.assignment
        assert arguments['source_ref'] in context.received_record_refs
        assert arguments['data_source_ref'] in context.received_record_refs
