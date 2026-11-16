"""Only explicitly bound versions appear in the real tool-information route."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_tool_info import proteome_tool_contracts
from test_api_bvbrc_appservice import CONFIG
from gene_annotation_episode.episodic_workflow.root.a101.tests.test_bvbrc_homology_tool_info import factory


@pytest.mark.parametrize('versions', [(), ('1', '1'), ('2', '2'), ('3',), ['2'], '2', (True,)])
def test_invalid_or_implicit_version_selection_rejected(factory, versions):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    with pytest.raises(ValueError, match='adapter_versions'):
        proteome_tool_contracts(resource_id='selected-api', assignment_schema=family.api_execution.assignment_schema('selected-api'),
                               adapter_versions=versions)
