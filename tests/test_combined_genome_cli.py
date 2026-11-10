"""The ordinary CLI binds the combined root to its exact investigation owners."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.all_evidence_tools import AllEvidenceToolRegistry
from gene_annotation_episode.cli import main
from gene_annotation_episode.root_axis_scalars import AXES, VERSION
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.state import Store


def test_cli_run_forwards_combined_root_credit_and_all_axis_registry(tmp_path, monkeypatch, capsys):
    import gene_annotation_episode.cli as cli
    import gene_annotation_episode.runtime as runtime

    workspace = tmp_path / 'genome'
    with Store(workspace) as store:
        store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
    config_file = tmp_path / 'settings.toml'
    config_file.write_text('')
    config = {'genome_investigation': {
        'version': 'combined_genome_investigation_v2',
        'root': {
            'version': 'signed_root_episode_binding_v2',
            'initial_known_record_refs': [],
            'annotation_support': {'version': VERSION},
            'root_task': {'kind': 'annotation_axis_credit',
                'cutoffs': {axis: .01 for axis in AXES},
                'yield_parameters': {'uncertainty_alpha': .05}}},
        'services': {'source_directory': str(tmp_path),
            'execution_configuration': {}, 'tool_retrieval': {},
            'literature_configuration': {}, 'scientific_yield_bindings': {}}}}
    monkeypatch.setattr(cli, 'tomllib', SimpleNamespace(loads=lambda _: config))

    async def capture(store, tools, **options):
        assert isinstance(tools, AllEvidenceToolRegistry)
        assert 'material.parse' in tools.catalog()
        assert options['project_credit'].task_credit is True
        assert options['project_annotation_score'].task_credit is False
        assert options['controller_factory']((('annotation', 'root'),),
            {'mode': 'annotation_axis_credit', 'arms': []}).state().root_score == 0
        with pytest.raises(ValueError, match='episode_owner_yield_binding_required'):
            options['controller_factory']((('annotation', 'root'), ('scientific_process', 'child')), 0)
        assert options['annotation_child_roles'] == ('scientific_process',)
        assert options['episode_service_binding']['version'] == 'genome_existing_evidence_services_v1'
        assert options['binding_definitions']['credit']['root_task_credit_formula'] == (
            'max_per_annotation_sum_of_axis_owner_received_progress')
        return {'status': 'bound'}

    monkeypatch.setattr(runtime, 'run_workflow', capture)
    assert main(['run', '--workspace', str(workspace), '--config', str(config_file)]) == 0
    assert json.loads(capsys.readouterr().out) == {'status': 'bound'}


def test_old_root_scalar_sum_binding_is_explicitly_incompatible():
    from gene_annotation_episode.signed_evidence_root import SignedRootEpisodeBinding
    with pytest.raises(ValueError, match='legacy_signed_root_scalar_credit_incompatible'):
        SignedRootEpisodeBinding.from_record({'version': 'signed_root_episode_binding_v1'})


def test_combined_services_prepare_actual_axis_catalog_without_execution(tmp_path):
    from gene_annotation_episode.genome_investigation import GenomeEvidenceServices
    from gene_annotation_episode.resource_estimation import ResourceToolEstimator
    from gene_annotation_episode.tool_configuration import build_tools

    source = Path(__file__).resolve().parents[1]
    resources = json.loads((source / 'examples/aurora_execution_resources.json').read_text())
    services = GenomeEvidenceServices(
        source_directory=str(source / 'research/slotted_process_library/publications/2026-10-24-001'),
        execution_configuration={'resources': resources, 'initial_information': {},
            'handoff_unit': 1, 'acquired_record_unit': 1,
            'monitoring_information_unit': 1,
            'monitor_yield_settings': {'kind': 'information_accumulation',
                'cutoff': .25, 'uncertainty_alpha': .05}},
        tool_retrieval={'version': 'scientific_tool_retrieval_v1', 'mode': 'literal_test_v1'},
        literature_configuration={'outcome_page_size': 5})
    with Store(tmp_path / 'genome') as store:
        store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        tools = build_tools(store, registry_class=AllEvidenceToolRegistry)
        application = services(store, run_id='setup-only', directory=tmp_path / 'run',
            tool_catalog=tools.catalog(), tool_registry=tools,
            resource_estimator=ResourceToolEstimator())
        bindings = {row['binding_id'] for row in application.episode_binding_descriptors}
        assert {'scientific_process', 'literature', 'execution_episodes', 'monitor'} <= bindings
        assert {'A101', 'A102', 'A103', 'A104', 'A105', 'A106', 'A107', 'A108', 'A110'} <= {
            row['option_ref']['option_id'] for row in
            ScientificProcessLibrary(tmp_path / 'run/scientific-process-library').headers()
            if row['option_ref']['slot'] == 'evidence_axis'}
