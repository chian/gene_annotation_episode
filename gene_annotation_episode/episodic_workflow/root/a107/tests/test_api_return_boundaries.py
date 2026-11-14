"""Actual seven-port constructors/negative custody and controlled saved projections.

No model, transport, native launch or API operation. Positive projection cases
use authenticated original synthetic fixture data; they do not prove producer
execution or complete host publication/receipt custody for seven families.
"""
from copy import deepcopy
from dataclasses import replace
import importlib
import hashlib
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a107.'
COHORT = (('phylogeny', 'BVBRCPhylogenyReturns'), ('alignment', 'BVBRCAlignmentReturns'),
    ('genome_alignment', 'BVBRCGenomeAlignmentReturns'), ('proteome', 'BVBRCProteomeReturns'),
    ('comparative_systems', 'BVBRCComparativeSystemsReturns'), ('fastqutils', 'BVBRCFastqUtilsReturns'),
    ('application', 'BVBRCApplicationReturns'))

def module(name): return importlib.import_module(PREFIX + name)
def library(name): return module('library.received_execution_information.historical_' + name)

@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def denied(*args, **kwargs): raise AssertionError('read controls attempted external execution')
    monkeypatch.setattr('socket.create_connection', denied)
    monkeypatch.setattr('socket.socket.connect', denied)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', denied)
    monkeypatch.setattr('subprocess.Popen', denied)
    monkeypatch.setattr(module('api_service_execution').APIServiceExecution, 'execute', denied)
    native = module('native_lifecycle')
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'collect', 'wait_job'):
        monkeypatch.setattr(native, name, denied)

@pytest.fixture
def api_case(tmp_path):
    with module('state').Store(tmp_path / 'store') as store:
        api = module('api_service_execution').APIServiceExecution(store, run_id='seven-return-read-controls',
            directory=tmp_path / 'api', configuration={'data': {'kind': 'api', 'service': 'bvbrc_data'}},
            tool_registry=module('tools').ToolRegistry(store), handoff_unit=1., acquired_record_unit=1.)
        subject, = store.create_problem(raw_sequence='ATGGCT', molecule='dna')['subject_refs']
        scope = store.validate_scope({'subject_refs': [subject]})
        path = (('annotation', 'root'),)
        episode_id = module('method_loop.identities').EpisodeRef(api.run_id, path).episode_id
        request = {'message': {'scope': scope, 'episode_assignment': {}}}
        context = module('episode_bindings').BindingContext(api.run_id, episode_id, 'annotation', path, scope, {}, request)
        journal = module('episode_journal').Journal(store, api.run_id)
        canonical = module('execution_contracts').canonical
        journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        yield SimpleNamespace(api=api, store=store, context=context)

def selected_schema(family):
    target = module('bvbrc_' + family + '_returns')
    sources = getattr(target, family + '_fact_sources')()
    first = next(iter(sources))
    return {'type': 'object', 'properties': {'selected': deepcopy(sources[first]['report_schema'])},
        'required': ['selected'], 'additionalProperties': False}

@pytest.mark.parametrize('family,class_name', COHORT)
def test_actual_eager_port_owns_canonical_receiving_type(api_case, family, class_name):
    host = getattr(api_case.api, family + '_returns')
    target = module('bvbrc_' + family + '_returns')
    assert type(host) is getattr(target, class_name)
    assert isinstance(host, module('episode_return_records').EpisodeReturnRecords)
    assert host.api is api_case.api and host.store is api_case.store and host.db is api_case.store.db
    assert host.run_id == api_case.api.run_id

@pytest.mark.parametrize('family,class_name', COHORT)
def test_foreign_context_is_rejected_by_original_typed_boundary(api_case, family, class_name):
    host = getattr(api_case.api, family + '_returns'); target = module('bvbrc_' + family + '_returns')
    expected = {'proteome':'ProteomeReturnError', 'comparative_systems':'ComparativeSystemsReturnError',
        'fastqutils':'FastqUtilsReturnError'}.get(family)
    error_type = ValueError if expected is None else getattr(target, expected)
    schema = selected_schema(family); before = tuple(api_case.store.db.iterdump())
    with pytest.raises(error_type) as caught:
        host.facts(replace(api_case.context, run_id='foreign-original-run'), schema)
    assert type(caught.value) is error_type
    assert str(caught.value) == target._PREFIX + 'context_conflict'
    assert tuple(api_case.store.db.iterdump()) == before

@pytest.mark.parametrize('family,class_name', COHORT)
def test_matching_source_requires_actual_saved_successful_admission(api_case, family, class_name):
    host = getattr(api_case.api, family + '_returns'); schema = selected_schema(family)
    error_type = module('bvbrc_appservice_custody').AppServiceCustodyError
    key = f'{api_case.api.run_id}:{api_case.context.episode_id}:0:typed_form'
    before = tuple(api_case.store.db.iterdump())
    with pytest.raises(error_type) as caught:
        host.record_admission(api_case.context, {'selected': []}, schema, key)
    assert type(caught.value) is error_type
    assert caught.value.code == 'bvbrc_appservice_custody_successful_return_required'
    assert tuple(api_case.store.db.iterdump()) == before


def fastq_oracle(name):
    base = Path(__file__).parent / 'fixtures/api_returns_saved'
    manifest_raw = (base / 'ASSETS.json').read_bytes()
    assert hashlib.sha256(manifest_raw).hexdigest() == '4bbab03a9f5700d450e811c70d7d42e769b8ef969b48c80393db41663f745372'
    raw = (base / 'fastqutils' / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == json.loads(manifest_raw)['fastqutils'][name]['sha256']
    return json.loads(raw)

def fastq_saved_case():
    """Controlled envelope using original oracle values; no producer/custody claim."""
    sheet = fastq_oracle('EXPECTED_SHEET_002.json'); calculations = fastq_oracle('EXPECTED_COMPONENTS_002.json')
    parameters = fastq_oracle('PROVIDER_PARAMETERS_002.json'); selector = fastq_oracle('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')
    bundle = fastq_oracle('ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json')
    # The original Returns.saved_fixture declares these three synthetic fields
    # consistently before parsing. Here only the copied envelope is constructed;
    # saved content, original task, selections, sheet and calculations stay exact.
    original_bundle = deepcopy(bundle)
    for artifact in bundle['artifacts']:
        synthetic_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'synthetic-fastqutils:' + artifact['workspace_object']['path']))
        artifact['workspace_object']['uuid'] = synthetic_uuid
        artifact['task_association']['output_path'] = artifact['workspace_object']['path']
        artifact['task_association']['output_uuid'] = synthetic_uuid
    reversed_bundle = deepcopy(bundle)
    for artifact, original in zip(reversed_bundle['artifacts'], original_bundle['artifacts']):
        artifact['workspace_object']['uuid'] = original['workspace_object']['uuid']
        artifact['task_association']['output_path'] = original['task_association']['output_path']
        artifact['task_association']['output_uuid'] = original['task_association']['output_uuid']
    assert reversed_bundle == original_bundle == fastq_oracle('ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json')
    assert module('bvbrc_appservice_contracts').validate_contract('ArtifactBundle', bundle) == bundle
    failure = {'requirements': deepcopy(sheet['requirements']), 'diagnostics': deepcopy(sheet['diagnostics'])}
    projection = library('bvbrc_fastqutils_projection').project_fastqutils_facts(sheet, calculations,
        requested_form=selector['requested_schema'], parameters=parameters, failure_context=failure)
    assert projection['facts'] == fastq_oracle('EXPECTED_FACTS_002.json') and projection['status'] == 'ok'
    # Exact original encode_saved_components data shape; no missing application
    # writer/producer module is restored solely to manufacture fixture support.
    components = {'version':'fastqutils_saved_components_v2', 'calculations':calculations,
        'projection_failure_context':failure, 'native_requirements':projection['requirements'],
        'native_diagnostics':projection['diagnostics']}
    encoded = library('bvbrc_fastqutils_saved_codec').encode_failures(projection['requirements'], projection['diagnostics'])
    canonical = module('execution_contracts').canonical; digest = module('execution_contracts').digest
    def content(value, source=None):
        value_hash = digest(value)
        return {'source_ref':source or 'source_' + value_hash[:24], 'artifact_field':'artifact_ref',
            'artifact_ref':'artifact_' + value_hash, 'sha256':value_hash, 'byte_count':len(canonical(value).encode())}
    source = 'source_' + digest(bundle)[:24]
    saved = {'adapter_id':'bvbrc_fastqutils', 'adapter_version':'2', 'status':projection['status'],
        'facts':deepcopy(projection['facts']), **encoded, 'sheet_content':content(sheet), 'components_content':content(components)}
    body = {'version':module('bvbrc_appservice_publication').RESULT_VERSION, 'source_ref':source, 'reference':source,
        'record_refs':[source], 'assignment':{'selector':deepcopy(selector)}, 'bundle':bundle,
        'publication_inputs':{'selector':selector, 'adapter':deepcopy(selector['adapter']),
            'adapter_implementation_sha256':'0' * 64},
        'publication':{'bundle_content':content(bundle,source), 'result_record_refs':[source], 'adapter_result':saved}}
    # The all-zero pin is explicit controlled envelope metadata, not an actual
    # installed producer digest or authenticated host configuration.
    return body, sheet, components, projection['facts']

def test_committed_fastq_projection_oracle_is_not_a_host_envelope():
    bundle = fastq_oracle('ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json'); before = deepcopy(bundle)
    host = module('bvbrc_appservice_contracts')
    assert module('bvbrc_fastqutils_returns').validate_contract is host.validate_contract
    assert library('bvbrc_fastqutils_contracts').validate_contract('Host_ArtifactBundle', bundle) == bundle
    with pytest.raises(host.ContractValidationError) as caught:
        host.validate_contract('ArtifactBundle', bundle)
    assert type(caught.value) is host.ContractValidationError
    assert caught.value.code == 'output_association_path_conflict'
    assert caught.value.diagnostics[0]['path'] == '/artifacts/0'
    sheet = fastq_oracle('EXPECTED_SHEET_002.json'); calculations = fastq_oracle('EXPECTED_COMPONENTS_002.json')
    result = library('bvbrc_fastqutils_projection').project_fastqutils_facts(sheet, calculations,
        requested_form=fastq_oracle('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')['requested_schema'],
        parameters=fastq_oracle('PROVIDER_PARAMETERS_002.json'),
        failure_context={'requirements':deepcopy(sheet['requirements']), 'diagnostics':deepcopy(sheet['diagnostics'])})
    assert result['facts'] == fastq_oracle('EXPECTED_FACTS_002.json') and result['status'] == 'ok'
    assert bundle == before

def test_original_fastq_saved_oracle_survives_actual_return_projection():
    target = module('bvbrc_fastqutils_returns'); body,sheet,components,expected = fastq_saved_case()
    before = deepcopy((body,sheet,components))
    rows = target.project_fastqutils_return_facts(body, requested_sources=target.FACT_SOURCES, sheet=sheet, components=components)
    actual = {row['field']:row for values in rows.values() for row in values}
    assert len(actual) == len(expected)
    for field,value in expected.items():
        key = library('bvbrc_fastqutils_identity').field_ref('example195',field)
        assert target.decode_return_value(value['selection']['target']['kind'], actual[key]['value']) == value
    assert (body,sheet,components) == before

@pytest.mark.parametrize('corruption', ['saved_fact', 'saved_sheet_binding'])
def test_original_fastq_saved_corruption_keeps_exact_exception(corruption):
    target = module('bvbrc_fastqutils_returns'); body,sheet,components,_ = fastq_saved_case()
    # A later failure is meaningful only after the same actual reader accepts
    # this uncorrupted controlled envelope. No guard is patched or suppressed.
    before = deepcopy((body,sheet,components))
    assert target.project_fastqutils_return_facts(body, requested_sources=target.FACT_SOURCES, sheet=sheet, components=components)
    assert (body,sheet,components) == before
    if corruption == 'saved_fact':
        body['publication']['adapter_result']['facts']['read_count']['records'][0]['payload']['value'] += 1
        code = 'saved_projection_invalid'
    else:
        body['publication']['adapter_result']['sheet_content']['sha256'] = '0' * 64
        code = 'saved_sheet_content_conflict'
    with pytest.raises(target.FastqUtilsReturnError) as caught:
        target.project_fastqutils_return_facts(body, requested_sources=target.FACT_SOURCES, sheet=sheet, components=components)
    assert type(caught.value) is target.FastqUtilsReturnError
    assert caught.value.code == target._PREFIX + code
    if corruption == 'saved_fact':
        assert type(caught.value.__cause__) is library('bvbrc_fastqutils_contracts').FastqUtilsContractError


def test_original_phylogeny_saved_values_survive_actual_return_projection():
    from . import api_returns_phylogeny_fixture as original
    body, sheet = original.projection(); before = deepcopy((body, sheet))
    target = module('bvbrc_phylogeny_returns')
    facts = target.project_phylogeny_facts(body, requested_sources=target.FACT_SOURCES, sheet_set=sheet)
    assert original.numbers(facts) == {'tips':4, 'negative':-.5, 'zero':0, 'missing':None}
    assert type(original.numbers(facts)['tips']) is int
    assert facts[original.BRANCHES][0]['branches'][0]['length'] == -.125
    assert facts[original.SITES][0]['sites'][1]['gap_count'] == 1
    assert facts[original.MEMBERS][0]['members'][1]['representation'] == 'coding_nucleotide'
    assert facts[original.QUALIFICATIONS][0]['qualifications'][0]['role_ref'] == original.ref('role','raw_tree')
    communication = module('communication')
    schema = communication.validate_closed_schema(original.fact_form(*target.FACT_SOURCES))
    form = communication.form_with_facts({}, schema, facts)
    assert communication.validate_form(form, schema, lambda *_:True) == form
    assert (body,sheet) == before


def test_original_phylogeny_changed_saved_fact_is_rejected():
    from . import api_returns_phylogeny_fixture as original
    body,sheet = original.projection()
    body['publication']['adapter_result']['facts']['tips'] = True
    target = module('bvbrc_phylogeny_returns')
    with pytest.raises(ValueError) as caught:
        target.project_phylogeny_facts(body, requested_sources=target.FACT_SOURCES, sheet_set=sheet)
    assert type(caught.value) is ValueError
    assert str(caught.value) == 'bvbrc_phylogeny_return_saved_fact_type_conflict'
