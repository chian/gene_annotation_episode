"""Bounded input custody for an allocated phmmer/original-detector request."""
import base64
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import re
import zlib

from .communication import plain
from .domain import ContractError, canonical, obj
from .component_axis_native_contracts import VERSION
from .component_axis_native_hpc import MAX_INPUT_BYTES, REQUEST_PROVIDER, provenance, publish, require, sha
from .a107_genomic_detection_native import PROFILE, REFERENCE_CDS_VERSION


TOOL = 'partner.request_detection_hpc'


def normalize(bindings):
    rows = plain(bindings)
    require(type(rows) is list, 'a107_detector_bindings_required')
    for row in rows:
        require(type(row) is dict and set(row) == {'id', 'resource_id', 'executable', 'sha256'},
            'a107_detector_binding_invalid')
        require(all(type(row[key]) is str and row[key] and not any(char in row[key] for char in '\0\r\n')
            for key in row) and Path(row['executable']).is_absolute()
            and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'a107_detector_binding_invalid')
    require(len({row['id'] for row in rows}) == len(rows), 'a107_duplicate_detector_binding')
    return deepcopy(rows)


def catalog(bindings):
    if not bindings:
        return {}
    ref = {'type': 'string', 'format': 'reference'}
    return {TOOL: {'resources': 'local', 'description':
        'Freeze an actually received protein query, searched CDS FASTA and selected GenBank records '
        'for pinned phmmer and the original scoped detector on shared HPC. Preserve native inclusion, '
        'verified translations, examined extent and incomplete coverage. Retain the same calculation\'s '
        'matched reference-CDS peptide/nucleotide sequences, record-local coordinates and executed '
        'translation modes for later qualification without repeating that calculation. No local search, A101 score '
        'or functional/whole-genome absence inference. Return native component and execution facts.',
        'input_schema': obj({'target_ref': deepcopy(ref), 'component_ref': deepcopy(ref),
            'database_source_ref': deepcopy(ref),
            'genomic_records': {'type': 'array', 'minItems': 1, 'maxItems': 32,
                'items': obj({'source_ref': deepcopy(ref), 'accession': {'type': 'string', 'minLength': 1}})},
            'binding_refs': {'type': 'array', 'items': deepcopy(ref), 'uniqueItems': True,
                'description': 'Optional actually received original locus bindings for later genomic-context qualification.'},
            'resource_id': {'enum': sorted({row['resource_id'] for row in bindings})},
            'binding_id': {'enum': [row['id'] for row in bindings]}})}}


def freeze(registry, args, *, context, known, invocation):
    from .component_sequence_attribution import protein_sequence, MAX_MAP_POSITIONS
    from .a103_publication import binding_body
    from .a103_hpc import SOURCES
    store = registry.store
    candidates = [row for row in registry.a107_detection_bindings
        if row['id'] == args['binding_id'] and row['resource_id'] == args['resource_id']]
    require(len(candidates) == 1, 'a107_detector_binding_not_configured')
    require({args['target_ref'], args['component_ref']} <= known, 'a107_detector_query_not_received')
    footprint = store.coverage(args['target_ref'])
    require(footprint and store.scope_covers(footprint, plain(context.scope)), 'a107_detector_original_scope_required')
    roots = {row['target_ref'] for row in footprint}
    require(len(roots) == 1, 'a107_detector_single_target_required')
    query = protein_sequence(store, args['component_ref'])
    require(0 < len(query) <= MAX_MAP_POSITIONS, 'a107_detector_query_exceeds_transfer_capacity')
    refs = {args['target_ref'], args['component_ref'], *args['binding_refs']}
    for reference in args['binding_refs']:
        binding_body(store, reference, known)
    assets, total = {}, len(query.encode())

    def file(reference, format):
        nonlocal total
        require(reference in known and reference in store.reference_subset([reference], plain(context.scope)),
            'a107_detector_original_file_not_received')
        if reference in assets:
            require(assets[reference]['file']['format'] == format, 'a107_detector_file_format_conflict')
            return assets[reference]
        admitted, path = invocation[1](context, reference, 'source', file_format=format)
        if admitted.get('failure') is not None or path is None:
            from .materials import source_window_selection
            artifact, _, _ = source_window_selection(store.get(reference), 'original')
            raise ContractError('component_native_original_detector_file_not_admitted', detail={
                'input_admission': True, 'failure': admitted.get('failure'),
                'witness_ref': reference, 'required_artifact_ref': artifact})
        identity = admitted['input']['file']
        total += identity['size_bytes']
        require(total <= MAX_INPUT_BYTES, 'a107_detector_inputs_exceed_transfer_capacity')
        raw = path.read_bytes()
        require(len(raw) == identity['size_bytes'] and sha(raw) == identity['sha256'],
            'a107_detector_original_file_bytes_conflict')
        require(raw.lstrip().startswith(b'>' if format == 'fasta_text' else b'LOCUS'),
            'a107_detector_input_format_mismatch')
        # Keep large literal genomic sequences out of the operational model's
        # frozen-file presentation without changing their byte identity.
        encoded = zlib.compress(raw) if format == 'genbank_text' else raw
        assets[reference] = {'file': identity,
            'encoding': 'zlib_base64' if format == 'genbank_text' else 'base64',
            'bytes_base64': base64.b64encode(encoded).decode()}
        refs.add(reference)
        return assets[reference]

    primary = file(args['database_source_ref'], 'fasta_text')
    records = []
    for selected in args['genomic_records']:
        file(selected['source_ref'], 'genbank_text')
        source = store.get(selected['source_ref'])
        original = json.loads(store.get_artifact(source['request_ref'])) if source.get('request_ref') else None
        records.append({**deepcopy(selected), 'source_request': original})
    require(len({(row['source_ref'], row['accession']) for row in records}) == len(records),
        'a107_detector_duplicate_record_selection')
    require(set(store.reference_subset(refs, plain(context.scope))) == refs,
        'a107_detector_operand_outside_scope')
    directory = Path(__file__).parent
    names = tuple(dict.fromkeys([*SOURCES, 'component_axis_native_contracts.py', 'a107_genomic_detection_native.py']))
    sources = {'axis_native/'+name: (directory/name).read_text() for name in names}
    sources['axis_native/__init__.py'] = ''
    worker = (directory/'component_axis_native_worker.py').read_text()
    manifest = {name: sha(text.encode()) for name, text in sources.items()}
    manifest['component-worker.py'] = sha(worker.encode())
    snapshot = canonical(sources)+'\n'
    selection = {key: deepcopy(args[key]) for key in (
        'component_ref', 'database_source_ref', 'genomic_records', 'binding_refs')}
    native = {'version': VERSION, 'axis': 'A107', 'operation': TOOL, 'scientific_profile': PROFILE,
        'run_id': context.run_id, 'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': footprint, 'component_ref': args['component_ref'],
        'source_ref': args['database_source_ref'], 'resource_id': args['resource_id'],
        'binding': deepcopy(candidates[0]), 'selection': selection,
        'reference_cds_verifications_version': REFERENCE_CDS_VERSION,
        'query_sequence': query, 'query_sequence_sha256': sha(query.encode()),
        'input': primary, 'assets': {ref: asset for ref, asset in assets.items()
            if ref != args['database_source_ref']}, 'genomic_records': records,
        'biopython_version': version('biopython'), 'jsonschema_version': version('jsonschema'),
        'code_manifest': manifest, 'code_manifest_sha256': sha(canonical(manifest).encode()),
        'source_snapshot_sha256': sha(snapshot.encode())}
    raw_request = (canonical(native)+'\n').encode()
    require(len(raw_request) <= 2*MAX_INPUT_BYTES, 'a107_detector_frozen_request_exceeds_transfer_capacity')
    body = {'version': VERSION, 'axis': 'A107', 'operation': TOOL, 'scientific_profile': PROFILE,
        'run_id': context.run_id, 'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': footprint, 'source_ref': args['database_source_ref'], 'input_file': primary['file'],
        'request': native, 'request_sha256': sha(raw_request), 'worker_sha256': manifest['component-worker.py'],
        'code_manifest_sha256': native['code_manifest_sha256'],
        'logical_work_sha256': sha(canonical({'selection': selection, 'query_sha256': sha(query.encode()),
            'files': {ref: asset['file'] for ref, asset in assets.items()}, 'binding': candidates[0],
            'profile': PROFILE, 'implementation': manifest}).encode()),
        'resource_id': args['resource_id'], 'evidence_refs': sorted(refs),
        'input_provenance': provenance(store, refs), 'arguments_sha256': sha(canonical(args).encode()),
        'features': {'input_bytes': total, 'query_symbols': len(query), 'genomic_records': len(records)},
        'files': {'component-worker.py': worker, 'component-sources.json': snapshot,
            'component-request.json': raw_request.decode()}, 'scientific_credit': None,
        'preparation': 'Prepare and execute the declared genomic search and scoped detector. Choose '
            'the scripts, environment and commands needed for jsonschema '+native['jsonschema_version']
            +' and Biopython '+native['biopython_version']+', retaining the caller-selected pinned '
            'phmmer deployment, actual search inputs and original result provenance. Keep preparation '
            'files in the assigned workspace. The search and detector execute on allocated compute nodes.'}
    return publish(store, REQUEST_PROVIDER, body), body
