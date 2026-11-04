"""Real v2 host acquisition, publication and typed return with controlled transport.

The fixture records selected commissions/actions in the ordinary Journal. These
are host and typed-boundary checks, not a shared method_loop Workflow run.
"""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode import bvbrc_proteome_directional_fact_contracts as c
from gene_annotation_episode.bvbrc_proteome_returns import proteome_fact_sources, ProteomeReturnError
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.form_reference_validation import form_reference_validation
from gene_annotation_episode.state import Store
from bvbrc_proteome_host_fixture import ProteomeDriver, ControlledClient
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import SavedRecords, api_assignment, selector as support_selector
from test_bvbrc_proteome_bundle_v2_resolution import fixture as provider_fixture
from test_bvbrc_proteome_directional import native
from test_bvbrc_proteome_directional_projection import selector, forbid_construction


DIRECTIONAL_SOURCES = tuple('bvbrc_proteome_' + family for family in c.FAMILIES.values())


def selected_fields():
    return {'count': selector('directional_count', 'report', 'displayed_query_count'),
        'fraction': selector('directional_fraction', 'subject', 'compatible_unique_pair_resolved_identity'),
        'coverage': selector('directional_coverage', 'query', 'any_displayed_subject_query_paired_union'),
        'integer': selector('directional_native_integer', 'hsp', 'gap_count'),
        'decimal': selector('directional_native_decimal', 'hsp', 'expect'),
        'state': selector('directional_state', 'report', 'operand_binding'),
        'extremum': selector('directional_extremum', 'subject', 'minimum_reported_hsp_expectation'),
        'intervals': selector('directional_intervals', 'query', 'any_displayed_subject_query_paired_union', offset=0, limit=1),
        'columns': selector('directional_columns', 'block', offset=0, limit=2),
        'edges': selector('directional_edges', 'subject', offset=0, limit=2),
        'conflicts': selector('directional_conflicts', 'subject', offset=0, limit=2),
        'support': selector('directional_support', 'subject', collection='pair_geometry_support', member='included_blocks', offset=0, limit=2),
        'issues': selector('directional_issues', 'hsp', layer='numerical', offset=0, limit=2),
        'requirements': {'kind': 'directional_requirements', 'scope': 'all'}}


class DirectionalDriver(ProteomeDriver):
    def __init__(self, store, directory):
        self.saved, self.store = SavedRecords(store), store
        self.config = deepcopy(CONFIG)
        self.config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID,
            'adapter_version': adapter.ADAPTER_VERSION, 'implementation_sha256': adapter.implementation_sha256()}]
        self.family = ExecutionEpisodes(None, store=store, directory=directory, run_id=self.saved.run_id,
            resources={'selected-api': self.config}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.api, self.client = self.family.api_execution, ControlledClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None

    def form_schema(self, sources=DIRECTIONAL_SOURCES):
        return super().form_schema(sources)

    def start(self, *, fields=None, key='2221', sources=DIRECTIONAL_SOURCES):
        self.native_key, self.fmt = key, 'ncbi_blastall_blastp_pairwise_text_v1'
        self.schema = self.form_schema(sources)
        self.outer_root = self.saved.root
        self.grandparent = self.saved.child(self.outer_root, 'scientific_process', {}, 0, schema=self.schema)
        self.parent = self.saved.child(self.grandparent, 'scientific_process', {}, 0, schema=self.schema)
        self.saved.root = self.parent
        self.query = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
            'required_application_id': 'GenomeComparison', 'parameters': {
                'genome_ids': [], 'user_genomes': ['/unused.faa', '/ref.faa', '/subject.faa'],
                'user_feature_groups': [], 'reference_genome_index': 2,
                'output_path': '/controlled/proteome', 'output_file': 'selected'},
            'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}
        launch_assignment = {'version': 'execution_launch_assignment_v1',
            'requests': {'selected-api': api_assignment(self.query)}, 'immutable_input_versions': [],
            'constraints': {'allowed_kinds': ['api']}}
        self.launch = self.saved.child(self.parent, 'launch', launch_assignment, 10)
        self.saved.receipts.receive(self.launch.episode_id, self.custody.initial_references(self.launch), kind='initial')
        self.context = self.saved.child(self.launch, 'launch_api', api_assignment(self.query), 0)
        self.api._manifest(self.context)
        preparation = self.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'GenomeComparison'}})
        self.client.value = {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'Q'}
        self.handoff = self.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})
        source = self.handoff['value']['original_task']['submission_source_ref']
        self.submission_content = self.content(source, 'request_ref')
        references = [self.handoff['source_ref'], source]
        self.freeze_refs(self.launch, self.context, references)
        self.freeze_refs(self.parent, self.launch, references)
        self.support = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': self.handoff['source_ref'], 'selector': support_selector()}, 20)
        self.api.initialize(self.support)
        self.client.value = {'123': {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'C'}}
        self.status = self.call('status', {'handoff_ref': self.handoff['source_ref']}, context=self.support)
        self.info = self.call('task_info', {'handoff_ref': self.handoff['source_ref'], 'file': 'job_result_id'}, context=self.support)
        self.freeze_refs(self.parent, self.support, [self.info['source_ref']])
        parameters = provider_fixture(key)['parameters']
        parameters['analysis_id'] = 'controlled-directional-host'
        self.declared_format = deepcopy(parameters['directional_documents'][0]['declared_format'])
        self.selected = support_selector()
        self.selected['supplied_metadata'] = [dict(content=self.content(self.info['source_ref']), pointer='/value')]
        self.selected.update(endpoint='requested_projection', supplied_contents=[],
            adapter={'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION, 'parameters': parameters},
            requested_schema=adapter.requested_form_schema(selected_fields() if fields is None else fields))
        self.selected['requirements'] = [dict(requirement_id='directional', role='proteome_directional_report', required=True,
            declared_format=deepcopy(self.declared_format), producer_rule_evidence=None, exact_object=None)]
        self.context = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': self.handoff['source_ref'], 'selector': self.selected}, 22, schema=self.schema)
        self.frozen_assignment = deepcopy(plain(self.context.assignment))
        self.api.initialize(self.context)
        return self.context

    def native_arguments(self):
        args = super().native_arguments()
        args.update(requirement_ids=['directional'], role='proteome_directional_report', declared_format=deepcopy(self.declared_format))
        return args

    def acquire_native(self, *, raw=None):
        args = self.native_arguments()
        self.client.body = native(self.native_key) if raw is None else raw
        self.native = self.call('download', args, context=self.context)
        return self.publication()


@pytest.fixture
def driver(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail('controlled directional host attempted live network')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        yield DirectionalDriver(store, tmp_path)


def test_all_fourteen_actual_sources_reach_own_frozen_admitted_and_forwarded_returns(driver):
    d = driver
    d.start()
    d.acquire_manifest()
    body = d.acquire_native()
    assert d.frozen_assignment == plain(d.context.assignment)
    assert d.service.scientific_adapters[('bvbrc_proteome', '2')][0] is adapter
    assert d.store.get_artifact(d.native['value']['artifact']['raw_artifact_ref']) == native('2221')
    host = d.api.appservice.facts(d.context)
    own = d.family.facts(d.context, {})
    assert all(host[name] == own[name] and len(own[name]) == 1 for name in DIRECTIONAL_SOURCES)
    facts = body['publication']['adapter_result']['facts']
    assert facts['decimal']['cell']['value'] == dict(sign=0, digits=[2], exponent=-66)
    assert facts['fraction']['cell']['value']['numerator'] == facts['fraction']['cell']['value']['denominator'] == 468
    assert facts['fraction']['pair_population']['unresolved_pairs'] == 61
    assert d.api._completion(d.context) is None  # Requested missing native gap stays unavailable.
    form, key, references = d.admit_numeric()
    assert set(references) == {body['source_ref'], d.native['value']['artifact']['source_ref']}
    assert d.family.received_report_facts(d.parent) == {name: own[name] for name in DIRECTIONAL_SOURCES}
    forwarded, _, forwarded_refs = d.admit_numeric(to_grandparent=True)
    assert forwarded == form and forwarded_refs == references
    assert d.family.received_report_facts(d.grandparent) == d.family.received_report_facts(d.parent)
    assert d.family.received_report_facts(d.outer_root) == {}
    with form_reference_validation():
        for source, rows in d.api.proteome_returns._values(form, d.schema).items():
            for row in rows:
                assert d.api.resolve(d.context, row['field'], 'bvbrc_proteome_field')
                assert d.family.resolve(d.context, row['field'], 'bvbrc_proteome_field')
                assert d.family.resolve_received_reference(d.parent, row['field'], 'bvbrc_proteome_field')
        assert d.family.resolve_received_reference(d.parent, 'd', 'bvbrc_proteome_document')
        assert not d.family.resolve_received_reference(d.parent, 'unrequested-document', 'bvbrc_proteome_document')
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('mutation', ['number', 'source', 'document', 'duplicate', 'noncanonical_decimal'])
def test_actual_return_rejects_changed_fact_identity_or_exact_numbers(driver, mutation):
    d = driver
    d.start(fields={'decimal': selected_fields()['decimal']}, sources=('bvbrc_proteome_directional_native_decimals',))
    d.acquire_manifest(); d.acquire_native()
    facts = d.family.facts(d.context, {})
    form = {'fact0': deepcopy(facts['bvbrc_proteome_directional_native_decimals'])}
    if mutation == 'number': form['fact0'][0]['value']['cell']['value']['exponent'] = -65
    elif mutation == 'source': form['fact0'][0]['source_ref'] = d.native['value']['artifact']['source_ref']
    elif mutation == 'document': form['fact0'][0]['value']['context']['target']['document_id'] = 'foreign'
    elif mutation == 'duplicate': form['fact0'].append(deepcopy(form['fact0'][0]))
    else: form['fact0'][0]['value']['cell']['value'] = dict(sign=0, digits=[2, 0], exponent=-67)
    with pytest.raises(ValueError): d.family.validate_received_report(d.context, form, d.schema)


def test_saved_parent_return_replay_performs_no_scientific_construction(driver, monkeypatch):
    d = driver
    d.start(fields={'decimal': selected_fields()['decimal']}, sources=('bvbrc_proteome_directional_native_decimals',))
    d.acquire_manifest(); body = d.acquire_native()
    form, key, refs = d.admit_numeric()
    before = [dict(row) for row in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')]
    calls = deepcopy(d.client.calls)
    forbidden = forbid_construction(monkeypatch)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    assert d.api.read_result(body['source_ref'], d.context.scope) == body
    assert d.family.received_report_facts(d.parent)['bvbrc_proteome_directional_native_decimals'] == form['fact0']
    assert d.family.received_form_references(d.parent, form, d.schema, key) == refs
    assert d.client.calls == calls
    assert [dict(row) for row in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')] == before


def test_owner_version_and_original_pin_remain_required(driver):
    d = driver
    d.start(fields={'decimal': selected_fields()['decimal']})
    d.acquire_manifest(); d.acquire_native()
    for field, value in [('run_id', 'foreign'), ('episode_id', 'foreign'), ('scope', {}), ('assignment', {})]:
        with pytest.raises(ValueError): d.api.proteome_returns.facts(replace(d.context, **{field: value}), d.schema)
    configuration = d.api.configuration['selected-api']['scientific_adapters']
    original = deepcopy(configuration)
    try:
        configuration[0]['adapter_version'] = '1'
        with pytest.raises(ValueError, match='appservice_publication_adapter_configuration_conflict'): d.api.proteome_returns.facts(d.context, d.schema)
    finally:
        configuration[:] = original
