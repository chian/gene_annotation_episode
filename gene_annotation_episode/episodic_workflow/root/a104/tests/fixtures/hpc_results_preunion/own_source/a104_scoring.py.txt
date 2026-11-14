"""Actual A104 measurements over authenticated native phylogenies.

Input identity, experimental characterization and evolutionary interpretation
remain separate. Native numerical support is never a function probability.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .domain import canonical
from .a104_hpc import require, native_body, request_body
from .phylogeny_formats import parse_newick
from .phylogeny_calculators import compare_unrooted_relationships


VERSION = 'a104_native_evolutionary_measurement_v1'
PROFILE = 'a104_bounded_phylogenetic_progress_v1'


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def analysis_body(store, reference, name, known):
    require(reference in known, 'a104_native_phylogeny_not_received')
    body = native_body(store, reference)
    require(body is not None, 'a104_authentic_native_phylogeny_required')
    results = [row for row in body['result']['analyses'] if row['name'] == name]
    bindings = [row for row in body['bindings'] if row['name'] == name]
    require(len(results) == len(bindings) == 1, 'a104_native_analysis_not_present')
    return body, results[0], bindings[0]


def target_member(binding, target):
    members = [row for row in binding['members'] if any(part.get('target_regions')
        or 'target_regions' not in part and part['subject_ref'] == target for part in row['parts'])]
    require(len(members) == 1, 'a104_unique_original_target_tip_required')
    return members[0]


def target_regions(member, target):
    # Original v1 protein-input commissions used exact local original-input
    # intervals. Later requests also carry explicit lifted feature/product maps.
    return [region for part in member['parts'] for region in
            part.get('target_regions', part['regions'] if part['subject_ref'] == target else [])]


def relationship_inventory(body):
    """Match native split questions by physical members, never split ordinals."""
    grouped = {}
    for result in body['result']['analyses']:
        binding = next(row for row in body['bindings'] if row['name'] == result['name'])
        if binding['purpose'] not in {'family', 'regional', 'sensitivity'}:
            continue
        target = target_member(binding, body['target_ref'])
        def key(member):
            return canonical([{'subject_ref': part['subject_ref'], 'regions': part['regions']}
                              for part in member['parts']])
        panel = sorted(key(member) for member in binding['members'])
        regions = target_regions(target, body['target_ref'])
        for index, split in enumerate(result['tree_summary']['splits']):
            side = split['side'] if target['tip_id'] in split['side'] else split['complement']
            members = [member for member in binding['members'] if member['tip_id'] in side
                       and member['tip_id'] != target['tip_id']]
            identity = digest([body['target_ref'], regions, panel, sorted(key(member) for member in members)])
            row = grouped.setdefault(identity, {'relationship_id': identity, 'target_regions': regions,
                'reference_members': sorted(([{'subject_ref': part['subject_ref'], 'regions': part['regions']}
                             for part in member['parts']] for member in members), key=canonical),
                'occurrences': []})
            population = result['bootstrap_population']['splits'][index]
            row['occurrences'].append({'analysis': result['name'], 'split_index': index,
                'bootstrap_matches': population['matches'], 'bootstrap_denominator': population['denominator']})
    return sorted((row for row in grouped.values() if len({item['analysis'] for item in row['occurrences']}) > 1),
                  key=lambda row: (len(row['reference_members']), row['relationship_id']))


def _base(body, reference, schema, operation, regions):
    return {'schema': schema, 'version': VERSION, 'producer_operation': operation,
        'target_ref': body['target_ref'], 'target_regions': regions, 'native_phylogeny_ref': reference,
        'native_request_ref': body['request_ref'], 'hpc_result_ref': body['hpc_result_ref'],
        'pbs_job_id': body['pbs_job_id'], 'result_sha256': body['result_sha256']}


def reference_distances(result, binding, target):
    """Actual MSA correspondence and native-tree distance for each precise use."""
    import io
    from Bio import Phylo
    from .a104_hpc_worker import read_fasta
    aligned = read_fasta(result['alignment_fasta'])
    tree = Phylo.read(io.StringIO(result['maximum_likelihood_tree']), 'newick')
    query = aligned[target['tip_id']]
    query_length = sum(symbol not in '-.' for symbol in query)
    rows = []
    for member in binding['members']:
        if member['tip_id'] == target['tip_id']:
            continue
        other = aligned[member['tip_id']]
        reference_length = sum(symbol not in '-.' for symbol in other)
        comparable = [(a, b) for a, b in zip(query, other) if a not in '-.' and b not in '-.']
        identical = sum(a == b and a in 'ACDEFGHIKLMNPQRSTVWY' for a, b in comparable)
        rows.append({'tip_id': member['tip_id'], 'reference_ref': member['parts'][0]['subject_ref'],
            'reference_regions': member['parts'][0]['regions'], 'reference_full_length': member['parts'][0]['full_length'],
            'aligned_residue_pairs': len(comparable), 'identical_canonical_pairs': identical,
            'query_compared_length': query_length, 'reference_compared_length': reference_length,
            'query_coverage': len(comparable)/query_length if query_length else 0.,
            'reference_coverage': len(comparable)/reference_length if reference_length else 0.,
            'observed_identity': identical/len(comparable) if comparable else None,
            'identity_extent_factor': identical/max(query_length, reference_length) if query_length and reference_length else 0.,
            'patristic_distance': tree.distance(target['tip_id'], member['tip_id']),
            'patristic_unit': 'expected_substitutions_per_site',
            'basis': 'exact_native_MUSCLE_rows_and_IQ_TREE_branch_lengths'})
    return rows


def placement(store, reference, analysis_name, split_index, known):
    body, result, binding = analysis_body(store, reference, analysis_name, known)
    require(binding['purpose'] in {'family', 'regional', 'sensitivity'}, 'a104_target_family_tree_required')
    member = target_member(binding, body['target_ref'])
    require(type(split_index) is int and 0 <= split_index < len(result['tree_summary']['splits']),
            'a104_actual_native_split_required')
    native_split = deepcopy(result['tree_summary']['splits'][split_index])
    target_tip = member['tip_id']
    side = native_split['side'] if target_tip in native_split['side'] else native_split['complement']
    require(target_tip in side and len(side) >= 2, 'a104_target_not_in_measured_relationship')
    bootstrap = result['bootstrap_population']['splits'][split_index]
    require(bootstrap['side'] == native_split['side'] and bootstrap['denominator'] > 0
            and 0 <= bootstrap['matches'] <= bootstrap['denominator'], 'a104_native_split_bootstrap_association_conflict')
    value = bootstrap['matches']/bootstrap['denominator']
    regions = target_regions(member, body['target_ref'])
    clade = [row for row in binding['members'] if row['tip_id'] in side]
    original = request_body(store, body['request_ref'])['native_request']
    configuration = {key: original[key] for key in ('threads', 'seed', 'model', 'bootstrap_replicates')}
    analysis_parameters = next(row for row in original['analyses'] if row['name'] == analysis_name)
    configuration.update({key: analysis_parameters[key] for key in ('model', 'seed') if key in analysis_parameters})
    def inference_parts(row):
        return [{key: part[key] for key in ('subject_ref', 'regions', 'full_length',
                    'target_regions', 'original_sequence_sha256') if key in part} for part in row['parts']]
    configuration['members'] = sorted([
        {'parts': inference_parts(row), 'sequence_sha256': row['sequence_sha256']} for row in binding['members']],
        key=canonical)
    configuration_digest = digest(configuration)
    panel = sorted([part for row in binding['members'] for part in inference_parts(row)], key=canonical)
    return {**_base(body, reference, 'a104_placement_v1', 'phylogeny.measure_placement', regions),
        'analysis': analysis_name, 'target_tip': target_tip, 'split_index': split_index,
        'target_side_tip_ids': sorted(side), 'clade_members': deepcopy(clade), 'native_split': native_split,
        'reference_panel_members': deepcopy(binding['members']),
        'support_method': result['support_method'], 'support_scale': result['support_scale'],
        'bootstrap_population': deepcopy(bootstrap), 'raw_value': value,
        'population': {'usable_replicates': result['bootstrap_population']['usable_replicates'],
                       'excluded_replicates': result['bootstrap_population']['excluded_replicates']},
        'native_correspondence': deepcopy(result['correspondence']),
        'reference_correspondences': reference_distances(result, binding, member),
        'analysis_configuration_digest': configuration_digest,
        'function_status': 'unassessed', 'rooting_status': 'unestablished',
        'variant_group': digest([body['target_ref'], regions, panel]),
        'variant': configuration_digest,
        'interpretation': 'observed_native_target_relationship; no_function_transfer_or_biological_root'}


def _tree(store, source, result):
    raw = result['maximum_likelihood_tree'].encode()
    artifact = store.artifact(raw, 'text/plain')
    parsed = parse_newick(raw, artifact={'raw_artifact_ref': artifact, 'source_ref': source,
                                        'sha256': hashlib.sha256(raw).hexdigest()}, dialect='newick')
    require(parsed['status'] == 'ok' and parsed['value']['completeness'] == 'complete'
            and len(parsed['value']['trees']) == 1, 'a104_complete_native_newick_required')
    return parsed['value']['trees'][0]


def history_comparison(store, reference, family_name, organismal_name, tip_ids, known):
    body, family, genes = analysis_body(store, reference, family_name, known)
    _, organismal, organisms = analysis_body(store, reference, organismal_name, known)
    require(genes['purpose'] in {'family', 'regional', 'sensitivity'}
            and organisms['purpose'] == 'organismal_reference' and organisms.get('organismal_basis'),
            'a104_actual_independent_organismal_reference_required')
    gene_members = {row['tip_id']: row for row in genes['members']}
    require(type(tip_ids) is list and len(tip_ids) == len(set(tip_ids)) and len(tip_ids) >= 4
            and set(tip_ids) <= set(gene_members), 'a104_declared_shared_taxon_scope_required')
    selected = [gene_members[label] for label in tip_ids]
    taxa = [row['taxon_id'] for row in selected]
    require(all(taxon is not None for taxon in taxa), 'a104_exact_tip_taxon_links_required')
    require(len(taxa) == len(set(taxa)), 'a104_paralog_copies_require_explicit_separate_comparison')
    organism_members = {row['taxon_id']: row for row in organisms['members']}
    require(len(organism_members) == len(organisms['members']) and None not in organism_members,
            'a104_organismal_reference_taxon_copies_ambiguous')
    require(set(taxa) <= set(organism_members), 'a104_organismal_taxon_mapping_missing')
    gene_tree, organism_tree = _tree(store, reference, family), _tree(store, reference, organismal)
    gene_nodes = {row['decoded_label']: row['node_index'] for row in gene_tree['nodes'] if not row['child_indices']}
    organism_nodes = {row['decoded_label']: row['node_index'] for row in organism_tree['nodes'] if not row['child_indices']}
    source = store.get(reference)
    payload = store.get_artifact(source['artifact_ref'])
    evidence = [{'content': {'source_ref': reference, 'artifact_field': 'artifact_ref',
        'artifact_ref': source['artifact_ref'], 'sha256': hashlib.sha256(payload).hexdigest(),
        'byte_count': len(payload)}, 'pointer': '/bindings'}]
    pairs = [{'gene_tree_id': gene_tree['tree_id'], 'gene_node_index': gene_nodes[row['tip_id']],
              'organismal_tree_id': organism_tree['tree_id'],
              'organismal_node_index': organism_nodes[organism_members[row['taxon_id']]['tip_id']],
              'subject': {'kind': 'genome', 'id': 'ncbi_taxon:'+str(row['taxon_id']),
                          'source_record_id': row['taxon_evidence'][0]['source_ref']}, 'evidence': evidence}
             for row in selected]
    # The pure existing calculator owns restricted split identity and RF
    # arithmetic. It does not diagnose transfer, duplication, loss or function.
    comparison = compare_unrooted_relationships(gene_tree, comparison_id='comparison_'+digest([reference, tip_ids]),
        organismal_tree=organism_tree, injective_tip_join=tuple(pairs))
    target = target_member(genes, body['target_ref'])
    regions = target_regions(target, body['target_ref'])
    require(target['tip_id'] in tip_ids, 'a104_history_must_include_actual_target')
    total = comparison['gene_splits']['value']+comparison['organismal_splits']['value']
    # A measured conflict is informative. Progress records an actually
    # evaluable comparison; agreement/discordance remain explicit raw metrics.
    def reliability(analysis, retained_tips):
        fractions = []
        for branch in analysis['bootstrap_population']['splits']:
            first = set(branch['side']) & retained_tips
            if len(first) >= 2 and len(retained_tips-first) >= 2:
                fractions.append(branch['matches']/branch['denominator'] if branch['denominator'] else 0.)
        return sum(fractions)/len(fractions) if fractions else None
    gene_reliability = reliability(family, set(tip_ids))
    organism_reliability = reliability(organismal, {organism_members[taxon]['tip_id'] for taxon in taxa})
    value = min(gene_reliability, organism_reliability) if total and gene_reliability is not None \
        and organism_reliability is not None else None
    return {**_base(body, reference, 'a104_history_comparison_v1', 'phylogeny.compare_histories', regions),
        'family_analysis': family_name, 'organismal_analysis': organismal_name,
        'selected_tip_ids': list(tip_ids), 'taxon_join': [{'gene_tip': row['tip_id'], 'taxon_id': row['taxon_id'],
            'organismal_tip': organism_members[row['taxon_id']]['tip_id']} for row in selected],
        'organismal_basis': deepcopy(organisms['organismal_basis']), 'comparison': comparison,
        'native_relationship_reliability': {'family': gene_reliability, 'organismal_reference': organism_reliability},
        'raw_value': value, 'historical_cause': 'unresolved',
        'limitations': ['paralog_subset_declared', 'restricted_taxon_scope', 'rooting_unestablished',
                       'discordance_does_not_establish_horizontal_transfer'],
        'variant_group': digest([body['target_ref'], family_name, organismal_name, sorted(tip_ids)]),
        'variant': body['result_sha256'],
        'interpretation': 'actual_matched_tree_comparison; agreement_and_conflict_separate_from_progress'}
