"""Pure selection and real shared registration, using authored declarations.

No fixture here is an executed native result or authenticated child report.
Run through packet445's existing bounded native lifecycle runner.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_chromatin_interaction_contracts import POLICY, REQUIRED_DEPENDENCIES, REQUIRED_MODULES
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def software():
    return {'python_executable': '/synthetic/python', 'python_sha256': '1' * 64,
        'python_version': 'synthetic', 'module_root': '/synthetic/source',
        'driver_module': 'gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_driver',
        'implementation_files': [{'module': name, 'sha256': '2' * 64}
            for name in sorted(REQUIRED_MODULES)],
        'dependencies': [{'distribution': name, 'version': 'synthetic',
            'package_root': '/synthetic/deps/' + name,
            'files': [{'path': '/synthetic/deps/' + name + '/member',
                'sha256': '3' * 64, 'size_bytes': 1}]} for name in sorted(REQUIRED_DEPENDENCIES)]}


def family(store, directory, resource):
    return ExecutionEpisodes(None, store=store, directory=directory, run_id='chromatin-registration',
        resources={'selected-local': resource}, initial_information={}, tool_registry=ToolRegistry(store, run_directory=store.path / 'tool-run'),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=['stdout', 'stderr'])


def resource(directory):
    return {'kind': 'local', 'workspace': str(directory), 'policy': deepcopy(POLICY),
        'native_chromatin_interactions': [{'operation': 'analyze_chromatin_interactions',
            'resource_kind': 'local', 'analysis_modes': ['cis_anchor_contact_enrichment',
                'cross_window_insulation_heuristic'], 'supported_formats': ['cooler_hdf5_v3'],
            'software': software()}]}


@pytest.mark.parametrize('kind', ['api', 'pbs_ssh'])
def test_unimplemented_resource_binding_is_explicit(tmp_path, kind):
    config = {**resource(tmp_path), 'kind': kind}
    with Store(tmp_path / 'store') as store:
        with pytest.raises(ValueError, match='native_chromatin_resource_execution_binding_unfinished'):
            family(store, tmp_path / 'run', config)


