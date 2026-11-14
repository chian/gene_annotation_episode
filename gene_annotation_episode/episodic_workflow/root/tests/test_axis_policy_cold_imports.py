"""Actual original/broken/corrected fresh module entry controls, without science."""
import pytest
from .axis_policy_cold_imports import CASES, input_record, observe


@pytest.mark.parametrize('variant,entry', CASES, ids=[variant + '-' + entry for variant, entry in CASES])
def test_cold_policy_entry(tmp_path, variant, entry):
    if variant != 'fixed' and input_record()[0] is None:
        pytest.skip('Historical original/broken import evidence requires explicit pinned cold inputs.')
    result = observe(tmp_path, variant, entry)
    outcome = result['outcome']
    if variant == 'broken':
        assert result['import_returncode'] == 1
        assert outcome['status'] == 'raised' and outcome['type'] == 'ImportError'
        assert 'partially initialized module' in outcome['message']
        assert '.library.' in outcome['message']
        assert any("'" + name + "'" in outcome['message'] for name in
            ('facts', 'action_schema', 'form_examples', 'scientific_child_contract', 'project_annotation_facts'))
    else:
        assert result['import_returncode'] == 0 and outcome['status'] == 'imported'
        if variant == 'fixed':
            assert len(result['identity']) == 4 and all(result['identity'].values())
