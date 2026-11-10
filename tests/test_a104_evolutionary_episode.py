"""Molecular identity, actual-result admission and zero-credit controls for A104.

These checks do no biological computation and launch no scheduler. Native real
run fixtures are tested separately from these deliberate contract controls.
"""
from copy import deepcopy
import json
from pathlib import Path
import asyncio

import pytest

from gene_annotation_episode.a104_hpc import prepare_request, request_body, native_body, commission, import_result
from gene_annotation_episode.a104_hpc_worker import validate_request, alignment_correspondence, tree_summary
from gene_annotation_episode.a104_credit import (A104EvolutionaryCredit,
    A104PanelIdentityCredit, A104AlignmentSuitabilityCredit)
from gene_annotation_episode.a104_investigation import initial_report, resolve_report
from gene_annotation_episode.a104_tools import catalog
from gene_annotation_episode.a104_characterization import clade_sheet
from gene_annotation_episode.hpc_campaign import validate_commission
from gene_annotation_episode.state import Store


REAL = Path(__file__).parent/'fixtures/a104/real/yjeh'


def operands(store):
    source_path = REAL/'family-yjeh.json'
    raw = source_path.read_bytes()
    artifact = store.artifact(raw, 'application/json')
    source = store.put('source', {'provider': 'retained.uniprot', 'accession': 'original-YjeH-response',
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'uri': None,
        'version': 'real-input-contract-check', 'retrieved_at': None}, origin='external')['id']
    refs, entries = [], json.loads(raw)['results'][:4]
    for entry in entries:
        symbols = entry['sequence']['value']
        refs.append(store.put('reference', {'reference_type': 'protein', 'source_ref': source,
            'accession': entry['primaryAccession'], 'label': 'Acquired reference',
            'sequence_ref': store.artifact(symbols, 'text/plain'), 'molecule': 'protein',
            'length': len(symbols), 'term_refs': [], 'context_refs': []}, origin='external')['id'])
    target, = store.create_problem(raw_sequence=entries[0]['sequence']['value'], molecule='protein')['subject_refs']
    known, scope = [target, source, *refs], {'subject_refs': [target]}
    analysis = {'name': 'family', 'purpose': 'family', 'members': [
        {'tip_id': 'tip_'+str(i), 'parts': [{'subject_ref': target if i == 0 else reference}],
         'taxon_id': entries[i]['organism']['taxonId']} for i, reference in enumerate(refs)]}
    return target, refs, known, scope, analysis


def test_anonymous_sequence_does_not_inherit_taxonomy_from_identical_reference(tmp_path):
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, analysis = operands(store)
        with pytest.raises(ValueError, match='tip_taxon_requires_actual_matching_metadata'):
            prepare_request(store, target_ref=target, analyses=[analysis], scope=scope,
                            known_record_refs=known, case_id='anonymous')
        analysis['members'][0].pop('taxon_id')
        reference = prepare_request(store, target_ref=target, analyses=[analysis], scope=scope,
                                   known_record_refs=known, case_id='anonymous')
        body = request_body(store, reference)
        assert body['bindings'][0]['members'][0]['taxon_id'] is None
        assert body['bindings'][0]['members'][0]['taxon_evidence'] == []
        assert body['bindings'][0]['members'][0]['parts'][0]['target_regions'] == [[0, store.subject_length(target)]]
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=[*known, reference])['credit'] == 0


def test_exact_request_has_one_real_target_and_no_local_scientific_execution(tmp_path):
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, analysis = operands(store)
        reference = prepare_request(store, target_ref=target, analyses=[analysis], scope=scope,
            known_record_refs=known, case_id='exact', target_origin_reference_ref=refs[0])
        body = request_body(store, reference)
        assert validate_request(deepcopy(body['native_request'])) == body['native_request']
        resources = json.loads((Path(__file__).parents[1]/'examples/aurora_execution_resources.json').read_text())
        work = commission(store, reference, resources['aurora'])
        validate_commission(work, resources)
        assert work['candidates'][0]['nodes'] == 1
        candidate = work['candidates'][0]
        assert candidate['features']['worker_threads'] == body['native_request']['threads']
        assert candidate['features']['input_residue_count'] == sum(len(row['sequence'])
            for row in body['native_request']['analyses'][0]['entries'])
        assert work['execution_profile']['tool'] == 'a104.phylogeny'
        assert work['execution_profile']['implementation'] == body['worker_sha256']
        assert 'memory_bytes' not in candidate.get('resource_capacity', {})
        assert set(work['model']['resource_priors']) == {'cpu_seconds', 'memory_bytes'}
        assert {slot['metric'] for slot in work['credit']['validation_slots']} == {
            'queue', 'work', 'cpu_seconds', 'memory_bytes'}
        from gene_annotation_episode import hpc_prediction
        forecast = hpc_prediction.predict(hpc_prediction.prior_model(work['model']), candidate['features'])
        assert forecast['support']['observations'] == 0
        assert all(forecast['resources'][name] is not None for name in ('cpu_seconds', 'memory_bytes'))
        assert work['candidates'][0]['units'][0]['argv'][0] == resources['aurora']['python_executable']
        assert 'begin sets;' in body['worker_text']
        assert all(row['resources'] == 'local' for row in catalog().values())
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=known)['credit'] == 0


def test_saved_frozen_panel_earns_only_its_commissioned_preparation_credit(tmp_path):
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, analysis = operands(store)
        annotation = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        assigned = {'scope': scope, 'proposed_annotation_ref': annotation}
        panel = A104PanelIdentityCredit()
        alignment = A104AlignmentSuitabilityCredit()
        assert panel(store, scope, known_record_refs=[*known, annotation],
            assignment=assigned)['credit'] == 0
        request = prepare_request(store, target_ref=target, analyses=[analysis], scope=scope,
            known_record_refs=known, case_id='panel-credit', target_origin_reference_ref=refs[0])
        received = [*known, annotation, request]
        result = panel.read_details(store, scope, known_record_refs=received * 2,
            assignment=assigned, details_limit=1)
        assert result['credit'] == 1
        assert result['source_contributions'][0]['source_ref'] == request
        assert alignment(store, scope, known_record_refs=received,
            assignment=assigned)['credit'] == 0
        native = A104EvolutionaryCredit()
        native_result = native(store, scope, known_record_refs=received, assignment=assigned)
        assert native_result['credit'] == 0
        from gene_annotation_episode.a104_credit import combine_received_task_progress
        assert combine_received_task_progress([(panel, result), (alignment,
            alignment(store, scope, known_record_refs=received, assignment=assigned)),
            (native, native_result)]) == 1


def test_renamed_or_changed_native_sequences_are_not_correspondence():
    entries = [{'tip_id': 'target', 'sequence': 'ACDE'}, {'tip_id': 'ref', 'sequence': 'ACDF'}]
    mapping = alignment_correspondence({'target': 'AC-DE', 'ref': 'ACD-F'}, entries)
    assert mapping['rows'][0]['alignment_to_residue_segments'] == [[0, 0, 2], [3, 2, 2]]
    with pytest.raises(ValueError, match='changed_original_sequence'):
        alignment_correspondence({'target': 'AC-DF', 'ref': 'ACD-F'}, entries)
    with pytest.raises(ValueError, match='membership_conflict'):
        alignment_correspondence({'wrong': 'AC-DE', 'ref': 'ACD-F'}, entries)


@pytest.mark.parametrize('receipt_extent,receipt_run,receiving_extent,expected_error', [
    ('full', 'scope-control', 'implicit', 'a104_original_completed_runtime_required'),
    ('full', 'scope-control', 'full', 'a104_original_completed_runtime_required'),
    ('partial', 'scope-control', 'implicit', 'a104_hpc_receiving_run_conflict'),
    ('full', 'another-run', 'implicit', 'a104_hpc_receiving_run_conflict'),
    ('full', 'scope-control', 'partial', 'a104_hpc_original_scope_conflict'),
])
def test_native_reader_accepts_equivalent_full_scope_but_retains_custody_guards(
        tmp_path, receipt_extent, receipt_run, receiving_extent, expected_error):
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, analysis = operands(store)
        request = prepare_request(store, target_ref=target, analyses=[analysis], scope=scope,
            known_record_refs=known, case_id='scope-control', target_origin_reference_ref=refs[0])
        def extent(kind):
            if kind == 'implicit':
                return scope
            return {**scope, 'segments': [{'target_ref': target, 'start': 0,
                'end': store.subject_length(target)-(1 if kind == 'partial' else 0), 'unit': 'aa'}]}
        # Deliberately incomplete receipt: passing scope must still require
        # original completed runtime custody and must never grant native credit.
        raw = json.dumps({'run_id': receipt_run, 'scope': extent(receipt_extent)})
        artifact = store.artifact(raw, 'application/json')
        receipt = store.put('source', {'provider': 'episode.hpc_result', 'accession': 'scope-control',
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'uri': None,
            'version': 'hpc_result_v1', 'retrieved_at': None}, origin='tool')['id']
        with pytest.raises(ValueError, match=expected_error):
            import_result(store, request_ref=request, hpc_result_ref=receipt,
                known_record_refs=[*known, request, receipt], scope=extent(receiving_extent), run_id='scope-control')
        assert store.db.execute('SELECT COUNT(*) FROM a104_native_results').fetchone()[0] == 0
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=[*known, request, receipt])['credit'] == 0


def test_representation_root_and_unknown_support_do_not_become_ancestry_or_zero():
    value = tree_summary('((a:1,b:1):1,(c:1,d:1):1);')
    assert value['biological_root'] == 'unestablished'
    assert value['splits'][0]['support_percent'] is None
    assert value['splits'][0]['support_state'] == 'unknown'


def test_native_tree_claim_requires_actual_received_execution(tmp_path):
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, analysis = operands(store)
        report = {**initial_report(), 'phylogeny_status': 'native_trees_received',
                  'records': [], 'phylogenetic_credit': 0.}
        with pytest.raises(ValueError, match='native_tree_statement_requires_received_original_execution'):
            resolve_report(store, report, scope=scope)


def test_copied_native_provider_label_is_not_host_scientific_custody(tmp_path):
    with Store(tmp_path/'state') as store:
        artifact = store.artifact('{}', 'application/json')
        source = store.put('source', {'provider': 'native.a104.phylogeny', 'accession': 'forged',
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'uri': None,
            'version': 'a104_shared_hpc_custody_v1', 'retrieved_at': None}, origin='external')['id']
        with pytest.raises(ValueError, match='host_scientific_grant_required'):
            native_body(store, source)


def test_clade_functions_keep_uncharacterized_and_mixed_members():
    def link(subject, function):
        return {'reference_ref': subject, 'function_key': function, **{name: name+'_'+subject for name in
            ('hypothesis_ref', 'assessment_ref', 'observation_ref', 'sheet_ref', 'evidence_source_ref')}}
    partial = clade_sheet({'a', 'b', 'c'}, [link('a', 'x')])
    assert partial['unknown_subject_refs'] == ['b', 'c']
    assert not partial['all_sampled_references_have_one_observed_activity']
    mixed = clade_sheet({'a', 'b'}, [link('a', 'x'), link('b', 'y')])
    assert mixed['status'] == 'mixed_characterized_functions'
    assert not mixed['all_sampled_references_have_one_observed_activity']


def test_new_native_requests_preserve_region_lineage_and_distinct_model_seed(tmp_path):
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, family = operands(store)
        family['members'][0].pop('taxon_id')
        sensitivity = deepcopy(family)
        sensitivity.update(name='alternative', purpose='sensitivity', model='MFP', seed=105)
        regional = deepcopy(family)
        regional.update(name='region', purpose='regional')
        regional['members'][0]['parts'][0]['regions'] = [[11, 29], [40, 60]]
        reference = prepare_request(store, target_ref=target, analyses=[family, sensitivity, regional],
            scope=scope, known_record_refs=known, case_id='different_native_tests')
        body = request_body(store, reference)
        assert body['native_request']['analyses'][1]['model'] == 'MFP'
        assert body['native_request']['analyses'][1]['seed'] == 105
        part = body['bindings'][2]['members'][0]['parts'][0]
        assert part['target_regions'] == [[11, 29], [40, 60]]
        assert part['selected_residue_to_subject_segments'] == [[0, 11, 18], [18, 40, 20]]
        assert part['original_mapping'] is not None
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=[*known, reference])['credit'] == 0


def test_new_scientific_tool_inputs_have_closed_object_schemas():
    from gene_annotation_episode.schema_support import _schema_nodes
    for operation in catalog().values():
        for path, node in _schema_nodes(operation['input_schema']):
            if isinstance(node, dict) and node.get('type') == 'object':
                assert node.get('additionalProperties') is False, path


def test_parent_wait_generation_needs_an_actual_pending_producer():
    from gene_annotation_episode.a104_investigation import parent_generation_schema
    schema = {'properties': {'response': {'anyOf': [{'properties': {'selection': {'anyOf': [
        {'properties': {'kind': {'enum': ['wait']}}},
        {'properties': {'kind': {'enum': ['tool']}}}]}}}]}}}
    original = deepcopy(schema)
    without = parent_generation_schema({'fields': {'pending_work': {'items': []}}}, schema)
    assert [branch['properties']['kind']['enum'] for branch in
        without['properties']['response']['anyOf'][0]['properties']['selection']['anyOf']] == [['tool']]
    assert parent_generation_schema({'fields': {'pending_work': {'items': [{'handle': 'actual_job'}]}}}, schema) == schema
    assert parent_generation_schema({'fields': {}}, schema) == schema
    assert schema == original


def test_reference_history_requires_actual_independent_marker_identities(tmp_path):
    from collections import defaultdict
    from gene_annotation_episode.a104_hpc import independent_marker_basis
    from tools.a104_inputs import MARKERS, gene_names
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, family = operands(store)
        raw = (REAL/'yjeh-organismal-markers.json').read_bytes()
        artifact = store.artifact(raw, 'application/json')
        source = store.put('source', {'provider': 'retained.uniprot', 'accession': 'original-ribosomal-markers',
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'uri': None,
            'version': 'real_input_control', 'retrieved_at': None}, origin='external')['id']
        groups = defaultdict(dict)
        for entry in json.loads(raw)['results']:
            group = next((name for name, genes in MARKERS.items() if gene_names(entry) & genes), None)
            if group:
                peptide = entry['sequence']['value']
                reference = store.put('reference', {'reference_type': 'protein', 'source_ref': source,
                    'accession': entry['primaryAccession'], 'label': 'Actual acquired marker',
                    'sequence_ref': store.artifact(peptide, 'text/plain'), 'molecule': 'protein',
                    'length': len(peptide), 'term_refs': [], 'context_refs': []}, origin='external')['id']
                groups[entry['organism']['taxonId']][group] = reference
        organismal = {'name': 'reference', 'purpose': 'organismal_reference',
            'organismal_basis': {'kind': 'independent_ribosomal_marker_supermatrix', 'markers': list(MARKERS)},
            'members': [{'tip_id': 'tax_'+str(taxon), 'taxon_id': taxon,
                'parts': [{'subject_ref': parts[group]} for group in MARKERS]}
                for taxon, parts in groups.items() if set(parts) == set(MARKERS)]}
        independent_marker_basis(store, organismal)
        # A real acquired YjeH protein is still not a ribosomal marker merely
        # because it has known taxonomic metadata and a changed purpose label.
        taxon = json.loads((REAL/'family-yjeh.json').read_text())['results'][0]['organism']['taxonId']
        bad = deepcopy(organismal)
        bad['members'] = [{'tip_id': 'fake_reference', 'taxon_id': taxon,
                          'parts': [{'subject_ref': refs[0]} for _ in MARKERS]}]
        with pytest.raises(ValueError, match='marker_identity_not_supported'):
            independent_marker_basis(store, bad)


def test_selected_translated_region_keeps_reverse_codon_mapping(tmp_path):
    from gene_annotation_episode.sequence_mapping import translation_mapping
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='AGCCAT'*4, molecule='dna')['subject_refs']
        artifact = store.artifact('{"engineering_control":"explicit translation lineage"}', 'application/json')
        source = store.put('source', {'provider': 'sequence.translate', 'accession': 'engineering_control',
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'uri': None,
            'version': 'control', 'retrieved_at': None}, origin='tool')['id']
        processing = store.put('context', {'context_type': 'processing', 'name': 'engineering_translation_model',
            'source_ref': source, 'attributes': [], 'related_refs': [target]}, origin='tool')['id']
        feature = store.put('feature', {'subject_ref': target, 'kind': 'CDS', 'segments': [{'start': 0, 'end': 24}],
            'strand': '-', 'context_refs': [processing]}, origin='tool')['id']
        mapping = translation_mapping(store.sequence_mapping(target)['path'], start=0, end=24,
                                      strand='-', protein_length=8)
        product = store.put('product', {'parent_refs': [feature], 'molecule': 'protein',
            'sequence_ref': store.artifact('MAMAMAMA', 'text/plain'), 'derivation': 'translation',
            'context_refs': [processing], 'footprint': store.footprint_from_mapping(mapping),
            'mapping': mapping, 'mapping_source_ref': source}, origin='tool')['id']
        refs = [store.put('reference', {'reference_type': 'protein', 'source_ref': source,
            'accession': 'engineering_'+str(i), 'label': 'Controlled reference '+str(i),
            'sequence_ref': store.artifact(peptide, 'text/plain'), 'molecule': 'protein', 'length': len(peptide),
            'term_refs': [], 'context_refs': []}, origin='external')['id']
            for i, peptide in enumerate(('MAMAMAMA', 'MAMAMAMT', 'MAMAMAMS', 'MAMAMAMG'))]
        family = {'name': 'region', 'purpose': 'regional', 'members': [
            {'tip_id': 'target', 'parts': [{'subject_ref': product, 'regions': [[1, 5]]}]},
            *[{'tip_id': 'reference_'+str(i), 'parts': [{'subject_ref': ref}]} for i, ref in enumerate(refs[1:])]]}
        known, scope = [target, source, processing, feature, product, *refs], {'subject_refs': [target]}
        reference = prepare_request(store, target_ref=target, analyses=[family], scope=scope,
            known_record_refs=known, case_id='translated_region_control', target_origin_reference_ref=refs[0])
        part = request_body(store, reference)['bindings'][0]['members'][0]['parts'][0]
        assert part['target_regions'] == [[9, 21]]
        assert part['original_mapping']['units_per_symbol'] == 3
        assert part['original_mapping']['path'][0]['strand'] == '-'
        assert part['selected_residue_to_subject_segments'] == [[0, 1, 4]]
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=[*known, reference])['credit'] == 0


def test_credit_read_is_pure_and_a_third_variant_requires_an_actual_comparison(tmp_path, monkeypatch):
    from gene_annotation_episode import a104_credit
    with Store(tmp_path/'state') as store:
        target, _, known, scope, _ = operands(store)
        def row(measurement, variant, value, **extra):
            return {'source_ref': measurement, 'grading_artifact_ref': 'engineering_control',
                'measurement_ref': measurement, 'target_ref': target, 'target_regions': [[0, store.subject_length(target)]],
                'qualification_dependencies': [measurement], 'score': value, 'raw_value': value,
                'policy': 'phylogeny.measure_placement_original_native_operands_v1',
                'variant_group': 'panel', 'variant': variant, 'state': 'attributed_phylogeny_received',
                'missing': [], **extra}
        attachments = [row('first', 'LG', .9), row('second', 'MFP', .8),
            row('compared', None, .7, variant_group=None,
                policy='phylogeny.compare_placements_original_native_operands_v1',
                compared_variant_group='panel', compared_variants=['LG', 'MFP'])]
        monkeypatch.setattr(a104_credit, 'received_attachments', lambda *_: deepcopy(attachments))
        before = store.db.total_changes
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=known)['credit'] == pytest.approx(.1)
        assert store.db.total_changes == before
        attachments.append(row('third', 'WAG', .95))
        view = A104EvolutionaryCredit()(store, scope, known_record_refs=known)
        assert view['credit'] == 0
        assert view['target_sheets'][target]['unresolved_variant_groups'] == ['panel']
        assert store.db.total_changes == before


def test_received_dynamic_commission_uses_existing_hpc_owner_and_cannot_change_scope(tmp_path):
    from gene_annotation_episode.hpc_commission_sources import publish, read
    from gene_annotation_episode.hpc_episodes import HPCEpisodes
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.domain import validate_schema
    from hpc_helpers import commission as work, resources
    with Store(tmp_path/'state') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='ACDE', molecule='protein')['subject_refs']}
        definition, configured = work(), resources()
        reference = publish(store, definition, scope=scope, resources=configured)
        assert read(store, reference, scope=scope, resources=configured) == definition
        binding = HPCEpisodes(object(), store=store, run_id='test', directory=tmp_path/'hpc',
            resources=configured, commissions={'original': definition})
        assignment = {'commission_source_ref': reference}
        parent = BindingContext('test', 'parent', 'annotation', (('annotation', 'parent'),), scope, {}, {})
        with pytest.raises(ValueError, match='source_not_received'):
            binding.prepare_assignment(parent, 'hpc', assignment, scope, 'first')
        parent = BindingContext('test', 'parent', 'annotation', (('annotation', 'parent'),), scope, {}, {}, (reference,))
        assert binding.prepare_assignment(parent, 'hpc', assignment, scope, 'first') == assignment
        validate_schema(assignment, binding.assignment_schema('hpc'))
        with pytest.raises(ValueError):
            validate_schema({**assignment, 'commission_id': 'original'}, binding.assignment_schema('hpc'))
        owner = BindingContext('test', 'hpc-owner', 'hpc', (('hpc', 'hpc-owner'),), scope, assignment, {}, (reference,))
        ledger = binding.state(owner)
        assert ledger.read('owner')['commission_source_ref'] == reference
        child = {'commission_source_ref': reference, 'owner_episode_id': 'hpc-owner'}
        assert binding.prepare_assignment(owner, 'hpc_execution', child, scope, 'second') == child
        changed = deepcopy(configured)
        changed[definition['resource_id']]['workspace'] += '/changed'
        with pytest.raises(ValueError, match='resource_changed'):
            read(store, reference, scope=scope, resources=changed)


def test_native_measurement_observation_is_usable_without_transcribing_json(tmp_path, monkeypatch):
    from gene_annotation_episode import a104_publication as publication
    with Store(tmp_path/'state') as store:
        target, refs, known, scope, _ = operands(store)
        source = store.put('source', {'provider': 'engineering_control', 'accession': 'measurement',
            'artifact_ref': store.artifact('{}', 'application/json'), 'uri': None,
            'text_ref': None, 'request_ref': None, 'version': 'control', 'retrieved_at': None}, origin='tool')['id']
        # Isolate presentation conversion; native-custody tests exercise the
        # actual measurement grant. This control claims no biological result.
        body = {'schema': 'a104_placement_v1', 'target_ref': target,
            'target_regions': [[11, 29]], 'native_phylogeny_ref': source, 'raw_value': .6,
            'bootstrap_population': {'matches': 600, 'denominator': 1000}, 'clade_members': []}
        monkeypatch.setattr(publication, 'received_measurement', lambda *_: {'body': body})
        observation = store.get(publication.native_observation(store, source))
        assert observation['origin'] == 'tool' and observation['source_ref'] == source
        assert observation['anchor'] is None
        assert observation['operand_intervals'] == [{'subject_ref': target, 'role': 'query',
            'start': 11, 'end': 29, 'unit': 'aa'}]
        assert {row['name']: row['value']['value'] for row in observation['measurements']} == {
            'bootstrap_split_matches': 600, 'bootstrap_split_denominator': 1000, 'bootstrap_split_frequency': .6}
        assert A104EvolutionaryCredit()(store, scope, known_record_refs=[*known, source, observation['id']])['credit'] == 0


def test_robustness_task_counts_saved_opposing_zero_once_for_its_annotation(tmp_path):
    from gene_annotation_episode.a104_attachments import PROVIDER, install
    from gene_annotation_episode.a104_credit import A104RobustnessCredit
    from gene_annotation_episode.a104_scoring import VERSION
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='ACDEFG', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        annotation = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        measurement = store.put('source', {'provider': 'engineering.native_measurement',
            'accession': 'robustness-zero', 'uri': None,
            'artifact_ref': store.artifact('{}', 'application/json'), 'text_ref': None,
            'request_ref': None, 'version': VERSION, 'retrieved_at': None}, origin='tool')['id']
        body = {'schema': 'a104_per_use_attribution_v1', 'version': VERSION,
            'measurement_ref': measurement, 'target_ref': target,
            'target_regions': [[0, 6]],
            'policy': 'phylogeny.compare_placements_original_native_operands_v1',
            'score': 0., 'raw_value': 0., 'state': 'attributed_phylogeny_received',
            'missing': [], 'qualification_dependencies': [measurement],
            'variant_group': None, 'variant': None,
            'compared_variant_group': 'panel', 'compared_variants': ['LG', 'MFP']}
        install(store)
        artifact = store.artifact(canonical(body), 'application/json')
        grading = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=artifact,
            grading={'grader': VERSION, 'failure': None, 'sheet': body})
        source = store.put('source', {'provider': PROVIDER, 'accession': 'saved-robustness-zero',
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': VERSION, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading]},
            origin='tool')['id']
        store.db.execute('INSERT INTO a104_attachments VALUES(?,?,?,?,?)',
            (source, measurement, target, canonical(body), grading))
        observed = store.put('observation', {'subject_refs': [target],
            'source_subject_refs': [], 'kind': 'comparison', 'source_ref': measurement,
            'measurements': [], 'dependencies': [], 'anchor': None,
            'operand_intervals': [{'subject_ref': target, 'role': 'query', 'start': 0,
                'end': 6, 'unit': 'aa'}]}, origin='tool')['id']
        assessed = store.put('assessment', {'hypothesis_ref': annotation,
            'observation_ref': observed, 'relation': 'weakens', 'applicability': 'direct',
            'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
            'expected_revision': 0},
            origin='reasoning')['id']
        known = [target, annotation, measurement, source, observed, assessed]
        selected = {'scope': scope, 'proposed_annotation_ref': annotation}
        credit = A104RobustnessCredit()
        assert credit(store, scope, known_record_refs=known[:-1], assignment=selected)['credit'] == 0
        assert credit(store, scope, known_record_refs=known * 2, assignment=selected)['credit'] == 1
        page = credit.read_details(store, scope, known_record_refs=known, assignment=selected,
            details_limit=1, details_offset=0)
        assert page['source_contributions'][0]['native_value'] == 0
        assert page['source_contributions'][0]['assessment_refs'] == [assessed]
        from gene_annotation_episode.a104_credit import combine_received_task_progress
        assert combine_received_task_progress([(credit, page)]) == 1


def test_only_particular_native_assay_criteria_qualify_reference_activity(tmp_path, monkeypatch):
    from gene_annotation_episode.a104_characterization import native_assay_qualification
    from gene_annotation_episode.literature_assay_grading_storage import LiteratureAssayGradingRepository as Repository
    from gene_annotation_episode.literature_assay_grading import grade_assay
    from test_literature_assay_grading import fixture
    with Store(tmp_path/'state') as store:
        artifact = store.artifact('{}', 'application/json')
        sheet = store.put('source', {'provider': 'literature.a105.assay_grading', 'accession': 'engineering_control',
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'uri': None,
            'version': 'control', 'retrieved_at': None}, origin='tool')['id']
        inputs = fixture('activity_rate')
        saved = {'sheet': grade_assay(inputs), 'selection': {'source_ref': 'source_engineering_assay'}}
        rows = Repository.rows(saved, sheet, ['source_log_evidence_ratio'])
        monkeypatch.setattr(Repository, 'read', lambda *_: saved)
        form, schema = {'assay': rows}, {'properties': {'assay': {'x-source': 'literature_assay_grading_cells'}}}
        assertion = {'id': inputs['assertion_ref'], 'predicate': 'catalyzes'}
        known = {sheet, *(ref for row in rows for value in row['interpretations'].values() for ref in value['support_refs'])}
        call = lambda: native_assay_qualification(store, form, schema, assertion,
            'source_engineering_assay', known, run_id='engineering_control')
        assert call()[0]['assay_type'] == 'activity_rate'
        saved['sheet']['interpretations']['attribution_supported']['status'] = 'unknown'
        rows[:] = Repository.rows(saved, sheet, ['source_log_evidence_ratio'])
        assert call() == []
        saved['sheet']['interpretations']['attribution_supported']['status'] = 'supported'
        rows[:] = Repository.rows(saved, sheet, ['source_log_evidence_ratio'])
        assertion['predicate'] = 'transports'
        assert call() == []
        assertion['predicate'] = 'catalyzes'
        rows[0]['assay_type'] = 'protein_amount'
        assert call() == []
