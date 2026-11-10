"""Exact A104 work commissions and authenticated shared-HPC result admission.

There is one scheduler: the existing HPC episode. This module freezes molecular
operands and connects its original execution receipts to scientific readers.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .domain import ContractError, canonical
from .a104_hpc_worker import VERSION as NATIVE_VERSION, validate_request, alignment_correspondence, read_fasta, tree_summary
from .hpc_result_receipts import planned_input_files


REQUEST_PROVIDER = 'host.a104.native_request'
RESULT_PROVIDER = 'native.a104.phylogeny'
VERSION = 'a104_shared_hpc_custody_v1'


def require(condition, code):
    if not condition:
        raise ContractError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def install(store):
    for table in ('a104_native_requests', 'a104_native_results'):
        store.db.execute('CREATE TABLE IF NOT EXISTS '+table+' (source_ref TEXT PRIMARY KEY, body TEXT NOT NULL)')


def _source(store, provider, body, operands):
    artifact = store.artifact(canonical(body), 'application/json')
    return store.put('source', {'provider': provider, 'accession': sha(canonical(body).encode()),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': VERSION, 'retrieved_at': None,
        'operand_refs': sorted({ref for ref in operands if store.get(ref)['record_type'] in
            {'input', 'feature', 'product', 'read_subject', 'reference'}})}, origin='tool')['id']


def _registered(store, reference, table, provider):
    record = store.get(reference)
    if record['record_type'] != 'source' or record.get('provider') != provider:
        return None
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    row = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(row is not None and record['origin'] == 'tool' and record.get('version') == VERSION,
            'a104_host_scientific_grant_required')
    body = json.loads(row[0])
    require(json.loads(store.get_artifact(record['artifact_ref'])) == body, 'a104_native_custody_conflict')
    return body


def request_body(store, reference):
    return _registered(store, reference, 'a104_native_requests', REQUEST_PROVIDER)


def native_body(store, reference):
    body = _registered(store, reference, 'a104_native_results', RESULT_PROVIDER)
    if body is not None:
        original = request_body(store, body['request_ref'])
        require(original is not None and original['native_request_sha256'] == body['request_sha256'],
                'a104_native_original_request_conflict')
        receipt = store.get(body['hpc_result_ref'])
        require(sha(store.get_artifact(receipt['artifact_ref'])) == body['hpc_receipt_sha256'],
                'a104_native_original_hpc_receipt_changed')
    return body


def sequence(store, reference):
    row = store.get(reference)
    require(row['record_type'] in {'input', 'feature', 'product', 'read_subject', 'reference'}
            and store.subject_unit(reference) == 'aa', 'a104_actual_protein_operand_required')
    if row.get('sequence_ref'):
        value = store.get_artifact(row['sequence_ref']).decode('ascii')
    elif row['record_type'] == 'feature':
        require(row.get('strand') != '-', 'a104_protein_feature_cannot_reverse_complement')
        parent = sequence(store, row['subject_ref'])
        value = ''.join(parent[span['start']:span['end']] for span in row['segments'])
    elif row['record_type'] == 'read_subject':
        from . import packing
        value = packing.component_window(store, store.get(row['member_ref']), 'sequence', 0, row['length']).decode('ascii')
    else:
        raise ContractError('a104_protein_sequence_unavailable')
    return value.replace(' ', '').replace('\n', '').upper().rstrip('*')


def native_taxon(store, reference):
    """Read actual UniProt identity metadata; copied functional names are unused."""
    record = store.get(reference)
    if record['record_type'] != 'reference':
        return None
    source = store.get(record['source_ref'])
    if not source.get('artifact_ref'):
        return None
    try:
        value = json.loads(store.get_artifact(source['artifact_ref']))
    except (ValueError, UnicodeError):
        return None
    rows = value.get('results', [value])
    matches = [row for row in rows if row.get('primaryAccession') == record.get('accession')]
    if len(matches) != 1:
        return None
    original = matches[0].get('sequence', {}).get('value')
    if not original or original.upper() != sequence(store, reference):
        return None
    taxon = matches[0].get('organism', {}).get('taxonId')
    return {'taxon_id': taxon, 'source_ref': source['id'], 'accession': record['accession']} if taxon else None


def independent_marker_basis(store, analysis):
    """Check this implemented reference protocol against original metadata.

    A purpose label cannot turn another copy of the family panel into an
    independent organismal reference. Orthology and species-tree uncertainty
    remain explicit even with these separately sourced ribosomal markers.
    """
    basis = analysis.get('organismal_basis', {})
    aliases = {'L2': {'rplb', 'rpl2'}, 'L3': {'rplc', 'rpl3'}, 'S3': {'rpsc', 'rps3'}}
    require(basis.get('kind') == 'independent_ribosomal_marker_supermatrix'
            and basis.get('markers') == list(aliases), 'a104_independent_organismal_marker_protocol_required')
    for member in analysis['members']:
        require(len(member['parts']) == len(aliases) and member.get('taxon_id') is not None,
                'a104_actual_independent_marker_parts_and_taxon_required')
        for group, part in zip(aliases, member['parts']):
            reference = store.get(part['subject_ref'])
            identity = native_taxon(store, part['subject_ref'])
            require(identity is not None and identity['taxon_id'] == member['taxon_id'],
                    'a104_independent_marker_original_identity_required')
            source = store.get(reference['source_ref'])
            value = json.loads(store.get_artifact(source['artifact_ref']))
            record = next(row for row in value.get('results', [value])
                          if row.get('primaryAccession') == reference['accession'])
            genes = {entry['value'].lower() for gene in record.get('genes', [])
                     for entry in [gene.get('geneName', {}), *gene.get('synonyms', [])] if entry.get('value')}
            require(bool(genes & aliases[group]), 'a104_marker_identity_not_supported_by_original_metadata')


def prepare_request(store, *, target_ref, analyses, scope, known_record_refs, case_id,
                    threads=4, seed=104, model='LG', target_origin_reference_ref=None):
    """Freeze exact received proteins/regions without requiring an annotation."""
    install(store)
    known = set(known_record_refs)
    scope = store.validate_scope(scope)
    require(target_ref in known and target_ref in scope['subject_refs'], 'a104_original_target_required')
    if target_origin_reference_ref is not None:
        require(target_origin_reference_ref in known, 'a104_caller_target_origin_not_received')
    bindings, native, operands = [], [], {target_ref}
    target_seen = False
    for analysis in analyses:
        if analysis['purpose'] == 'organismal_reference':
            independent_marker_basis(store, analysis)
        entries, members = [], []
        for row in analysis['members']:
            parts, symbols, taxa = [], [], []
            for part in row['parts']:
                subject = part['subject_ref']
                require(subject in known and subject in store.reference_subset([subject], scope),
                        'a104_panel_member_not_received')
                full = sequence(store, subject)
                regions = part.get('regions', [[0, len(full)]])
                require(regions and all(type(a) is int and type(b) is int and 0 <= a < b <= len(full)
                                        for a, b in regions), 'a104_panel_region_invalid')
                require(all(a[1] <= b[0] for a, b in zip(regions, regions[1:])), 'a104_panel_regions_overlap')
                mapped = store.map_segments(subject, [{'start': a, 'end': b} for a, b in regions]) if store.roots(subject) else []
                target_regions = [[span['start'], span['end']] for span in mapped if span['target_ref'] == target_ref]
                symbols.append(''.join(full[a:b] for a, b in regions))
                offset, selected_segments = 0, []
                for start, end in regions:
                    selected_segments.append([offset, start, end-start])
                    offset += end-start
                parts.append({'subject_ref': subject, 'regions': deepcopy(regions), 'full_length': len(full),
                              'target_regions': target_regions,
                              'selected_residue_to_subject_segments': selected_segments,
                              'original_mapping': store.sequence_mapping(subject) if store.roots(subject) else None,
                              'original_sequence_sha256': sha(full.encode())})
                operands.add(subject)
                if target_regions and target_origin_reference_ref is not None:
                    require(full == sequence(store, target_origin_reference_ref),
                            'a104_caller_target_origin_sequence_conflict')
                identity = native_taxon(store, target_origin_reference_ref if target_regions
                                        and target_origin_reference_ref is not None else subject)
                if identity:
                    taxa.append(identity)
                if target_regions:
                    target_seen = True
            require(analysis['purpose'] not in {'family', 'regional', 'sensitivity'} or len(parts) == 1,
                    'a104_family_tip_cannot_invent_a_fused_protein')
            if row.get('taxon_id') is not None:
                require(taxa and all(t['taxon_id'] == row['taxon_id'] for t in taxa)
                        and len(taxa) == len(parts), 'a104_tip_taxon_requires_actual_matching_metadata')
            text = ''.join(symbols)
            entry = {'tip_id': row['tip_id'], 'sequence': text, 'sequence_sha256': sha(text.encode()),
                     'part_lengths': [len(value) for value in symbols]}
            entries.append(entry)
            members.append({'tip_id': row['tip_id'], 'parts': parts, 'sequence_sha256': entry['sequence_sha256'],
                            'taxon_id': row.get('taxon_id'), 'taxon_evidence': taxa})
        native.append({'name': analysis['name'], 'purpose': analysis['purpose'], 'entries': entries,
                       **{key: analysis[key] for key in ('model', 'seed') if key in analysis}})
        if analysis['purpose'] in {'family', 'regional', 'sensitivity'}:
            require(sum(bool(part['target_regions']) for member in members for part in member['parts']) == 1,
                    'a104_one_original_target_tip_per_family_analysis_required')
            identities = [member['parts'][0]['subject_ref'] for member in members]
            require(len(identities) == len(set(identities)),
                    'a104_one_physical_protein_occurrence_per_family_tip_required')
        bindings.append({'name': analysis['name'], 'purpose': analysis['purpose'], 'members': members,
                         'organismal_basis': analysis.get('organismal_basis')})
    require(target_seen, 'a104_target_missing_from_native_family_request')
    family_sequences = {sequence(store, part['subject_ref']) for row in analyses if row['purpose'] != 'organismal_reference'
                        for member in row['members'] for part in member['parts']}
    marker_sequences = {sequence(store, part['subject_ref']) for row in analyses if row['purpose'] == 'organismal_reference'
                        for member in row['members'] for part in member['parts']}
    require(not family_sequences & marker_sequences, 'a104_family_and_organismal_inputs_must_be_independent')
    request = validate_request({'version': NATIVE_VERSION, 'case_id': case_id, 'threads': threads,
                               'seed': seed, 'model': model, 'bootstrap_replicates': 1000, 'analyses': native})
    raw = (canonical(request)+'\n').encode()
    worker = Path(__file__).with_name('a104_hpc_worker.py').read_text()
    body = {'version': VERSION, 'target_ref': target_ref, 'scope': scope, 'case_id': case_id,
        'native_request': request, 'native_request_json': raw.decode(), 'native_request_sha256': sha(raw),
        'worker_text': worker, 'worker_sha256': sha(worker.encode()), 'bindings': bindings,
        'caller_target_origin_reference_ref': target_origin_reference_ref,
        'interpretation': 'exact_scientific_operands; no_tree_measurement_or_function_claim'}
    with store.transaction():
        reference = _source(store, REQUEST_PROVIDER, body, operands)
        store.db.execute('INSERT OR IGNORE INTO a104_native_requests VALUES(?,?)', (reference, canonical(body)))
    return reference


def commission(store, request_ref, resource, *, queue='debug', scheduler_wall_seconds=900):
    """A useful scientific portfolio for the existing HPC episode contract."""
    body = request_body(store, request_ref)
    require(body is not None, 'a104_declared_native_request_required')
    workspace = '{allocation_workspace}'
    code = workspace+'/a104-worker.py'
    data = workspace+'/a104-request.json'
    request = body['native_request']
    features = {'nodes': 1, 'wall_seconds': scheduler_wall_seconds, 'worker_threads': request['threads'],
        'sequence_count': sum(len(row['entries']) for row in request['analyses']),
        'input_residue_count': sum(len(entry['sequence']) for row in request['analyses'] for entry in row['entries']),
        'analysis_count': len(request['analyses']),
        'marker_partition_count': sum(len(row['entries'][0]['part_lengths']) for row in request['analyses']
                                      if row['purpose'] == 'organismal_reference'),
        'model_selection_count': sum(row.get('model', request['model']) == 'MFP' for row in request['analyses'])}
    from .execution_guidance import resource_identity
    identity = resource_identity('aurora', resource)
    profile = {'resource_id': identity, 'backend': 'hpc', 'tool': 'a104.phylogeny',
        'implementation': body['worker_sha256'],
        'parameters': sha(canonical({'native_protocol': NATIVE_VERSION, 'bootstrap_replicates': 1000,
            'model_options': sorted({row.get('model', request['model']) for row in request['analyses']}),
            'programs': ['MUSCLE-5.3', 'IQ-TREE-2.4.0'], 'serial_analyses': True}).encode()),
        'hardware': identity}
    candidate = {'id': 'a104_'+body['native_request_sha256'][:16], 'queue': queue,
        'nodes': 1, 'wall_seconds': scheduler_wall_seconds,
        'features': features,
        'units': [{'unit_id': 'phylogeny', 'obligation_id': 'native_phylogeny', 'effort': 1.,
                   'argv': [resource['python_executable'], '-B', code, data], 'environment': {}}],
        'files': [{'path': 'a104-worker.py', 'text': body['worker_text']},
                  {'path': 'a104-request.json', 'text': body['native_request_json']}],
        'preparation': 'Prepare and execute the declared phylogenetic analysis. Choose the scripts, '
            'Python environment and commands needed for Bio.Phylo and the pinned official MUSCLE and '
            'IQ-TREE assets. Preserve the scientific input panel, software identities and original '
            'native output provenance. Keep preparation files within the assigned workspace. Program '
            'version probes, alignment and tree inference execute on allocated compute nodes.'}
    predicates = [{'field': [name], 'operator': 'eq', 'value': value} for name, value in (
        ('program', 'a104_phylogeny_native'), ('completed', True), ('returncode', 0),
        ('case_id', body['case_id']), ('request_sha256', body['native_request_sha256']),
        ('worker_sha256', body['worker_sha256']))]
    return {'objective': 'Execute this exact A104 phylogenetic analysis on Aurora and return its original native '
            'alignments, trees, branch support and provenance. A biological contradiction remains useful evidence. '
            'Preserve the original PBS execution and do not substitute a local algorithm or another input panel.',
        'resource_id': 'aurora', 'execution_profile': profile,
        'monitoring': {'min_interval_seconds': 60., 'max_interval_seconds': 120., 'monitor_cost': .001},
        'obligations': {'native_phylogeny': {'credit': 10., 'acceptance': predicates}},
        'candidates': [candidate], 'model': {'features': [
            {'name': name, 'transform': 'log1p', 'scale': math.log1p(scale)} for name, scale in
            (('nodes', 1.), ('wall_seconds', 900.), ('worker_threads', 4.), ('sequence_count', 64.),
             ('input_residue_count', 20000.), ('analysis_count', 4.), ('marker_partition_count', 3.),
             ('model_selection_count', 1.))],
            'priors': {name: {'median_seconds': seconds, 'log_sigma': 2., 'coefficient_variance': .01}
                       for name, seconds in {'queue': 900, 'setup': 30, 'work': 180, 'return': 10}.items()},
            # Broad initial demand priors, not measured history or allocation
            # capacity. Native PBS accounting supplies the later observations.
            'resource_priors': {
                'cpu_seconds': {'median': 180*request['threads'], 'unit': 'cpu_seconds',
                                'log_sigma': 2., 'coefficient_variance': .01},
                'memory_bytes': {'median': 256*1024**2, 'unit': 'bytes',
                                 'log_sigma': 2., 'coefficient_variance': .01}},
            'success_prior': [1., 1.]}, 'history': [], 'validation_ids': [],
        'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
            {'id': 'planned_'+name, 'metric': name, 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0}
            for name in ('queue', 'work', 'cpu_seconds', 'memory_bytes')]},
        'preferences': {'elapsed_cost_per_second': .00001, 'node_hour_cost': .01},
        'limits': {'result_limit_bytes': 512*1024, 'queue_max_age_seconds': 900}}


def import_result(store, *, request_ref, hpc_result_ref, known_record_refs, scope, run_id, workflow_directory=None):
    """Admit a result only after original shared-HPC collection and validation."""
    install(store)
    known = set(known_record_refs)
    require({request_ref, hpc_result_ref} <= known, 'a104_hpc_operands_not_received')
    expected = request_body(store, request_ref)
    def same_scope(left, right):
        return store.scope_contains(left, right) and store.scope_contains(right, left)
    require(expected is not None and same_scope(expected['scope'], store.validate_scope(scope)),
            'a104_hpc_original_scope_conflict')
    source = store.get(hpc_result_ref)
    require(source['record_type'] == 'source' and source.get('provider') == 'episode.hpc_result'
            and source['origin'] == 'tool' and source['version'] == 'hpc_result_v1', 'a104_actual_hpc_result_required')
    raw_receipt = store.get_artifact(source['artifact_ref'])
    receipt = json.loads(raw_receipt)
    require(receipt['run_id'] == run_id and same_scope(receipt['scope'], expected['scope']),
            'a104_hpc_receiving_run_conflict')
    require(all(store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
                for name in ('runtime_episodes', 'runtime_actions')), 'a104_original_completed_runtime_required')
    action = store.db.execute("SELECT a.action,a.result FROM runtime_actions a JOIN runtime_episodes e "
        "USING(run_id,episode_id) WHERE a.run_id=? AND a.episode_id=? AND json_extract(e.path,'$[#-1][0]') IN ('hpc','hpc_execution') "
        "AND json_extract(a.action,'$.tool')='hpc.results' AND a.result IS NOT NULL", (run_id, receipt['episode_id'])).fetchall()
    require(any(hpc_result_ref in json.loads(row['result']).get('record_refs', []) for row in action),
            'a104_hpc_result_requires_original_completed_collection_action')
    # The submitted portfolio must have staged this exact scientific worker
    # and request, rather than an unrelated command which copied their hashes.
    import sqlite3
    from contextlib import closing
    from .hpc_queue import digest as hpc_digest
    settings = (store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (run_id,)).fetchone()
                if store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_runs'").fetchone() else None)
    from method_loop.identities import EpisodeRef
    owner_path = store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                                 (run_id, receipt['episode_id'])).fetchone()
    require(owner_path is not None, 'a104_original_hpc_receiving_episode_required')
    path = json.loads(owner_path[0])
    prefixes = [path[:i+1] for i, part in enumerate(path) if part[0] == 'hpc']
    require(prefixes, 'a104_original_hpc_parent_required')
    owner = EpisodeRef(run_id, tuple(map(tuple, prefixes[-1]))).episode_id
    # Assembled runs persist their directory in runtime_runs. Direct Workflow
    # callers, including the original pilot, use the case's workflow directory
    # or explicitly pass their actual host directory. This locates evidence;
    # the original owning ledger and submission still authenticate every byte.
    runtime_directory = (Path(json.loads(settings[0])['directory']) if settings is not None else
                         Path(workflow_directory) if workflow_directory is not None else store.path.parent/'workflow')
    directory = runtime_directory/'hpc'/hpc_digest([run_id, owner])
    with closing(sqlite3.connect((directory/'hpc.sqlite').resolve().as_uri()+'?mode=ro', uri=True)) as reader:
        owners = [json.loads(row[0]) for row in reader.execute("SELECT body FROM evidence WHERE kind='owner'")]
        plans = [json.loads(row[0]) for row in reader.execute("SELECT body FROM evidence WHERE kind='plan'")]
    require(len(owners) == 1 and owners[0]['run_id'] == run_id and owners[0]['episode_id'] == owner
            and owners[0]['scope'] == receipt['scope'] and same_scope(owners[0]['scope'], expected['scope']),
            'a104_original_hpc_ledger_owner_conflict')
    plans = [plan for plan in plans if plan['plan_id'] == receipt['plan_id']]
    require(len(plans) == 1, 'a104_original_hpc_plan_required')
    files = {Path(item['path']).name: item for item in planned_input_files(plans[0])}
    require(files['a104-worker.py']['sha256'] == expected['worker_sha256']
            and files['a104-request.json']['sha256'] == expected['native_request_sha256'],
            'a104_original_hpc_staged_scientific_files_conflict')
    units = [unit for unit in plans[0]['manifest']['units'] if unit['unit_id'] == receipt['unit']['unit_id']]
    require(len(units) == 1 and units[0]['argv'][-2:] ==
            [files['a104-worker.py']['path'], files['a104-request.json']['path']],
            'a104_original_hpc_native_command_conflict')
    raw = base64.b64decode(receipt['window']['bytes_base64'], validate=True)
    require(sha(raw) == receipt['unit']['result_sha256'] and json.loads(raw) == receipt['document'],
            'a104_hpc_result_original_bytes_conflict')
    result = receipt['document']
    require(result.get('version') == NATIVE_VERSION and result.get('program') == 'a104_phylogeny_native'
            and result.get('returncode') == receipt['unit']['returncode']
            and (result.get('completed') is True and result.get('returncode') == 0
                 or result.get('completed') is False and result.get('returncode') != 0 and result.get('failure')),
            'a104_hpc_native_execution_outcome_conflict')
    require(result['request_sha256'] == expected['native_request_sha256']
            and result['worker_sha256'] == expected['worker_sha256'] and result['case_id'] == expected['case_id'],
            'a104_hpc_scientific_request_or_worker_conflict')
    require(result['pbs_job_id'] == receipt['job_id'] and result['compute_hostname']
            and not result['compute_hostname'].startswith(('aurora-uan', 'login')), 'a104_hpc_original_compute_identity_conflict')
    requested = {row['name']: row for row in expected['native_request']['analyses']}
    received_names = {row['name'] for row in result['analyses']}
    require(received_names and len(received_names) == len(result['analyses']) and received_names <= set(requested)
            and (not result['completed'] or received_names == set(requested)), 'a104_native_analysis_membership_conflict')
    for analysis in result['analyses']:
        original = requested[analysis['name']]
        require(analysis['purpose'] == original['purpose'], 'a104_native_analysis_role_conflict')
        fasta = ''.join('>'+row['tip_id']+'\n'+row['sequence']+'\n' for row in original['entries'])
        require(analysis['input_fasta'] == fasta and analysis['input_sha256'] == sha(fasta.encode()),
                'a104_native_original_panel_conflict')
        mapping = alignment_correspondence(read_fasta(analysis['alignment_fasta']), original['entries'])
        require(mapping == analysis['correspondence'], 'a104_native_region_mapping_conflict')
        require(tree_summary(analysis['maximum_likelihood_tree']) == analysis['tree_summary'],
                'a104_native_tree_measurement_conflict')
        require(analysis['support_method'] == 'ultrafast_bootstrap' and analysis['support_scale'] == 'percent'
                and analysis['bootstrap_population']['usable_replicates'] == 1000, 'a104_native_support_method_conflict')
        require(analysis['alignment_execution']['returncode'] == analysis['tree_execution']['returncode'] == 0,
                'a104_native_algorithm_execution_failed')
    body = {'version': VERSION, 'target_ref': expected['target_ref'], 'scope': expected['scope'],
        'request_ref': request_ref, 'request_sha256': expected['native_request_sha256'],
        'hpc_result_ref': hpc_result_ref, 'hpc_receipt_sha256': sha(raw_receipt),
        'pbs_job_id': receipt['job_id'], 'result_sha256': sha(raw), 'result': result,
        'bindings': expected['bindings'], 'interpretation': 'received_actual_native_phylogeny; functional_interpretation_separate'}
    body.update(partial_execution=not result['completed'], missing_analysis_names=sorted(set(requested)-received_names))
    operands = [part['subject_ref'] for analysis in expected['bindings'] for row in analysis['members'] for part in row['parts']]
    with store.transaction():
        reference = _source(store, RESULT_PROVIDER, body, operands)
        store.db.execute('INSERT OR IGNORE INTO a104_native_results VALUES(?,?)', (reference, canonical(body)))
    return reference
