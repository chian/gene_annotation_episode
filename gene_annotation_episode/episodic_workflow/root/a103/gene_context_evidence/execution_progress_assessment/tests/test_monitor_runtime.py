"""The three A103 progress monitors register on the generic runner over real collaborators.

The run's shared Store and A103's own tool registry over it; the real
episode_runtime registry, journal and linker. No model is called. A monitor
target is an execution handle of A103's execution job provider; observing one
needs an execution binding run to have produced it, so observation is not
exercised here.
"""
from importlib import import_module

import pytest

from episode_runtime import BindingRegistry, LinkError, RunJournal, link
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import A103ToolRegistry
from gene_annotation_episode.state import Store

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.'
HOMES = ('execution_progress_assessment', 'hpc_work_planning.execution_progress_assessment',
         'hpc_work_planning.hpc_allocation_execution.execution_progress_assessment')
SETTINGS = {'kind': 'information_accumulation', 'cutoff': 0.25, 'uncertainty_alpha': 0.1}
UNIT = 2.5  # an information unit other than one: credit stays on its own scale


def monitors(tools):
    return [import_module(PACKAGE + home + '.episode').MonitorEpisode(information_unit=UNIT, yield_settings=SETTINGS,
                                                                      tool_registry=tools)
            for home in HOMES]


def test_monitor_bindings_register_and_require_their_runtime_collaborators(tmp_path):
    with Store(tmp_path / 'state') as store:
        tools = A103ToolRegistry(store, a103_work_directory=tmp_path / 'runs' / 'a103', target_genomic_sources={})
        registry = BindingRegistry(monitors(tools))
        assert set(registry.paths) == {'gene_context_evidence/' + home.replace('.', '/') for home in HOMES}
        for binding in monitors(tools):
            assert binding.required_collaborators == ('model_provider', 'store', 'a103_progress_provider')
            assert binding.tool_registry is tools
        journal = RunJournal(tmp_path / 'journal.sqlite')
        with pytest.raises(LinkError, match='collaborator_required:gene_context_evidence/execution_progress_assessment'):
            link(registry, 'gene_context_evidence/execution_progress_assessment',
                 {'scope': {'subject_refs': []}, 'role_assignment': {}}, run_id='unlinked', journal=journal)
