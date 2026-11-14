"""Pure provider assembly from supplied parsed artifacts and explicit joins.

All native bytes remain outside this object in their retained artifacts. This
module does not parse/acquire bytes, execute tools, or choose scientific work.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math
import re
from typing import Literal

from . import phylogeny_calculation_contracts as c
from . import bvbrc_phylogeny_common_contracts as v


def input_member_subject_id(input_binding_id: str, member_id: str) -> str:
    """Canonical UTF-8 percent encoding of the exact original binding/member."""
    return v._member_id(input_binding_id, member_id)


def _diagnostic(code, *, path='', source_refs=(), severity='qualification'):
    return {'code': 'bvbrc_phylogeny_' + code, 'phase': 'association', 'path': path,
            'severity': severity, 'evidence_refs': list(dict.fromkeys(source_refs))}


def _requirement(scope, reason, role, kind='scientific_metadata', sources=()):
    return {'requirement_id': scope + '/' + reason, 'kind': kind, 'role': role,
            'source_refs': list(dict.fromkeys(sources)), 'reason_code': reason}


def _read_parameters(value, provider):
    if provider == 'gene_tree':
        v._shape(value, ('source_dialect', 'raw_tree_required_for_branch_facts'), 'read_parameters_invalid')
        v._require(value['source_dialect'] == 'retained_bvbrc_gene_tree' and type(value['raw_tree_required_for_branch_facts']) is bool, 'read_parameters_invalid')
    else:
        v._shape(value, ('source_dialect', 'membership_dialect', 'family_stats_dialect'), 'read_parameters_invalid')
        v._require(value['source_dialect'] == 'retained_codon_trees' and value['membership_dialect'] in ('pgfams_legacy', 'homologs_current') and value['family_stats_dialect'] in (None, 'current_missing_header_tab'), 'read_parameters_invalid')


def _model(row):
    v._shape(row, ('native_run_label', 'partition_index', 'partition_name', 'model_token', 'datatype', 'branch_optimization', 'parameters', 'location'), 'native_model_shape_invalid')
    for key in ('native_run_label', 'partition_name', 'model_token'):
        c.text(row[key], nullable=True)
    c.integer(row['partition_index'], nullable=True)
    v._require(row['datatype'] in ('dna', 'rna', 'protein', 'mixed', 'unknown') and row['branch_optimization'] in ('joint', 'separate', 'unknown'), 'native_model_invalid')
    c.location(row['location']); c.sequence(row['parameters'], stored=True)
    for field in row['parameters']:
        v._shape(field, ('name', 'value', 'native_location'), 'model_parameter_shape_invalid')
        c.text(field['name']); c.number(field['value']); c.location(field['native_location'])


def _native_reader_value(reader, value, artifact):
    """Validate all input-only reader records without re-running a reader."""
    if reader == 'raxml_run_log':
        v._shape(value, ('artifact', 'engine', 'commands', 'observations', 'models', 'completeness'), 'raxml_value_shape_invalid')
        v._require(value['artifact'] == artifact and value['completeness'] in c.COMPLETENESS, 'raxml_artifact_conflict')
        commands = v._unique(value['commands'], 'command_id')
        for row in commands.values():
            v._command(row)
        v._engine(value['engine'], commands)
        c.sequence(value['models'], stored=True)
        for row in value['models']:
            _model(row)
    else:
        extra = {'codon_membership': ('rows', 'missing_codon_family_ids'),
                 'codon_family_statistics': ('observations', 'rows', 'header_defect'),
                 'codon_genome_counts': ('observations', 'rows'),
                 'codon_analysis_statistics': ('observations', 'commands', 'uninterpreted_source_row_indices')}[reader]
        v._shape(value, {'table'} | set(extra), 'native_reader_value_shape_invalid'); v._table(value['table'])
        v._require(value['table']['artifact'] == artifact, 'native_reader_artifact_conflict')
        table = value['table']; row_count = len(table['rows'])
        if reader == 'codon_membership':
            c.sequence(value['rows'], stored=True); c.sequence(value['missing_codon_family_ids'], stored=True)
            for family_id in value['missing_codon_family_ids']:
                c.text(family_id)
            for row in value['rows']:
                v._shape(row, ('family_id', 'representation', 'included_feature_ids', 'deleted_feature_ids', 'missing_codon_feature_ids', 'source_row_index'), 'membership_row_shape_invalid')
                c.text(row['family_id']); v._require(row['representation'] in ('protein', 'coding_nucleotide'), 'representation_invalid')
                for key in ('included_feature_ids', 'deleted_feature_ids', 'missing_codon_feature_ids'):
                    # Native duplicates are retained by the reader with diagnostics.
                    c.sequence(row[key], stored=True)
                    for feature in row[key]:
                        c.text(feature)
                c.integer(row['source_row_index']); v._require(row['source_row_index'] < row_count and table['rows'][row['source_row_index']]['family_id'] == row['family_id'], 'membership_source_row_conflict')
        elif reader == 'codon_family_statistics':
            v._require(value['header_defect'] == 'missing_tab_before_used_in_tree', 'family_header_defect_invalid')
            c.sequence(value['rows'], stored=True)
            for row in value['rows']:
                v._shape(row, ('family_id', 'observation_ids', 'used_in_tree', 'bad_sequence_values', 'disqualification', 'source_row_indices'), 'family_statistics_row_shape_invalid')
                c.text(row['family_id']); c.strings(row['observation_ids']); c.unique_indices(row['source_row_indices'])
                v._require(row['used_in_tree'] is None or type(row['used_in_tree']) is bool, 'family_inclusion_invalid')
                v._require(row['disqualification'] in (None, 'bad seqs', 'low alignment score'), 'family_disqualification_invalid')
                v._require(all(i < row_count and table['rows'][i]['family_id'] == row['family_id'] for i in row['source_row_indices']), 'family_statistics_source_row_conflict')
                c.sequence(row['bad_sequence_values'], stored=True)
                for item in row['bad_sequence_values']:
                    v._shape(item, ('genome_id', 'value'), 'bad_sequence_shape_invalid'); c.text(item['genome_id']); c.number(item['value'])
        elif reader == 'codon_genome_counts':
            c.sequence(value['rows'], stored=True)
            for row in value['rows']:
                v._shape(row, ('genome_id', 'all_families_observation_id', 'single_copy_observation_id', 'filtered_single_copy_observation_id'), 'genome_counts_row_shape_invalid')
                for text in row.values():
                    c.text(text)
        else:
            c.unique_indices(value['uninterpreted_source_row_indices']); v._require(all(i < row_count for i in value['uninterpreted_source_row_indices']), 'analysis_row_index_invalid')
            for row in v._unique(value['commands'], 'command_id').values():
                v._command(row)
    if 'observations' in value:
        observations = v._unique(value['observations'], 'observation_id')
        for obs in observations.values():
            c.native_observation(obs)
            v._require(obs['location'] is not None and obs['location']['artifact'] == artifact, 'reader_observation_artifact_conflict')
        if reader == 'codon_family_statistics':
            for row in value['rows']:
                v._require(all(oid in observations and observations[oid]['subject_id'] == row['family_id'] for oid in row['observation_ids']), 'family_observation_conflict')
        if reader == 'codon_genome_counts':
            for row in value['rows']:
                for key, field in (('all_families_observation_id', 'genome_native_all_families'), ('single_copy_observation_id', 'genome_native_single_copy_families'), ('filtered_single_copy_observation_id', 'genome_native_filtered_single_copy_families')):
                    oid = row[key]
                    v._require(oid in observations and observations[oid]['field'] == field and observations[oid]['subject_id'] == row['genome_id'], 'genome_observation_conflict')


def _envelope(documents, provider):
    extras = {'raxml_runs'} if provider == 'gene_tree' else {'raxml_runs', 'membership', 'family_statistics', 'genome_counts', 'analysis_statistics'}
    v._shape(documents, {'parsed', 'reads'} | extras, 'extraction_documents_shape_invalid')
    v._json(documents)
    parsed = deepcopy(documents['parsed']); v._shape(parsed, ('store', 'analyses'), 'documents_shape_invalid')
    v._shape(parsed['store'], ('alignments', 'tree_documents', 'partitions', 'phyloxml', 'source_records', 'native_tables'), 'store_shape_invalid')
    for key, identity in (('alignments', 'alignment_id'), ('tree_documents', 'document_id'), ('partitions', 'document_id'), ('phyloxml', 'document_id'), ('source_records', 'source_record_id'), ('native_tables', 'table_id')):
        parsed['store'][key] = list(v._unique(parsed['store'][key], identity, equal=True).values())
    alignments, trees, docs, tables, records = v._store(parsed['store'])
    reads = list(v._unique(documents['reads'], 'read_id', equal=True).values())
    declared = {'raxml_run_log': 'raxml_runs', 'codon_membership': 'membership', 'codon_family_statistics': 'family_statistics', 'codon_genome_counts': 'genome_counts', 'codon_analysis_statistics': 'analysis_statistics'}
    native = {key: [] for key in extras}; materialized = set(); outcomes = []; artifacts = {}; observations = {}; qualifications = []
    for index, read in enumerate(reads):
        v._shape(read, ('read_id', 'artifact', 'reader', 'result'), 'reader_input_shape_invalid'); v._artifact(read['artifact']); v._reader_spec(read['reader'])
        artifact = read['artifact']; raw = artifact['raw_artifact_ref']
        v._require(raw not in artifacts or artifacts[raw] == artifact, 'read_artifact_identity_conflict'); artifacts[raw] = artifact
        result = read['result']; v._shape(result, ('status', 'value', 'diagnostics'), 'reader_result_shape_invalid')
        v._require(result['status'] in ('ok', 'partial', 'invalid'), 'reader_status_invalid'); c.sequence(result['diagnostics'], stored=True)
        v._require(result['status'] != 'ok' or result['value'] is not None, 'ok_reader_value_missing')
        outcome = {'read_id': read['read_id'], 'artifact': deepcopy(artifact), 'reader': deepcopy(read['reader']), 'status': result['status'], 'value_present': result['value'] is not None, 'document_ids': [], 'observation_ids': [], 'diagnostics': deepcopy(result['diagnostics'])}
        for j, diag in enumerate(result['diagnostics']):
            v._diag(diag)
            outward = deepcopy(diag); outward['path'] = f'/read_outcomes/{index}/diagnostics/{j}'; outward['evidence_refs'] = list(dict.fromkeys(diag['evidence_refs'] + [artifact['source_ref']]))
            qualifications.append(outward)
        value = result['value']; reader = read['reader']['reader']
        if value is not None:
            if reader in declared:
                v._require(declared[reader] in extras, 'reader_provider_conflict'); _native_reader_value(reader, value, artifact)
                native[declared[reader]].append(value)
                if reader != 'raxml_run_log':
                    table = value['table']; did = table['table_id']; v._require(tables.get(did) == table, 'reader_table_copy_conflict'); outcome['document_ids'].append(did); materialized.add(did)
                for obs in value.get('observations', []):
                    oid = obs['observation_id']; v._require(oid not in observations or observations[oid] == obs, 'native_observation_conflict'); observations[oid] = obs; outcome['observation_ids'].append(oid)
            else:
                did = value.get('alignment_id', value.get('document_id')) if type(value) is dict else None
                stored = alignments.get(did, docs.get(did)); v._require(stored == value and stored is not None and stored['artifact'] == artifact, 'reader_document_copy_conflict')
                expected_format = reader
                v._require(value['format'] == expected_format, 'reader_format_conflict')
                if reader == 'newick':
                    v._require(value['dialect'] == read['reader']['dialect'] and (read['reader']['allow_multiple'] or len(value['trees']) <= 1), 'reader_declaration_conflict')
                if reader == 'aligned_fasta':
                    v._require(value['encoding'] == read['reader']['encoding'] and value['id_rule'] == read['reader']['id_rule'], 'reader_declaration_conflict')
                if reader == 'relaxed_phylip':
                    v._require(value['layout'] == read['reader']['layout'], 'reader_declaration_conflict')
                if reader == 'raxml_partitions':
                    v._require(value['alignment_column_count'] == read['reader']['alignment_column_count'], 'reader_declaration_conflict')
                outcome['document_ids'].append(did); materialized.add(did)
        outcomes.append(outcome)
    for key in extras:
        c.sequence(documents[key], stored=True)
        # Equal repeated read IDs may share one representation. Unequal duplicate
        # results may not be hidden by a selected first/last record.
        supplied = []
        for item in documents[key]:
            if item not in supplied:
                supplied.append(item)
        expected = []
        for item in native[key]:
            if item not in expected:
                expected.append(item)
        v._require(supplied == expected, 'typed_reader_array_conflict')
    v._require(materialized == set(alignments) | set(docs) | set(tables), 'parsed_reader_outcome_missing')
    for record in records.values():
        if record['artifact'] is not None:
            artifact = record['artifact']; raw = artifact['raw_artifact_ref']
            v._require(raw not in artifacts or artifacts[raw] == artifact, 'source_artifact_conflict'); artifacts[raw] = artifact
    return parsed, reads, outcomes, native, artifacts, observations, qualifications


def _merge_run(supplied, native, qualifications):
    run = deepcopy(supplied)
    # Requested/observed conflicts are completed below, never overwritten.
    v._shape(run, ('original_task_id', 'source_revision', 'settings', 'commands', 'engines', 'conflicts', 'completeness'), 'run_shape_invalid')
    for key in ('settings', 'commands', 'engines', 'conflicts'):
        c.sequence(run[key], stored=True)
    commands = v._unique(run['commands'], 'command_id')
    for source in native['raxml_runs'] + native.get('analysis_statistics', []):
        for row in source['commands']:
            cid = row['command_id']; v._require(cid not in commands or commands[cid] == row, 'command_identity_conflict')
            if cid not in commands:
                commands[cid] = deepcopy(row); run['commands'].append(deepcopy(row))
        if 'engine' in source and source['engine'] not in run['engines']:
            run['engines'].append(deepcopy(source['engine']))
    # Derive settings only from observed command tokens. Source defaults and
    # submitted requests never become observed settings.
    for command in run['commands']:
        v._command(command)
        if command['origin'] != 'observed' or not command['argv'] or not (command['location'] or command['evidence']):
            continue
        argv = command['argv']; engine = [e for e in run['engines'] if command['command_id'] in e['command_ids']]
        if len(engine) != 1 or engine[0]['name'] != 'raxml' or engine[0]['version'] is None:
            continue
        facts = [('recipe', 'raxml')]
        for opt, name in (('-m', 'substitution_model'), ('-N', 'bootstrap_replicates'), ('-#', 'bootstrap_replicates'), ('-T', 'threads')):
            values = [argv[i + 1] for i, token in enumerate(argv[:-1]) if token == opt]
            if len(values) != 1:
                continue
            value = values[0]
            if name != 'substitution_model':
                if not value.isdecimal():
                    continue
                value = int(value)
            facts.append((name, value))
        for name, item in facts:
            setting = {'name': name, 'value': item, 'origin': 'observed', 'evidence': deepcopy(command['evidence']), 'location': deepcopy(command['location'])}
            if setting not in run['settings']:
                run['settings'].append(setting)
    for i, requested in enumerate(run['settings']):
        if requested['origin'] != 'requested':
            continue
        for j, observed in enumerate(run['settings']):
            if observed['origin'] == 'observed' and requested['name'] == observed['name'] and requested['value'] != observed['value']:
                conflict = {'setting_name': requested['name'], 'requested_index': i, 'observed_index': j, 'diagnostic_code': 'bvbrc_phylogeny_requested_observed_setting_conflict'}
                matching = [r for r in run['conflicts'] if r.get('requested_index') == i and r.get('observed_index') == j]
                if not matching:
                    run['conflicts'].append(conflict)
                qualifications.append(_diagnostic('requested_observed_setting_conflict', path=f'/observed_run/conflicts/{len(run["conflicts"]) - 1}'))
    v._run(run)
    observed = defaultdict(set)
    for row in run['settings']:
        if row['origin'] == 'observed':
            observed[row['name']].add((type(row['value']).__name__, row['value']))
    for key, values in observed.items():
        if len(values) > 1:
            qualifications.append(_diagnostic('observed_settings_conflict', path='/observed_run/settings', severity='error'))
    return run


def _native_populations(observations):
    grouped = defaultdict(list)
    for observation in observations.values():
        grouped[observation['population_id']].append(observation)
    result = []
    for pid, rows in grouped.items():
        fields = {r['field'] for r in rows}
        kind = 'native_pretrim_alignment' if any(f.startswith('family_native_') for f in fields) else 'native_log_alignment' if any(r['method'].startswith('raxml_8_') for r in rows) else 'native_reported_population'
        def count(field):
            values = {r['value'] for r in rows if r['field'] == field and r['state'] == 'available'}
            return next(iter(values)) if len(values) == 1 else None
        result.append({'population_id': pid, 'kind': kind, 'observed_member_count': count('family_native_sequences'), 'observed_site_count': count('family_native_length'), 'members': [], 'membership_completeness': 'unknown',
            'evidence': [e for row in rows for e in row['evidence']], 'locations': [deepcopy(row['location']) for row in rows if row['location'] is not None]})
    return result


def _finite_token(token):
    if type(token) is not str or re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', token.strip()) is None:
        return None
    number = float(token)
    if not math.isfinite(number) or number == 0 and re.search(r'[1-9]', token.strip().lower().split('e')[0]):
        return None
    return number


def _tree_semantics(tree, analysis, reads, run):
    """Resolve only a selected tree with explicit run/analysis evidence.

    Generic XML confidence types alone have no named support semantics. The
    native engine readers remain responsible for declaring valid command facts.
    """
    unknown = ('native_unknown', 'native_unknown', 'native_unknown', None)
    if not analysis['output_role_evidence']:
        return unknown
    tree_ids = {analysis[k] for k in analysis if k.endswith('tree_id') and analysis[k] is not None}
    if tree['tree_id'] not in tree_ids:
        return unknown
    linked = []
    for read in reads:
        if read['reader']['reader'] != 'raxml_run_log' or read['result']['status'] == 'invalid' or read['result']['value'] is None:
            continue
        source = read['result']['value']
        if set(analysis['native_engine_observation_ids']) & {o['observation_id'] for o in source['observations']}:
            linked.append(source)
    if len(linked) != 1:
        return unknown
    source = linked[0]; engine = source['engine']
    if engine['name'] != 'raxml' or engine['version'] is None or engine['version_location'] is None:
        return unknown
    commands = [r for r in source['commands'] if r['origin'] == 'observed' and r['role'] in ('inference', 'support_mapping') and r['argv'] is not None and (r['location'] or r['evidence'])]
    candidates = []
    for command in commands:
        argv = command['argv']; modes = [argv[i + 1] for i, token in enumerate(argv[:-1]) if token == '-f']
        if len(modes) != 1:
            continue
        mode = modes[0]
        method = 'rapid_bootstrap' if mode == 'a' else 'rell_bootstrap' if mode == 'D' else 'native_unknown'
        models = source['models']; datatypes = {r['datatype'] for r in models if r['datatype'] != 'unknown'}
        optimization = {r['branch_optimization'] for r in models}
        unit = 'joint_mixed_partition_model_site' if datatypes >= {'dna', 'protein'} and optimization == {'joint'} else 'expected_substitutions_per_model_site' if len(datatypes) == 1 and optimization <= {'joint', 'separate'} else 'native_unknown'
        # Missing partition records can still have an observed homogeneous -m.
        model_tokens = [argv[i + 1] for i, token in enumerate(argv[:-1]) if token == '-m']
        if not models and len(model_tokens) == 1 and '-q' not in argv and (model_tokens[0].startswith('GTR') or model_tokens[0].startswith('PROT')):
            unit = 'expected_substitutions_per_model_site'
        candidates.append((unit, method, 'percent' if method != 'native_unknown' else 'native_unknown', command['command_id']))
    return candidates[0] if len(candidates) == 1 else unknown


def _branches(parsed, analysis, reads, run, populations, observations, qualifications, requirements, provider, parameters):
    tree_documents = parsed['store']['tree_documents']; xml_documents = parsed['store']['phyloxml']
    for document in tree_documents + xml_documents:
        for entry in document['trees']:
            tree = entry if document['format'] == 'newick' else entry['tree']; tid = tree['tree_id']
            population = v._whole_id(analysis['analysis_id'], 'tree', tid)
            unit, method, scale, command_id = _tree_semantics(tree, analysis, reads, run)
            if tree['source_format'] == 'phyloxml':
                # XML conversions may insert zeros and drop native zero support.
                qualifications.append(_diagnostic('xml_converter_zero_and_support_loss', path='/documents/store/phyloxml', source_refs=[document['artifact']['source_ref']]))
                if provider == 'gene_tree' and parameters['raw_tree_required_for_branch_facts'] and analysis['raw_tree_id'] is None:
                    requirements.append(_requirement(c.scope(tid), 'raw_tree_required_for_branch_facts', 'native_raw_tree', 'output_bytes', [document['artifact']['source_ref']]))
                if provider == 'gene_tree' and analysis['raw_tree_id'] is None:
                    qualifications.append(_diagnostic('xml_raw_tree_unavailable', path='/documents/store/phyloxml', source_refs=[document['artifact']['source_ref']]))
            for node in tree['nodes']:
                index = node['node_index']; subject = tid + '/node/' + str(index)
                token, number = node['branch_length_token'], node['branch_length']
                if token is not None:
                    oid = subject + '/branch_length'
                    observations[oid] = {'observation_id': oid, 'field': 'branch_length', 'value': number, 'raw_token': token,
                        'state': 'available' if number is not None else 'failed', 'unit': unit, 'population_id': population,
                        'subject_id': subject, 'method': 'native_branch_length', 'location': deepcopy(node['source_location']), 'evidence': [], 'uncertainty': None, 'requirement_ids': []}
                    if number is not None and number < 0:
                        qualifications.append(_diagnostic('negative_branch_length', path=f'/documents/store/{"phyloxml" if tree["source_format"] == "phyloxml" else "tree_documents"}', source_refs=[document['artifact']['source_ref']]))
                supports = []
                if tree['source_format'] == 'newick':
                    # Numeric internal labels are native values; absent method
                    # evidence leaves their scale/method unknown.
                    if node['child_indices'] and node['decoded_label'] is not None and (_finite_token(node['decoded_label']) is not None or method != 'native_unknown'):
                        supports.append(('internal_label', 0, node['label_token'], _finite_token(node['decoded_label']), node['source_location']))
                    if document['dialect'] == 'raxml_branch_labels':
                        for j, comment in enumerate(node['comments']):
                            if comment['position'] == 'after_length':
                                supports.append(('branch_comment', j, comment['text'], _finite_token(comment['text']), comment['location']))
                else:
                    for ann in entry['annotations']:
                        if ann['node_index'] == index:
                            for j, confidence in enumerate(ann['confidences']):
                                supports.append(('phyloxml_confidence', j, confidence['raw_token'], confidence['value'], confidence['source_location']))
                for source_kind, j, support_token, support_value, location in supports:
                    # The converter's generic support tag does not attest which
                    # analysis populated it, even when some raw tree is present.
                    smethod, sscale, scmd = (method, scale, command_id) if source_kind != 'phyloxml_confidence' else ('native_unknown', 'native_unknown', None)
                    oid = subject + '/support/' + source_kind + '/' + str(j)
                    sunit = {'percent': 'percent', 'fraction': 'fraction', 'statistic': 'native_statistic', 'native_unknown': 'native_unknown'}[sscale]
                    observations[oid] = {'observation_id': oid, 'field': 'branch_support_native', 'value': support_value, 'raw_token': support_token,
                        'state': 'available' if support_value is not None else 'failed', 'unit': sunit, 'population_id': population,
                        'subject_id': subject, 'method': smethod, 'location': deepcopy(location), 'evidence': [], 'uncertainty': None, 'requirement_ids': []}
                    yield {'tree_id': tid, 'node_index': index, 'native_observation_id': oid, 'source_kind': source_kind, 'method': smethod, 'scale': sscale, 'command_id': scmd, 'bootstrap_population_id': None, 'evidence': []}


def _dependence(parsed, joins, analysis, inputs):
    groups = []; aid = analysis.get('aligned_document_id', analysis.get('final_alignment_id'))
    alignments = {a['alignment_id']: a for a in parsed['store']['alignments']}
    if aid is not None:
        alignment = alignments[aid]; repeated = defaultdict(list)
        if alignment['completeness'] == 'complete':
            for row in alignment['rows']:
                repeated[row['sequence']].append(aid + '/row/' + str(row['row_index']))
        for index, members in enumerate(repeated.values()):
            if len(members) > 1:
                groups.append({'group_id': aid + '/identical/' + str(index), 'kind': 'identical_final_sequence', 'subject_ids': members, 'evidence': []})
    originals = defaultdict(list)
    member_facts = {(binding['binding_id'], member['member_id']): member for binding in inputs for member in binding['members']}
    aliases = {}
    for member, fact in member_facts.items():
        if fact['evidence'] is not None:
            source = fact['evidence']; content = source['content']
            key = (content['source_ref'], content['artifact_ref'], content['sha256'], source['pointer'], fact['member_pointer'])
            if key in aliases:
                previous = member_facts[aliases[key]]
                for field in ('length', 'molecule', 'sequence_sha256'):
                    v._require(fact[field] is None or previous[field] is None or fact[field] == previous[field], 'shared_original_member_facts_conflict')
            else:
                aliases[key] = member
    for join in joins['input_rows']:
        key = (join['input_binding_id'], join['member_id']); row_id = join['alignment_id'] + '/row/' + str(join['row_index'])
        fact = member_facts.get(key)
        if fact is not None and fact['evidence'] is not None:
            source = fact['evidence']; content = source['content']
            key = aliases[(content['source_ref'], content['artifact_ref'], content['sha256'], source['pointer'], fact['member_pointer'])]
        if row_id not in originals[key]:
            originals[key].append(row_id)
    for key, row_ids in originals.items():
        if len(row_ids) > 1:
            groups.append({'group_id': input_member_subject_id(*key) + '/shared_original', 'kind': 'shared_original_member', 'subject_ids': row_ids, 'evidence': [e for r in joins['input_rows'] if (r['input_binding_id'], r['member_id']) == key for e in r['evidence']]})
    derivatives = defaultdict(list)
    for join in joins['display_tips']:
        derivatives[(join['raw_tree_id'], join['display_tree_id'])].extend(join['evidence'])
    for index, ((raw, display), evidence) in enumerate(derivatives.items()):
        if raw != display:
            groups.append({'group_id': c.scope(analysis['analysis_id'], 'derived_tree', str(index)), 'kind': 'derived_tree', 'subject_ids': [raw, display], 'evidence': evidence})
    by_source = defaultdict(list)
    for record in parsed['store']['source_records']:
        if record['artifact'] is not None:
            artifact = record['artifact']
            source = (artifact['source_ref'], artifact['raw_artifact_ref'], artifact['sha256'], record['pointer'])
            by_source[source].append(record['source_record_id'])
    for index, source_ids in enumerate(by_source.values()):
        if len(source_ids) > 1:
            groups.append({'group_id': c.scope(analysis['analysis_id'], 'same_source_record', str(index)), 'kind': 'same_source_record', 'subject_ids': source_ids, 'evidence': []})
    return groups


def extract_common_fields(*, provider: Literal['gene_tree', 'codon_tree'], documents: dict,
                          inputs: tuple[dict, ...], observed_run: dict, joins: dict,
                          assembly: dict, parameters: dict) -> dict:
    """Build the exact common fields, retaining every supplied reader outcome.

    Structural conflicts return invalid without an invented sheet. Independent
    valid values remain in a partial sheet when other reader results failed.
    """
    try:
        v._require(provider in ('gene_tree', 'codon_tree'), 'provider_invalid'); _read_parameters(parameters, provider)
        v._require(type(inputs) in (tuple, list), 'inputs_array_invalid')
        parsed, reads, outcomes, native, artifacts, observations, qualifications = _envelope(documents, provider)
        alignments, trees, docs, tables, records = v._store(parsed['store'])
        analysis = v._analysis(parsed, provider, alignments, trees, docs, tables)
        populations = deepcopy(assembly['caller_populations'])
        v._shape(populations, v.POPULATION_KEYS, 'populations_shape_invalid')
        requirements = []; run = _merge_run(observed_run, native, qualifications)
        for kind, rows in populations.items():
            c.sequence(rows, stored=True)
            for row in rows:
                v._require(type(row) is dict and 'population_id' in row and not (row['population_id'].startswith('analysis/') and row['population_id'].endswith('/whole')), 'reserved_population_identity')
        for alignment in alignments.values():
            columns = alignment['observed_column_count']
            if columns is None:
                columns = alignment['declared_column_count']
            if columns is None:
                columns = max((len(r['sequence']) for r in alignment['rows']), default=0)
            populations['alignments'].append({'population_id': v._whole_id(analysis['analysis_id'], 'alignment', alignment['alignment_id']), 'alignment_id': alignment['alignment_id'], 'row_indices': [r['row_index'] for r in alignment['rows']], 'columns_0based': list(range(columns)), 'completeness': alignment['completeness'], 'evidence': []})
        for tree in trees.values():
            populations['leaves'].append({'population_id': v._whole_id(analysis['analysis_id'], 'tree', tree['tree_id']), 'tree_id': tree['tree_id'], 'node_indices': [n['node_index'] for n in tree['nodes'] if not n['child_indices']], 'completeness': 'complete', 'evidence': []})
        v._require(not populations['native'], 'caller_native_population_forbidden')
        populations['native'] = _native_populations(observations)
        support = list(_branches(parsed, analysis, reads, run, populations, observations, qualifications, requirements, provider, parameters))
        primary_alignment = analysis.get('aligned_document_id', analysis.get('final_alignment_id'))
        if primary_alignment is None:
            requirements.append(_requirement(c.scope(analysis['analysis_id']), 'alignment_bytes_required', 'alignment', 'output_bytes'))
        common = {'inputs': deepcopy(list(inputs)), 'artifact_refs': deepcopy(list(artifacts.values())), 'observed_run': run,
            'documents': parsed, 'joins': deepcopy(joins), 'populations': populations, 'native_measurements': deepcopy(list(observations.values())),
            'support_observations': support, 'dependence_groups': _dependence(parsed, joins, analysis, inputs),
            'qualifications': qualifications, 'missing_requirements': requirements, 'assembly': deepcopy(assembly), 'read_outcomes': outcomes}
        v._validate_common(common, provider)
        partial = any(r['status'] != 'ok' for r in outcomes) or any(d['severity'] == 'error' for d in qualifications)
        return {'status': 'partial' if partial else 'ok', 'value': common, 'diagnostics': deepcopy(qualifications)}
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error).startswith(('bvbrc_phylogeny_', 'phylogeny_')) else 'bvbrc_phylogeny_extraction_operand_invalid'
        return {'status': 'invalid', 'value': None, 'diagnostics': [{'code': code, 'phase': 'association', 'path': '', 'severity': 'error', 'evidence_refs': []}]}


__all__ = ['extract_common_fields', 'input_member_subject_id']
