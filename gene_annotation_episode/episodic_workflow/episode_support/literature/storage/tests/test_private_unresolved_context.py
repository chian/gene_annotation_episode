"""Missing contextual operands remain unresolved saved evidence, not support."""
from copy import deepcopy
import pytest
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import LiteratureA108GradingRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.tests.test_private_context_publication import context_fixture

@pytest.mark.parametrize('missing', ['target_identity', 'criterion'])
def test_missing_context_operand_saves_partial_original_observation(tmp_path, missing):
    with Store(tmp_path / 'state') as store:
        context, arguments = context_fixture(store, requested=False)
        arguments = deepcopy(arguments)
        observation = arguments['observations'][0]
        qualification = 'Actual source condition retained; transfer remains unresolved.'
        observation['qualifications'] = [qualification]
        if missing == 'target_identity':
            arguments['target_identity'] = {'status': 'unknown', 'support_refs': []}
        else:
            criterion = next(iter(observation['criteria']))
            observation['criteria'][criterion] = {'status': 'unknown', 'support_refs': []}
        repository = LiteratureA108GradingRepository(store, context.run_id)
        result = repository.populate(context, arguments, 'original-unresolved-observation')
        saved = repository.read(result['result']['sheet_ref'])
        row, = saved['sheet']['relations']
        assert row['relation'] == 'unresolved' and row['requested_relation'] == 'support'
        assert row['original_observation_ref'] == observation['original_observation_ref']
        assert row['source_subject_ref'] == observation['source_subject_ref']
        assert row['qualifications'] == [qualification]
        cells = saved['sheet']['cells']
        assert cells['support_count']['value'] == 0 and cells['evidence_amount']['value'] == 0
        assert cells['unresolved_count']['value'] == 1 and cells['unresolved_count']['status'] == 'partial'
        assert saved['sheet']['annotation_credit'] is None
