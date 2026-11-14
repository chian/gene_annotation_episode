"""Run a pinned phmmer and the original scoped detector on an allocation.

This is a new receipt profile over the existing A103 detector, not a fabricated
legacy parsed-search receipt. No family/function score is calculated here.
"""
import base64
from copy import deepcopy
import hashlib
from importlib.metadata import version
import io
from pathlib import Path
import subprocess
import zlib


PROFILE = 'a107_genomic_detection_v1'
REFERENCE_CDS_VERSION = 'a107_reference_cds_verifications_v1'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def matched_reference_translations(detection, verified_cds):
    """Keep all actual CDS candidates for each hit sequence, not its FASTA label."""
    targets = {}
    for hit in detection['native_hits']:
        targets.setdefault(hit['sequence_sha256'], []).append(hit['native_target_id'])
    matches = [{**deepcopy(row), 'native_target_ids': sorted(set(targets[row['sequence_sha256']]))}
        for row in verified_cds
        if row['in_searched_database'] and row['sequence_sha256'] in targets]
    return {'version': REFERENCE_CDS_VERSION, 'matches': matches,
        'method': 'original_a103_scoring._translation_reused_from_the_same_detector_call',
        'identity_rule': 'hit_sequence_hash_to_all_verified_reference_CDS; not_FASTA_label_to_locus',
        'coordinate_scope': 'actual_admitted_GenBank_record_local_frame; no_genome_offset_inferred',
        'translation_semantics': 'original_detector_verified_status; not_an_experimental_measurement',
        'terminal_stop_handling': {
            'original_policy': 'try_cds_true; on_failure_translate_and_strip_trailing_stop_symbols',
            'executed_calls': 'retained_in_each_match.translation_calculation',
            'actual_nucleotide_calculated_and_declared_sequences_retained': True},
        'not_established': ['submitted_target_genomic_origin', 'experimental_sample_genotype',
            'protein_expression', 'required_partnership', 'molecular_function']}


def validate_reference_translations(native, request):
    """Authenticate retained witness identities without recalculating translation."""
    retained = native.get('reference_cds_verifications')
    if retained is None:
        require(request.get('reference_cds_verifications_version') is None,
            'a107_requested_reference_translation_witnesses_missing')
        return  # Historical native publications remain readable as originally saved.
    require(request.get('reference_cds_verifications_version') in (None, REFERENCE_CDS_VERSION),
        'a107_requested_reference_translation_version_conflict')
    require(retained['version'] == REFERENCE_CDS_VERSION, 'a107_reference_translation_version_conflict')
    admitted = {(row['source_ref'], row['accession']): row for row in request['genomic_records']}
    targets = {}
    for hit in native['detection']['native_hits']:
        targets.setdefault(hit['sequence_sha256'], set()).add(hit['native_target_id'])
    witnessed = set()
    for row in retained['matches']:
        origin = admitted.get((row['record_source_ref'], row['selected_accession']))
        require(origin is not None and row['source_file_sha256'] ==
            request['assets'][row['record_source_ref']]['file']['sha256'],
            'a107_reference_translation_source_conflict')
        scope_matches = [scope for scope in native['detection']['record_scopes']
            if scope['source_file_sha256'] == row['source_file_sha256']
            and scope['accession'] == row['accession'] and scope['record_length'] == row['record_length']]
        require(row['selected_accession'] == origin['accession'] and scope_matches
            and row['source_request'] == origin['source_request']
            and row['coordinate_system'] == 'zero_based_half_open_record_local'
            and row['source_feature_index'] >= 0
            and row['segments'] and all(0 <= start < end <= row['record_length']
                for start, end in row['segments'])
            and row['segments'] == [[part['start'], part['end']] for part in row['location_parts']]
            and all(part['ref'] is None and part['strand'] in (-1, 0, 1, None)
                for part in row['location_parts']), 'a107_reference_translation_frame_conflict')
        translation = row['translation']
        require(translation['status'] == 'verified' and translation['exact_boundaries'] is True
            and translation['calculated_sequence'] is not None
            and translation['sequence'] == translation['calculated_sequence']
            and translation['declared_sequence'] in (None, translation['calculated_sequence'])
            and sha(translation['sequence'].encode()) == row['sequence_sha256']
            and row['in_searched_database'] is True,
            'a107_reference_translation_sequence_conflict')
        calculation = row['translation_calculation']
        call = calculation['translation_call']
        require(calculation['version'] == 'a103_translation_calculation_v1'
            and calculation['completed'] is True and calculation['qualification'] is None
            and calculation['codon_start'] == translation['codon_start']
            and call['table'] == translation['genetic_code'] and type(call['cds']) is bool
            and call['postprocessing'] == ('none' if call['cds'] else 'rstrip_terminal_stop_symbols'),
            'a107_reference_translation_calculation_provenance_conflict')
        require(set(row['native_target_ids']) == targets.get(row['sequence_sha256'])
            and row['native_target_ids'], 'a107_reference_translation_hit_conflict')
        witnessed.add(row['sequence_sha256'])
    require(witnessed == set(targets), 'a107_reference_translation_hit_witness_missing')


def reference_translation_evidence(native, sequence_sha256, unresolved_symbols):
    retained = native.get('reference_cds_verifications')
    if retained is None:
        return None
    exact = [deepcopy(row) for row in retained['matches'] if row['sequence_sha256'] == sequence_sha256]
    return {'version': REFERENCE_CDS_VERSION,
        'state': ('verified_reference_CDS_literal_sequence_correspondence' if exact else
            'no_verified_reference_CDS_for_the_exact_component_sequence'),
        'matches': exact, 'literal_sequence_identity_supported': bool(exact),
        'biological_residue_identity_complete': bool(exact) and not unresolved_symbols,
        'unresolved_component_symbols': deepcopy(unresolved_symbols),
        'translation_method': retained['method'],
        'terminal_stop_handling': deepcopy(retained['terminal_stop_handling']),
        'coordinate_scope': retained['coordinate_scope'],
        'evidence_dependence': 'same_original_native_search_and_reference_translation; not_an_independent_confirmation',
        'target_or_sample_genomic_origin': 'not_established_by_reference_correspondence'}


def calculate(request, unit):
    from Bio import SeqIO
    from .a103_detection import detect
    from .a103_scoring import parse_records
    require(version('biopython') == request['biopython_version'],
        'a107_detector_biopython_version_conflict')
    pin = request['binding']
    executable = Path(pin['executable'])
    require(executable.is_file() and sha(executable.read_bytes()) == pin['sha256'],
        'a107_detector_executable_identity_conflict')
    software = subprocess.run([str(executable), '-h'], capture_output=True, check=True)
    require(b'phmmer' in software.stdout.lower(), 'a107_detector_requires_phmmer')
    query = request['query_sequence']
    require(sha(query.encode()) == request['query_sequence_sha256'],
        'a107_detector_query_identity_conflict')
    query_path = unit/'inputs'/'component.faa'
    query_path.write_text('>a107_component_query\n'+query+'\n')
    database = base64.b64decode(request['input']['bytes_base64'], validate=True)
    require(sha(database) == request['input']['file']['sha256'],
        'a107_detector_database_identity_conflict')
    database_path = unit/'inputs'/'annotated-cds.faa'
    database_path.write_bytes(database)
    bindings = []
    for selected in request['genomic_records']:
        asset = request['assets'][selected['source_ref']]
        encoded = base64.b64decode(asset['bytes_base64'], validate=True)
        if asset.get('encoding') == 'zlib_base64':
            decoder = zlib.decompressobj()
            raw = decoder.decompress(encoded, asset['file']['size_bytes']+1)
            require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                'a107_detector_genomic_encoding_conflict')
        else:
            require(asset.get('encoding') in (None, 'base64'), 'a107_detector_unknown_input_encoding')
            raw = encoded
        require(len(raw) == asset['file']['size_bytes'] and sha(raw) == asset['file']['sha256'],
            'a107_detector_genomic_bytes_conflict')
        records = parse_records(raw.decode('utf-8'), format='genbank')
        matches = [record for record in records if selected['accession'] in {
            record.id, record.name, *record.annotations.get('accessions', [])}]
        require(len(matches) == 1, 'a107_detector_genomic_record_not_unique')
        record = matches[0]
        projection = io.StringIO()
        SeqIO.write([record], projection, 'genbank')
        bindings.append({'accession': record.id, 'selected_accession': selected['accession'],
            'source_ref': selected['source_ref'],
            'genbank_projection': projection.getvalue(),
            'source_request': deepcopy(selected['source_request']), 'record_length': len(record),
            'source_file_sha256': asset['file']['sha256']})
    native = unit/'phmmer.txt'
    hits = unit/'phmmer.tbl'
    domains = unit/'phmmer.domtbl'
    command = [str(executable), '--notextw', '-o', str(native),
        '--tblout', str(hits), '--domtblout', str(domains), str(query_path), str(database_path)]
    executed = subprocess.run(command, capture_output=True)
    (unit/'phmmer.stderr').write_bytes(executed.stderr)
    require(executed.returncode == 0, 'a107_detector_phmmer_nonzero_exit:'+str(executed.returncode))
    # The original detector independently parses the complete one-query native
    # output, checks program/query/termination and verifies CDS translations.
    # Null legacy handles below are transport placeholders, never Source IDs.
    verified_cds = []
    proof = detect({'native_path': str(native), 'database_path': str(database_path),
        'search_metadata': {'database_sha256': sha(database), 'native_parameters': {
            'command': command, 'executable_sha256': pin['sha256'],
            'help_sha256': sha(software.stdout)}},
        'query_sequence': query, 'bindings': bindings, 'component_ref': request['component_ref'],
        'snapshot_ref': None, 'native_source_ref': None,
        'database_source_ref': request['source_ref'], 'neighborhood': None}, verified_cds=verified_cds)
    proof.update(binding_refs=deepcopy(request['selection']['binding_refs']),
        target_ref=request['target_ref'],
        target_regions=[[row['start'], row['end']] for row in request['target_regions']])
    artifacts = {}
    for name, path in (('native_text', native), ('hit_table', hits), ('domain_table', domains)):
        raw = path.read_bytes()
        artifacts[name] = {'sha256': sha(raw), 'size_bytes': len(raw),
            'bytes_base64': base64.b64encode(raw).decode()}
    return {'version': PROFILE, 'selection': deepcopy(request['selection']),
        'dataset_id': 'searched-protein-fasta:'+sha(database),
        'origin': 'native_search_over_received_sequences_and_annotations',
        'query_sequence_sha256': request['query_sequence_sha256'],
        'database_sha256': sha(database), 'software': {
            'executable': str(executable), 'sha256': pin['sha256'],
            'phmmer_help_utf8': software.stdout.decode('utf-8'),
            'biopython_version': version('biopython')},
        'native_command': command, 'native_returncode': executed.returncode,
        'native_artifacts': artifacts, 'detection': proof,
        'reference_cds_verifications': matched_reference_translations(proof, verified_cds),
        'receipt_kind': 'authenticated_HPC_search_and_original_scoped_detector; not_legacy_snapshot_registration',
        'limitations': ['No function, required partnership or sample origin follows from detection.',
            'Copied translation annotations are checked against the admitted genomic records.',
            'Unexamined or unverifiable CDS preserve unknown coverage and preclude scoped absence.',
            'No whole-genome or replicon absence is inferred.']}
