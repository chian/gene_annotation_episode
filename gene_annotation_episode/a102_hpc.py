"""A102 work definitions and scientific admission over the existing HPC service.

Scheduler decisions, prediction sisters, launch, observation and collection stay
with HPCEpisodes. Only authenticated original native results can mint B here.
"""
from copy import deepcopy
import base64
import hashlib
import json
import math
from pathlib import Path
import zlib

from .communication import plain
from .domain import canonical
from .a102_scoring import digest, require
from .a102_structures import binding_summary, comparison_identity
from .a102_native_setup import PINS
from .a102_hpc_worker import VERSION as NATIVE_VERSION
from .hpc_result_receipts import planned_input_files


VERSION = 'a102_shared_hpc_custody_v1'
REQUEST_PROVIDER = 'host.a102.hpc_request'
RESULT_PROVIDER = 'host.a102.hpc_admission'
SOURCE_FILES = ('__init__.py', 'a102_native_worker.py', 'a102_scoring.py', 'a102_structures.py',
    'protein_structure_formats.py', 'protein_structure_sequences.py', 'protein_structure_contracts.py',
    'protein_structure_metadata.py', 'execution_contracts.py', 'communication.py',
    'form_reference_validation.py', 'episode_bindings.py', 'launch_instructions.py', 'tool_knowledge.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def install(store):
    for table in ('a102_hpc_requests', 'a102_hpc_results'):
        store.db.execute('CREATE TABLE IF NOT EXISTS '+table+
            ' (source_ref TEXT PRIMARY KEY, body TEXT NOT NULL)')


def _source(store, provider, body, scope):
    artifact = store.artifact(canonical(body), 'application/json')
    return store.put('source', {'provider': provider, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': scope['subject_refs']}, origin='tool')['id']


def _registered(store, reference, table, provider):
    record = store.get(reference)
    if record.get('provider') != provider:
        return None
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone()
    row = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(row is not None and record['origin'] == 'tool' and record['version'] == VERSION,
        'a102_original_hpc_scientific_grant_required')
    body = json.loads(row[0])
    require(json.loads(store.get_artifact(record['artifact_ref'])) == body, 'a102_hpc_scientific_custody_conflict')
    return body


def request_body(store, reference):
    return _registered(store, reference, 'a102_hpc_requests', REQUEST_PROVIDER)


def result_body(store, reference):
    return _registered(store, reference, 'a102_hpc_results', RESULT_PROVIDER)


def binding(store, reference, known, scope):
    require(reference in known, 'a102_hpc_structure_binding_not_received')
    source = store.get(reference)
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name='a102_structure_bindings'").fetchone()
    row = store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(row is not None and source['origin'] == 'tool'
        and source['provider'] == 'native.a102.structure_binding', 'a102_hpc_structure_binding_custody_required')
    body = json.loads(row[0])
    require(json.loads(store.get_artifact(source['artifact_ref'])) == binding_summary(body),
        'a102_hpc_structure_binding_custody_conflict')
    if body['target_ref'] is not None:
        require(store.scope_covers(store.coverage(body.get('material_ref') or body['target_ref']), scope),
            'a102_hpc_target_binding_outside_scope')
    return body


def _native_binding(body):
    """Stage the existing algorithm's CA operands, without unrelated atoms."""
    return {key: deepcopy(body.get(key)) for key in ('target_ref', 'sequence', 'length', 'target_scope',
        'coordinates', 'model_metadata', 'file_identity', 'selection', 'coordinate_sha256',
        'coordinate_to_input_mapping', 'qualifications')}


def prepare_request(store, arguments, *, context, known):
    install(store)
    scope = store.validate_scope(plain(context.scope))
    target = _native_binding(binding(store, arguments['target_binding_ref'], known, scope))
    references = list(arguments['reference_binding_refs'])
    algorithm = arguments['algorithm']
    require(algorithm in PINS and 1 <= len(references) <= 32
        and (algorithm != 'US-align' or len(references) == 1), 'a102_hpc_comparison_panel_invalid')
    panel = [{'binding_ref': reference, 'binding': _native_binding(binding(store, reference, known, scope))}
        for reference in references]
    attribution = arguments.get('attribution')
    if target['target_ref'] is None:
        require(attribution is not None and attribution['target_ref'] in known
            and attribution['target_ref'] in scope['subject_refs'], 'a102_hpc_reference_requires_target_attribution')
        from .a101_scoring import intervals
        regions = attribution['target_regions']
        require(intervals(regions, length=store.subject_length(attribution['target_ref']), merge_adjacent=False) == regions,
            'a102_hpc_reference_attribution_regions_invalid')
        store.validate_scope({'subject_refs': [attribution['target_ref']], 'segments': [
            {'target_ref': attribution['target_ref'], 'start': start, 'end': end, 'unit': 'aa'}
            for start, end in regions]}, parent_scope=scope)
        if attribution['sequence_alignment_ref'] is not None:
            require(attribution['sequence_alignment_ref'] in known, 'a102_hpc_sequence_attribution_not_received')
        target = {**target, 'target_ref': arguments['target_binding_ref']}
    else:
        require(attribution is None, 'a102_hpc_direct_and_reference_attribution_are_separate')
    native = {'operation': 'usalign' if algorithm == 'US-align' else 'foldseek',
        'target': target, 'target_binding_ref': arguments['target_binding_ref'], 'primary': arguments['primary']}
    if algorithm == 'US-align':
        native.update(reference=panel[0]['binding'], reference_binding_ref=references[0],
            comparison_group=comparison_identity(target, panel[0]['binding']),
            variant_ref=digest({'target': target, 'reference': panel[0]['binding'], 'algorithm': algorithm}))
    else:
        manifest = [{'binding_ref': row['binding_ref'], 'file_identity': row['binding']['file_identity'],
            'selection': row['binding']['selection']} for row in panel]
        native.update(references=panel, database_manifest={'entries': manifest, 'sha256': digest(manifest)},
            request_identity=digest({'target': target, 'references': panel, 'algorithm': algorithm}))
    directory = Path(__file__).parent
    sources = {'gene_annotation_episode/'+name: (directory/name).read_text() for name in SOURCE_FILES}
    snapshot = canonical(sources)+'\n'
    files = {'a102-sources.json': snapshot, 'a102-worker.py': (directory/'a102_hpc_worker.py').read_text()}
    manifest = {name: sha(text.encode()) for name, text in sources.items()}
    manifest['a102-worker.py'] = sha(files['a102-worker.py'].encode())
    request = {'version': NATIVE_VERSION, 'algorithm': algorithm, 'software_pin': deepcopy(PINS[algorithm]),
        'native_request': native, 'code_manifest': manifest, 'source_snapshot_sha256': sha(snapshot.encode()),
        'code_manifest_sha256': sha(canonical(manifest).encode())}
    raw = (canonical(request)+'\n').encode()
    body = {'version': VERSION, 'run_id': context.run_id, 'scope': scope,
        'target_binding_ref': arguments['target_binding_ref'], 'reference_binding_refs': references,
        'attribution': plain(attribution), 'request': request, 'request_json': raw.decode(),
        'request_sha256': sha(raw), 'files': files, 'worker_sha256': manifest['a102-worker.py'],
        'code_manifest_sha256': request['code_manifest_sha256'], 'resource_id': arguments['resource_id']}
    with store.transaction():
        reference = _source(store, REQUEST_PROVIDER, body, scope)
        store.db.execute('INSERT OR IGNORE INTO a102_hpc_requests VALUES(?,?)', (reference, canonical(body)))
    return reference


def commission(store, reference, resources):
    body = request_body(store, reference)
    resource = resources[body['resource_id']]
    root = '{allocation_workspace}'
    request_path, worker_path = root+'/a102-request.json', root+'/a102-worker.py'
    request = body['request']
    target = request['native_request']['target']
    count = len(body['reference_binding_refs'])
    panel = ([request['native_request']['reference']] if request['native_request']['operation'] == 'usalign'
        else [row['binding'] for row in request['native_request']['references']])
    features = {'nodes': 1, 'wall_seconds': 900, 'worker_threads': 1,
        'target_residues': len(target['coordinates']), 'reference_count': count,
        'reference_residues': sum(len(row['coordinates']) for row in panel)}
    from .execution_guidance import resource_identity
    resource_key = resource_identity(body['resource_id'], resource)
    profile = {'resource_id': resource_key, 'backend': 'hpc', 'tool': 'a102.structural_comparison',
        'implementation': body['code_manifest_sha256'], 'parameters': digest({
            'algorithm': request['algorithm'], 'pin': request['software_pin'], 'native_profile': 'CA'}),
        'hardware': resource_key}
    candidate = {'id': 'a102_'+body['request_sha256'][:16], 'queue': 'debug', 'nodes': 1,
        'wall_seconds': 900, 'features': features,
        'units': [{'unit_id': 'structural_comparison', 'obligation_id': 'native_structural_comparison',
            'argv': [resource['python_executable'], '-B', worker_path, request_path],
            'environment': {'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}, 'effort': 1.}],
        'files': [{'path': name, 'text': text} for name, text in body['files'].items()]+
            [{'path': 'a102-request.json', 'text': body['request_json']}],
        'preparation': 'Prepare and execute the supplied structural-analysis request on Aurora. '
            'Choose the scripts, Python environment and commands needed for its numpy/jsonschema '
            'dependencies and pinned official native assets. Preserve the declared scientific inputs, '
            'software identity and output provenance. Keep preparation files in the assigned workspace. '
            'Compilation, version probes, coordinate processing and native structure calculations belong '
            'on the allocated compute nodes. Retain the original result in HPC_UNIT_DIRECTORY.'}
    predicates = [{'field': [key], 'operator': 'eq', 'value': value} for key, value in (
        ('version', NATIVE_VERSION), ('program', 'a102_structural_native'), ('completed', True), ('returncode', 0),
        ('request_sha256', body['request_sha256']), ('worker_sha256', body['worker_sha256']),
        ('code_manifest_sha256', body['code_manifest_sha256']))]
    return {'objective': 'Execute this exact received A102 structural comparison on Aurora. Return '
        'native correspondences, transforms, extent, qualifiers and original provenance. Structural '
        'opposition or an uninformative search is useful; no particular similarity or function is expected.',
        'resource_id': body['resource_id'], 'execution_profile': profile,
        'monitoring': {'min_interval_seconds': 60., 'max_interval_seconds': 120., 'monitor_cost': .001},
        'yield_bindings': {
            'hpc': {'cutoff': .01, 'parameters': {'uncertainty_alpha': .05}},
            'hpc_prediction': {'cutoff': .001, 'parameters': {'uncertainty_alpha': .05}},
            'hpc_execution': {'cutoff': .01, 'parameters': {'uncertainty_alpha': .05}}},
        'obligations': {'native_structural_comparison': {'credit': 1., 'acceptance': predicates}},
        'candidates': [candidate], 'model': {'features': [{'name': key, 'transform': 'log1p',
            'scale': math.log1p(max(1, value))} for key, value in features.items()],
            'priors': {key: {'median_seconds': value, 'log_sigma': 2., 'coefficient_variance': .01}
                for key, value in {'queue': 900., 'setup': 30., 'work': 60., 'return': 10.}.items()},
            'resource_priors': {'cpu_seconds': {'median': 60., 'unit': 'cpu_seconds', 'log_sigma': 2.,
                'coefficient_variance': .01}, 'memory_bytes': {'median': 512*1024**2, 'unit': 'bytes',
                'log_sigma': 2., 'coefficient_variance': .01}}, 'success_prior': [1., 1.]},
        'history': [], 'validation_ids': [],
        'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
            {'id': 'planned_'+key, 'metric': key, 'phase': 'planned', 'minimum_elapsed_seconds': 0., 'weight': 1.}
            for key in ('queue', 'work', 'cpu_seconds', 'memory_bytes')]},
        'preferences': {'elapsed_cost_per_second': .00001, 'node_hour_cost': .01},
        'limits': {'result_limit_bytes': 512*1024, 'queue_max_age_seconds': 900}}


def admit_result(store, request_ref, hpc_result_ref, *, context, known, read_result):
    """Publish existing A102 numerical grants from qualified original HPC bytes."""
    from .a102_publication import publish_comparison
    from .a102_native_worker import _native
    install(store)
    require({request_ref, hpc_result_ref} <= known, 'a102_hpc_original_operands_not_received')
    expected = request_body(store, request_ref)
    require(expected is not None and expected['run_id'] == context.run_id, 'a102_hpc_original_request_required')
    store.validate_scope(expected['scope'], parent_scope=plain(context.scope))
    for ref in [expected['target_binding_ref'], *expected['reference_binding_refs']]:
        binding(store, ref, known, expected['scope'])
    authority = read_result(context, hpc_result_ref)
    receipt, plan, unit = authority['receipt'], authority['plan'], authority['unit']
    result = receipt['document']
    require(receipt['scope'] == expected['scope'], 'a102_hpc_original_result_scope_conflict')
    staged = {row['path']: row for row in planned_input_files(plan)}
    workspace = plan['manifest']['workspace']
    expected_files = {workspace+'/'+key: sha(value.encode()) for key, value in expected['files'].items()}
    expected_files[workspace+'/a102-request.json'] = expected['request_sha256']
    require(all(path in staged and staged[path]['sha256'] == value for path, value in expected_files.items()),
        'a102_hpc_original_staged_scientific_files_conflict')
    require(authority['resource_id'] == expected['resource_id']
        and unit['argv'] == [authority['resource']['python_executable'], '-B',
            workspace+'/a102-worker.py', workspace+'/a102-request.json'],
        'a102_hpc_original_native_command_conflict')
    require(result.get('version') == NATIVE_VERSION and result.get('program') == 'a102_structural_native'
        and result.get('request_sha256') == expected['request_sha256']
        and result.get('worker_sha256') == expected['worker_sha256']
        and result.get('code_manifest_sha256') == expected['code_manifest_sha256']
        and result.get('pbs_job_id') == receipt['job_id']
        and result.get('compute_hostname') and not result['compute_hostname'].startswith(('aurora-uan', 'login')),
        'a102_hpc_original_native_identity_conflict')
    require(result['returncode'] == receipt['unit']['returncode'], 'a102_hpc_original_execution_outcome_conflict')
    refs, leads, provenance = [], [], []
    if result['completed']:
        require(result['returncode'] == 0 and result['payload_encoding'] == 'zlib_base64',
            'a102_hpc_original_execution_not_completed')
        decoder = zlib.decompressobj()
        raw = decoder.decompress(base64.b64decode(result['payload'], validate=True), 128*1024**2)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
            and sha(raw) == result['payload_sha256'], 'a102_hpc_original_native_payload_conflict')
        document = json.loads(raw)
        native_request = expected['request']['native_request']
        q = native_request['target']
        panel = ({native_request['reference_binding_ref']: native_request['reference']}
            if native_request['operation'] == 'usalign' else
            {row['binding_ref']: row['binding'] for row in native_request['references']})
        require(len(document['comparisons']) == result['comparison_count']
            and len(document['leads']) == result['lead_count'], 'a102_hpc_native_population_conflict')
        for original in document['comparisons']:
            require(original['reference_ref'] in panel, 'a102_hpc_reference_not_in_original_panel')
            t = panel[original['reference_ref']]
            qi = {row['position']: index for index, row in enumerate(q['coordinates'])}
            ti = {row['position']: index for index, row in enumerate(t['coordinates'])}
            pairs = [(qi[a], ti[b]) for a, b in zip(original['target_positions'], original['reference_positions'], strict=True)]
            require(original['producer'] == expected['request']['algorithm']
                and all(original['software'].get(key) == value
                    for key, value in expected['request']['software_pin'].items()),
                'a102_hpc_original_native_software_conflict')
            parameters = {**native_request, 'reference_binding_ref': original['reference_ref'],
                'comparison_group': comparison_identity(q, t), 'variant_ref': original['variant_ref'],
                'native_transform_precision': original['transform'].get('native_rounding_precision')}
            reconstructed = _native(parameters, q, t, pairs, original['transform']['rotation'],
                original['transform']['translation_A'], original['native_metrics'], original['producer'], original['software'])
            # Foldseek retains additional printed-precision bounds and metrics.
            require(all(original.get(key) == value for key, value in reconstructed.items()
                if key not in {'native_metrics', 'qualifications'}), 'a102_hpc_original_native_geometry_conflict')
            native = deepcopy(original)
            # Job addresses/timings are execution provenance, not new measured
            # correspondences. Keep them in this actual admission, so another
            # delivery of identical geometry cannot create a primary variant.
            execution = {'software_path': native['software'].pop('path', None),
                'native_command': native['native_metrics'].pop('command', None),
                'stdout_sha256': native['native_metrics'].pop('original_stdout_sha256', None)}
            native['execution_provenance'] = {'request_ref': request_ref,
                'code_manifest_sha256': expected['code_manifest_sha256'],
                'original_execution': 'separately_received_A102_HPC_admission'}
            reference = publish_comparison(store, native)['source_ref']
            refs.append(reference)
            provenance.append({'comparison_ref': reference, **execution})
            if expected['attribution'] is not None:
                from .a102_attachments import request as attachment_request
                attribution = expected['attribution']
                operands = [attribution['target_ref'], reference, expected['target_binding_ref'], original['reference_ref']]
                if attribution['sequence_alignment_ref'] is not None:
                    operands.append(attribution['sequence_alignment_ref'])
                refs.append(attachment_request(store, {'operation': 'structure.reference_align',
                    'target_ref': attribution['target_ref'], 'measurement_ref': reference,
                    'measured_binding_ref': expected['target_binding_ref'], 'regions': attribution['target_regions'],
                    'sequence_alignment_ref': attribution['sequence_alignment_ref']}, operands))
        leads = document['leads']
    else:
        require(result['returncode'] != 0 and result.get('failure'), 'a102_hpc_failed_execution_requires_original_reason')
    body = {'version': VERSION, 'scope': expected['scope'], 'request_ref': request_ref,
        'hpc_result_ref': hpc_result_ref, 'hpc_source_artifact_ref': authority['source_artifact_ref'],
        'pbs_job_id': receipt['job_id'], 'completed': result['completed'], 'failure': result.get('failure'),
        'python_version': result.get('python_version'),
        'comparison_refs': refs, 'native_execution_provenance': provenance,
        'unresolved_leads': leads, 'scientific_scalar': None,
        'interpretation': 'original_native_comparisons_use_existing_A102_grader; execution_credit_separate'}
    with store.transaction():
        reference = _source(store, RESULT_PROVIDER, body, expected['scope'])
        store.db.execute('INSERT OR IGNORE INTO a102_hpc_results VALUES(?,?)', (reference, canonical(body)))
    return [reference, *refs]


def receive_results(store, context, known, *, read_result):
    """Deterministic receipt routing, also used when the result arrives later."""
    requests = {body['request_sha256']: ref for ref in known
        if (body := request_body(store, ref)) is not None}
    admitted = {(body['request_ref'], body['hpc_result_ref']) for ref in known
        if (body := result_body(store, ref)) is not None}
    generated, needs = [], []
    for reference in sorted(known):
        source = store.get(reference)
        if source.get('provider') != 'episode.hpc_result':
            continue
        document = json.loads(store.get_artifact(source['artifact_ref'])).get('document', {})
        request = requests.get(document.get('request_sha256'))
        if document.get('program') != 'a102_structural_native' or request is None or (request, reference) in admitted:
            continue
        expected = request_body(store, request)
        missing = {expected['target_binding_ref'], *expected['reference_binding_refs']} - known
        if missing:
            body = {'version': VERSION, 'scope': expected['scope'], 'request_ref': request,
                'hpc_result_ref': reference, 'status': 'pending_attribution',
                'missing_record_refs': sorted(missing), 'scientific_credit': 0.}
            generated.append(_source(store, 'host.a102.hpc_pending_attribution', body, expected['scope']))
            for target in expected['scope']['subject_refs']:
                needs.append((request, {'target_ref': target, 'policy': 'a102_received_hpc_comparison',
                    'missing': ['received_original_structural_bindings'],
                    'required_operands': {'source_refs': sorted(missing), 'hpc_result_ref': reference}}))
            continue
        try:
            with store.transaction():
                published = admit_result(store, request, reference,
                    context=context, known=known, read_result=read_result)
            generated.extend(published)
        except (ValueError, KeyError, OSError) as error:
            # Keep the original receipt visible. A failed scientific admission
            # earns nothing and must not undo delivery of the actual result.
            body = {'version': VERSION, 'scope': expected['scope'], 'request_ref': request,
                'hpc_result_ref': reference, 'status': 'scientific_admission_unavailable',
                'reason': str(error), 'scientific_credit': 0.}
            generated.append(_source(store, 'host.a102.hpc_admission_failure', body, expected['scope']))
    return list(dict.fromkeys(generated)), needs


def received_execution_findings(store, context, known):
    """Expose actual received execution/admission states, without polling."""
    findings = []
    for reference in sorted(known):
        source = store.get(reference)
        if source.get('provider') == RESULT_PROVIDER:
            body = result_body(store, reference)
        elif source.get('provider') in {'host.a102.hpc_pending_attribution', 'host.a102.hpc_admission_failure'}:
            require(source['origin'] == 'tool' and source['version'] == VERSION, 'a102_hpc_status_source_required')
            body = json.loads(store.get_artifact(source['artifact_ref']))
        else:
            continue
        if not (store.scope_contains(plain(context.scope), body['scope'])
                or store.scope_contains(body['scope'], plain(context.scope))):
            continue
        findings.append({'source_ref': reference, 'receiving_scope': plain(context.scope), **deepcopy(body)})
    admitted = {(row['request_ref'], row['hpc_result_ref']): row['source_ref']
        for row in findings if 'completed' in row}
    for row in findings:
        replacement = admitted.get((row['request_ref'], row['hpc_result_ref']))
        if 'status' in row and replacement is not None:
            row.update(current=False, resolved_by_admission_ref=replacement)
        else:
            row['current'] = True
    return findings
