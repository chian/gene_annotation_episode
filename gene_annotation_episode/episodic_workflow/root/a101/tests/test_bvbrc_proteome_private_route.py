"""Pure original A101 GenomeComparison configuration/spec/catalog boundaries.

No acquired action, API request, provider/native worker, model, or workflow is
executed. Original numerical/saved-value tests remain separate and unchanged.
"""
from copy import deepcopy
import importlib
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.a101 import bvbrc_appservice_adapters as registry
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_adapter as v1
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_adapter_v2 as v2
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_application_definitions import get_application_spec, prepare_application
from gene_annotation_episode.episodic_workflow.root.a101.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.episodic_workflow.root.a101.api_service_execution import APIServiceExecution


HOMES = (
    'execution_job_submission',
    'execution_job_submission/api_job_execution',
    'execution_job_submission/local_job_execution',
    'execution_job_submission/hpc_job_execution',
    'execution_result_acquisition',
    'scientific_process/execution_job_submission',
    'scientific_process/execution_job_submission/api_job_execution',
    'scientific_process/execution_job_submission/local_job_execution',
    'scientific_process/execution_job_submission/hpc_job_execution',
    'scientific_process/execution_result_acquisition',
)


def pin(adapter):
    return dict(adapter_id=adapter.ADAPTER_ID, adapter_version=adapter.ADAPTER_VERSION,
                implementation_sha256=adapter.implementation_sha256())


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('pure route inspection attempted external execution')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('subprocess.run', forbidden)


def test_no_implicit_or_unknown_adapter_choice():
    assert registry.bind_adapters([]) == {}
    assert registry.bind_adapters([dict(adapter_id='unknown_provider', adapter_version='1', implementation_sha256='0' * 64)]) == {}


def original_parameters(kind='genome_ids'):
    # Exact original test_bvbrc_proteome_tool_info.launch parameters. Duplicate
    # occurrences and omitted identity/uncertainty retain their original meaning.
    values = {'genome_ids': [], 'user_genomes': [], 'user_feature_groups': [],
        'reference_genome_index': 1, 'output_path': '/synthetic/work/output', 'output_file': 'compare',
        'min_ident': .25, 'min_seq_cov': .3, 'min_positives': .2, 'max_e_val': 1e-5}
    values[kind] = (['83333.1', '83333.1'] if kind == 'genome_ids'
                   else ['/synthetic/input/first', '/synthetic/input/first'])
    return values


def test_exact_original_packaged_definition_is_detached():
    spec = get_application_spec('GenomeComparison')
    assert spec['source']['sha256'] == '98b639266d78107b21a1e8ba21be0c4038a498a5ede2fd1deac96b89426d9bdd'
    assert spec['native_id'] == spec['required_id'] == 'GenomeComparison'
    spec['definition']['parameters'].clear()
    assert get_application_spec('GenomeComparison')['definition']['parameters']


@pytest.mark.parametrize('kind', ['genome_ids', 'user_genomes', 'user_feature_groups'])
def test_original_native_parameter_occurrences_are_preserved(kind):
    values = original_parameters(kind)
    original = deepcopy(values)
    prepared = prepare_application('GenomeComparison', values, {})
    assert prepared['status'] == 'ok', prepared
    assert values == original


def test_omitted_native_options_stay_omitted():
    values = original_parameters()
    for name in ('reference_genome_index', 'min_ident', 'min_seq_cov', 'min_positives', 'max_e_val'):
        values.pop(name)
    original = deepcopy(values)
    assert prepare_application('GenomeComparison', values, {})['status'] == 'ok'
    assert values == original


def test_missing_original_input_family_remains_invalid():
    values = original_parameters()
    values['genome_ids'] = []
    result = prepare_application('GenomeComparison', values, {})
    assert result['status'] == 'invalid'
    assert any(row['code'] == 'input_required' for row in result['diagnostics'])


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('adapter', [None, v1, v2])
def test_actual_private_catalog_selects_only_explicit_original_version(home, adapter):
    # Exercise the actual private catalog and API assignment-schema methods with
    # an inert configured service object. No service constructor or method that
    # issues a request is invoked by this control.
    service = object.__new__(BVBRCAppServiceService)
    service.scientific_adapters = registry.bind_adapters([] if adapter is None else [pin(adapter)])
    config = {'kind': 'api', 'service': 'bvbrc_appservice'}
    api = object.__new__(APIServiceExecution)
    api.configuration = {'selected-api': config}
    api.services = {'selected-api': service}
    operations = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a101.' + home.replace('/', '.') + '.execution_operations').OperationalOperations
    host = SimpleNamespace(resources={'selected-api': config}, api_execution=api)
    rows = [row for row in operations.resource_tool_contracts(host) if row['name'] == 'bvbrc.proteome_comparison']
    if adapter is None:
        assert rows == []
        return
    assert len(rows) == 1
    row = rows[0]
    assert row['resources'] == 'api'
    assert row['invocation_route']['routes'] == [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]
    Draft202012Validator.check_schema(row['input_schema'])
    launch = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
        'service': 'bvbrc_appservice', 'endpoint': 'usable_handoff', 'constraints': {},
        'request': {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
            'required_application_id': 'GenomeComparison', 'parameters': original_parameters(),
            'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}}
    validator = Draft202012Validator(row['input_schema'])
    assert validator.is_valid(launch), list(validator.iter_errors(launch))
    launch['request']['required_application_id'] = 'Homology'
    assert not validator.is_valid(launch)
