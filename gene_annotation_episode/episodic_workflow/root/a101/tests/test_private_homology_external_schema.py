"""Legacy root report composition may ask job bindings for non-job sources."""
from importlib import import_module
import pytest


@pytest.mark.parametrize('home',['homology_job_submission','homology_job_monitoring','homology_result_acquisition'])
@pytest.mark.parametrize('role',['annotation','sequence_homology_evidence'])
def test_original_external_report_schema_query_remains_empty(home,role):
    cls=import_module('gene_annotation_episode.episodic_workflow.root.a101.'+home+'.episode').HomologyEpisode
    binding=object.__new__(cls)
    # Workflow.report_sources invokes this callback before job-role filtering.
    # No registry/resource read or invented job schema is needed for this role.
    assert binding.fact_sources(role)=={}
