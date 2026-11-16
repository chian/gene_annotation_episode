from __future__ import annotations
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.blast_pairwise_grader import validate_blast_correspondence_instance
from gene_annotation_episode.episodic_workflow.root.a110.alignment_correspondence import validate_correspondence_artifacts, _same
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_search import PROGRAM_UNITS
from gene_annotation_episode.episodic_workflow.root.a110.domain import identity, parse_sequences
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_contracts import _options

def record_key(bundle, search_key, family, hit_ordinal=None, hsp_ordinal=None):
    return identity('native_blast_pairwise_row', {'bundle_identity': bundle['identity'], 'search_key': search_key, 'family': family, 'hit_ordinal': hit_ordinal, 'hsp_ordinal': hsp_ordinal})

def _failure(diagnostics, stage, code, key=None, **details):
    diagnostics.append({'stage': stage, 'code': code, 'record_key': key, **details})

def _input_records(bundle, paths, snapshots, diagnostics):
    units = PROGRAM_UNITS[bundle['program']]
    options = _options(bundle['requested_job']['native_blast'])
    records = {}
    for axis, role, unit, flag in (('query', 'query_sequence', units[0], '-query_loc'), ('reference', 'subject_sequence', units[1], '-subject_loc')):
        items = [row for row in paths if row['kind'] == 'input' and row['role'] == role]
        if len(items) != 1:
            _failure(diagnostics, 'inputs', 'native_blast_captured_operand_missing', role=role)
            continue
        item = items[0]
        binding = next((b for b in bundle['operand_bindings'] if b['operand_role'] == role), None)
        snapshot = snapshots.get((binding or {}).get('subject_ref') if axis == 'query' else (binding or {}).get('reference_ref'))
        molecule = 'protein' if unit == 'aa' else 'dna'
        if snapshot and snapshot.get('molecule') in {'dna', 'rna'} and (unit == 'nt'):
            molecule = snapshot['molecule']
        try:
            parsed = parse_sequences(Path(item['path']).read_bytes(), format='fasta', molecule=molecule)
            if len(parsed) != 1:
                raise ValueError('native_blast_single_fasta_operand_required')
            source = parsed[0]
            if 'unexpected_symbol_for_declared_molecule' in source.issues:
                raise ValueError('native_blast_fasta_molecule_conflict')
            interval = options.get(flag)
            interval = [int(interval.split('-')[0]) - 1, int(interval.split('-')[1])] if interval else None
            if interval and interval[1] > len(source.sequence):
                raise ValueError('native_blast_selected_interval_outside_operand')
            native_title = source.name + (' ' + source.description if source.description else '')
            row = {'axis': axis, 'operand_role': role, 'record_ordinal': 0, 'artifact_ref': item['artifact_ref'], 'artifact_key': item['relative_path'], 'native_id': source.name, 'native_title': native_title, 'sequence': source.sequence, 'sequence_sha256': hashlib.sha256(source.sequence.encode('ascii')).hexdigest(), 'molecule': molecule, 'length': len(source.sequence), 'selected_interval': interval, 'binding': binding, 'binding_error': None}
            if binding:
                if binding['native_name'] is None and binding['native_accession'] is None or (binding['native_name'] is not None and binding['native_name'] != source.name) or (binding['native_accession'] is not None and binding['native_accession'] != source.name) or (axis == 'query' and binding['reference_ref'] is not None) or (axis == 'reference' and binding['subject_ref'] is not None):
                    row['binding_error'] = 'native_blast_operand_binding_identity_mismatch'
                supplied = binding['subject_ref'] if axis == 'query' else binding['reference_ref']
                if supplied is not None:
                    if not snapshot or snapshot.get('error'):
                        row['binding_error'] = (snapshot or {}).get('error') or 'native_blast_store_binding_unavailable'
                    elif snapshot['length'] != row['length'] or snapshot['molecule'] != molecule or snapshot['sequence_sha256'] != row['sequence_sha256']:
                        row['binding_error'] = 'native_blast_subject_sequence_mismatch'
                    elif axis == 'reference' and (snapshot['record_type'] != 'reference' or snapshot['accession'] != source.name):
                        row['binding_error'] = 'native_blast_reference_binding_identity_mismatch'
            records[axis] = row
            if row['binding_error']:
                _failure(diagnostics, 'binding', row['binding_error'], role=role)
        except (ValueError, OSError, UnicodeError) as error:
            _failure(diagnostics, 'inputs', str(error), role=role)
    return records

def _invocation(bundle, records):
    options = _options(bundle['requested_job']['native_blast'])
    operands, bindings = ([], {})
    for axis, row in records.items():
        binding = row['binding'] or {}
        ref = binding.get('subject_ref') if axis == 'query' else binding.get('reference_ref')
        descriptor = {'subject_ref': ref, **{key: row[key] for key in ('length', 'molecule', 'artifact_key', 'native_id', 'selected_interval')}}
        bindings[axis] = descriptor
        operands.append({'role': 'query' if axis == 'query' else 'subject', **descriptor, 'record_ordinal': 0, 'native_title': row['native_title'], 'identity': {'namespace': 'sequence_sha256', 'value': row['sequence_sha256'], 'version': None}})
    return ({'execution_program': bundle['program'], 'scientific_mode': 'pairwise', 'resource_kind': 'local', 'query_kind': 'sequence', 'reference_kind': 'sequence', 'request': bundle['requested_job'], 'effective_options': {**options, 'requested_hit_limit': int(options['-max_target_seqs']) if '-max_target_seqs' in options else None, 'requested_hsp_limit': int(options['-max_hsps']) if '-max_hsps' in options else None}, 'operands': operands, 'completion': {'native_returncode': bundle['returncode'], 'producer_complete': bundle['returncode'] == 0 and (not bundle['failures'])}}, bindings)

def _hsp_values(component, common):
    if component is None:
        return {}
    if common is None:
        raise ValueError('native_blast_common_hsp_components_required')
    counts, scores = (common['counts'], component['native_scores'])
    values = {name: scores[source] for name, source in (('native_score_bits', 'bit_score'), ('native_raw_score', 'score'), ('native_evalue', 'evalue'))}
    values.update({name: counts.get(source) for name, source in (('alignment_columns', 'alignment_columns'), ('paired_positions', 'paired_positions'), ('identical_positions', 'identical_positions'), ('substituted_positions', 'substituted_positions'), ('query_gap_columns', 'query_gap_columns'), ('reference_gap_columns', 'reference_gap_columns'))})
    values.update({axis + '_aligned_positions': common['paired_units'][axis] for axis in ('query', 'reference')})
    values.update({name: component['denominators'][name] for name in ('query_length', 'reference_length')})
    values.update(component['fractions'])
    return values

def validate_native_blast_correspondence_collections(sheet, scores, *, admission=False):
    """Authenticate the explicit new collection companion without frozen regrading."""
    if set(sheet) != {'schema', 'collection', 'searches', 'publication_inputs', 'correspondence'} or sheet['schema'] != 'native_blast_sheet_collection_v2' or set(scores) != {'schema', 'searches', 'rows', 'metric_definitions', 'correspondence', 'fallback_hsp_components'} or (scores['schema'] != 'native_blast_scores_collection_v2') or (not _same(sheet['correspondence'], scores['correspondence'])):
        raise ValueError('native_blast_correspondence_collections_required')
    companion = validate_correspondence_artifacts(scores['correspondence'], admission=admission)
    expected = {}
    for index, entry in enumerate(scores['searches']):
        if entry['scores'] is not None:
            expected['/searches/' + str(index) + '/scores/components'] = entry['scores']['components']
    for index, entry in enumerate(scores['fallback_hsp_components']):
        expected['/fallback_hsp_components/' + str(index) + '/component'] = entry['component']
    if {instance['legacy_pointer'] for instance in companion['instances']} != set(expected):
        raise ValueError('native_blast_correspondence_instances_conflict')
    for instance in companion['instances']:
        if instance['axis_basis'] != 'qualified':
            raise ValueError('native_blast_correspondence_axis_conflict')
        validate_blast_correspondence_instance(expected[instance['legacy_pointer']], instance)
