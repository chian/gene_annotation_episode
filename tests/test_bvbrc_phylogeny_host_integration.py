"""Real configured host publication and typed parents; controlled native replies.

Journal selections and service responses are fixtures. Parsing, calculations,
custody, publication, requested forms and parent validation are production code.
This is not a shared-method_loop run or live native scientific execution.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_gene_tree_bundle_adapter as gene
from gene_annotation_episode import bvbrc_codon_tree_bundle_adapter as codon
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.bvbrc_phylogeny_returns import phylogeny_fact_sources
from gene_annotation_episode.communication import plain, form_with_facts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import SavedRecords
from test_bvbrc_appservice_host import ProductionDriver
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_phylogeny_bundle_resolution import fixture, slot
from test_bvbrc_phylogeny_returns import forbid_acquisition_or_scientific_work
from test_public_search import Client


MODES = ('gene_tree', 'concatenated_sequence_loci', 'core_genome_codon_protein')


def configured(module):
    return {**deepcopy(CONFIG), 'scientific_adapters': [{
        'adapter_id': module.ADAPTER_ID, 'adapter_version': module.ADAPTER_VERSION,
        'implementation_sha256': module.implementation_sha256()}]}


def supplied(mode):
    """Explicit synthetic native operands; no original native run is asserted."""
    provider = 'codon_tree' if mode == MODES[2] else 'gene_tree'
    module = codon if provider == 'codon_tree' else gene
    bundle, contents, _, parameters = fixture(provider)
    plan = parameters['analyses'][0]
    plan['analysis']['mode'] = mode
    plan['scientific_inputs'] = None
    plan['calculation_parameters']['alignment_requests'][0]['alphabet'] = 'unknown'
    if mode == MODES[1]:
        plan['analysis']['locus_ids'] = ['locusA', 'locusB']
    request = {'version': 'bvbrc_appservice_request_v1',
        'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'CodonTree' if provider == 'codon_tree' else 'GeneTree',
        'parameters': {'output_path': '/synthetic/output', 'output_file': 'tree'},
        'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [],
        'workspace_targets': []}
    if provider == 'gene_tree':
        paths = ['/synthetic/input/locusA.fa']
        if mode == MODES[1]:
            paths.append('/synthetic/input/locusB.fa')
            request['parameters']['genome_selection'] = {'concat_segments': True}
        request['parameters'].update(alphabet='Protein', recipe='RAxML',
            sequences=[{'type': 'aligned_protein_fasta', 'filename': path} for path in paths])
        request['input_bindings'] = [{'binding_id': 'locus'+str(index),
            'parameter_pointer': f'/sequences/{index}/filename', 'kind': 'workspace_object',
            'content': None, 'workspace_path': path, 'inline_value': None,
            'link_evidence': None, 'members': []} for index, path in enumerate(paths)]
    else:
        genomes = ['1075089.3', '1171377.3', '1222034.3', '1232659.5']
        request['parameters'].update(genome_ids=genomes, genome_groups=[],
            optional_genome_ids=[], number_of_genes=10, bootstraps=100,
            max_genomes_missing=1, max_allowed_dups=0)
        request['input_bindings'] = [{'binding_id': 'genomes', 'parameter_pointer': '/genome_ids',
            'kind': 'inline_parameter', 'content': None, 'workspace_path': None,
            'inline_value': genomes, 'link_evidence': None, 'members': []}]
    fields = {
        'tips': {'metric': 'tree_tip_count', 'analysis_id': 'a', 'population_id': 'leaves',
            'tree': slot('tree', tree=True)},
        'cells': {'metric': 'alignment_cell_count', 'analysis_id': 'a', 'population_id': 'matrix'},
        'gap_fraction': {'metric': 'alignment_gap_fraction', 'analysis_id': 'a', 'population_id': 'matrix'},
        'edges': {'metric': 'branch_rows', 'analysis_id': 'a', 'population_id': 'leaves',
            'tree': slot('tree', tree=True), 'node_indices': [2, 5]},
        'missing': {'metric': 'missing_requirements'}}
    files, requirements = [], []
    for index, artifact in enumerate(bundle['artifacts']):
        fmt = {**artifact['declared_format'], 'mode': mode}
        target_id = 'native-'+str(index)
        path = '/synthetic/output/'+target_id
        request['workspace_targets'].append({'target_id': target_id, 'path': path,
            'type': 'file', 'purpose': 'output_parent', 'input_binding_id': None,
            'metadata': {}, 'allow_overwrite': False, 'allow_create_parents': True})
        requirements.append({'requirement_id': target_id, 'role': artifact['role'],
            'required': True, 'declared_format': fmt, 'producer_rule_evidence': None,
            'exact_object': None})
        files.append({'object': {'kind': 'original_target', 'target_id': target_id},
            'role': artifact['role'], 'declared_format': fmt, 'requirement_ids': [target_id],
            'raw': contents[artifact['raw_artifact_ref']]})
    selection = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_projection',
        'requirements': requirements, 'adapter': {'adapter_id': module.ADAPTER_ID,
            'adapter_version': module.ADAPTER_VERSION, 'parameters': parameters},
        'requested_schema': module.requested_form_schema(fields), 'supplied_metadata': [],
        'supplied_capabilities': []}
    sources = phylogeny_fact_sources()
    form = {'type': 'object', 'properties': {
        key: sources['bvbrc_phylogeny_'+kind]['report_schema']
        for key, kind in [('numbers', 'measurements'), ('edges', 'branches'), ('missing', 'requirements')]},
        'required': ['numbers', 'edges', 'missing'], 'additionalProperties': False}
    return SimpleNamespace(module=module, request=request, selector=selection, files=files, form=form)


class HostDriver(ProductionDriver):
    def __init__(self, store, directory, case):
        self.saved, self.store = SavedRecords(store), store
        registry = ToolRegistry(store, clients=Client())
        self.family = ExecutionEpisodes(None, store=store, directory=directory,
            run_id=self.saved.run_id, resources={'selected-api': configured(case.module)},
            initial_information={}, tool_registry=registry, handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=128, log_roles=('stdout', 'stderr'))
        self.api = self.family.api_execution
        self.client = NativeClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None


def admit(d, parent, child):
    schema = plain(child.request)['report_contract']['measurements']['schema']
    facts = (d.family.facts(child, {}) if child.role == 'results'
        else d.family.received_report_facts(child))
    candidate = form_with_facts({}, schema, facts)
    d.saved.journal.save('runtime_forms', {'episode_id': child.episode_id,
        'facts': canonical(facts), 'form': canonical(candidate)})
    original = plain(child.request)['report_contract']
    typed = TypedReportContract(original['decision'], schema,
        lambda ref, namespace: d.family.resolve(child, ref, namespace),
        lambda value: d.family.validate_received_report(child, value, schema))
    form = plain(typed.admit(candidate, audit_identifiers=(child.episode_id,)).as_record())
    index = int(child.path[-1][1].removeprefix('child_'))
    d.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
        'decision_index': index, 'delivery_ref': 'delivery_'+digest([parent.episode_id, index])[:24],
        'child_episode_id': child.episode_id, 'contract': canonical(original),
        'form': canonical(form), 'failure': None})
    refs = d.family.received_form_references(parent, form, schema,
        f'{parent.run_id}:{parent.episode_id}:{index}:typed_form')
    d.saved.receipts.receive(parent.episode_id, refs, kind='child_form', source_index=index)
    return form, refs


@pytest.mark.parametrize('mode', MODES)
def test_configured_native_publication_reaches_two_parents_without_regrading(tmp_path, monkeypatch, mode):
    def no_network(*args, **kwargs):
        raise AssertionError('host integration attempted live transport')
    monkeypatch.setattr('socket.create_connection', no_network)
    monkeypatch.setattr('socket.socket.connect', no_network)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', no_network)
    case = supplied(mode)
    with Store(tmp_path/'state') as store:
        d = HostDriver(store, tmp_path, case)
        root = d.saved.root
        science = d.saved.child(root, 'scientific_process', {}, 0, schema=case.form)
        d.saved.root = science
        d.tree(case.request)
        preparation = d.call('prepare', {'definition': {'kind': 'packaged',
            'required_application_id': case.request['required_application_id']}})
        d.client.value = {'id': '123', 'application_id': case.request['required_application_id'], 'state_code': 'Q'}
        handoff = d.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})
        d.saved.admit(d.launch, d.context, handoff['source_ref'])
        d.saved.admit(science, d.launch, handoff['source_ref'])
        results = d.saved.child(science, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': handoff['source_ref'], 'selector': case.selector}, 3, schema=case.form)
        d.api.initialize(results)
        first = None
        for selected in case.files:
            d.client.value = ['https://fixture.invalid/'+selected['object']['target_id']]
            capability = d.call('download_capability', {'objects': [selected['object']],
                'generation': 0, 'predecessor_receipt_ref': None}, context=results)
            d.client.body = selected['raw']
            arguments = {key: deepcopy(selected[key]) for key in ('object', 'role', 'declared_format', 'requirement_ids')}
            arguments.update(max_bytes=1024 * 1024, byte_range=None, capability={'kind': 'acquired',
                'receipt_ref': capability['source_ref'], 'input_index': 0})
            receipt = d.call('download', arguments, context=results)
            reference = d.last_outcome['result']['source_ref']
            if first is None:
                first = d.api.read_result(reference, results.scope)
                assert first['publication']['completion_proof'] is None
                assert first['publication']['adapter_result']['facts']['tips'] is None
        body = d.api.read_result(reference, results.scope)
        saved = body['publication']['adapter_result']
        assert saved['facts']['tips'] == 4
        assert saved['facts']['cells'] == 16
        assert saved['facts']['gap_fraction'] == .125
        assert {row['reason_code'] for row in saved['facts']['missing']} == {
            'phylogeny_native_support_unavailable', 'phylogeny_bootstrap_counts_unavailable'}
        assert [row['length'] for row in saved['facts']['edges']] == [0, -.1]
        # Requested edge rows also ask for support/replicate counts, which this
        # fixture does not contain. Valid lengths must survive that partiality.
        assert body['publication']['completion_proof'] is None
        assert saved['status'] == 'partial'
        assert d.api.read_result(first['reference'], results.scope) == first
        sheet = d.api.appservice.publications.read_content_source(saved['sheet_content']['source_ref'], results.scope)
        assert sheet['analyses'][0]['sheet']['mode'] == mode
        # Freeze all scientific functions after the genuine publication. The
        # two typed admissions and later reads must copy their original facts.
        forbid_acquisition_or_scientific_work(monkeypatch)
        returned, refs = admit(d, science, results)
        forwarded, forwarded_refs = admit(d, root, science)
        assert returned == forwarded and refs == forwarded_refs == [reference]
        assert {row['field']: row['value'] for row in returned['numbers']} == {
            'tips': 4, 'cells': 16, 'gap_fraction': .125}
        assert d.family.received_report_facts(root) == {}
        expected = d.api.phylogeny_returns.received_facts(root, case.form)
        assert expected['bvbrc_phylogeny_measurements'] == forwarded['numbers']
        assert d.family.resolve_received_reference(science, 'edges', 'bvbrc_phylogeny_field') is True
        assert d.family.resolve_received_reference(root, 'not-requested', 'bvbrc_phylogeny_field') is False
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        count = store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
        calls = deepcopy(d.client.calls)
        assert d.api.phylogeny_returns.received_facts(root, case.form) == expected
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == count
        assert d.client.calls == calls


@pytest.mark.parametrize('module', [gene, codon])
def test_explicit_phylogeny_binding_rejects_wrong_implementation(module):
    pin, = configured(module)['scientific_adapters']
    assert bind_adapters([pin])[(module.ADAPTER_ID, '1')][0] is module
    with pytest.raises(ValueError, match='appservice_adapter_implementation_conflict'):
        bind_adapters([{**pin, 'implementation_sha256': '0'*64}])
