"""Remote FBA metadata and input freeze; original solver/reader formulas remain.

Caller-supplied remote software pins are deployment metadata, not an assertion
that the software is available. The native driver verifies them on allocation.
"""
from copy import deepcopy
import base64
from importlib.metadata import version
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, obj
from .flux_balance_contracts import flux_balance_schema
from .flux_balance_request_binding import scientific_request_schema, _files
from .flux_balance_result_contracts import fba_result_schema
from .native_flux_balance_contracts import validate_flux_balance_software
from .component_axis_native_contracts import VERSION
from .component_axis_native_hpc import (MAX_INPUT_BYTES, REQUEST_PROVIDER,
    sha, require, publish, provenance)


TOOL = 'chemistry.request_flux_balance_hpc'
PROFILE = 'a110_flux_balance_hpc_v2'
FBA_SOURCES = ('a110_fba_native.py', 'communication.py', 'form_reference_validation.py',
    'episode_bindings.py', 'launch_instructions.py', 'tool_knowledge.py', 'execution_contracts.py',
    'flux_balance_contracts.py', 'native_flux_balance_contracts.py', 'native_flux_balance_storage.py',
    'flux_balance_readers.py', 'flux_balance_sheet.py', 'flux_balance_calculations.py',
    'flux_balance_result_contracts.py', 'flux_balance_result_views.py', 'flux_balance_result_selection.py',
    'flux_balance_worker_contracts.py', 'flux_balance_native_capture_contracts.py', 'flux_balance_result_worker.py')


def normalize(bindings):
    require(type(bindings) in (list, tuple), 'remote_fba_bindings_required')
    result = []
    for supplied in bindings:
        row = plain(supplied)
        require(type(row) is dict and set(row) == {'id', 'resource_id', 'software', 'model_formats'},
            'remote_fba_binding_invalid')
        require(all(type(row[key]) is str and bool(row[key]) for key in ('id', 'resource_id'))
            and type(row['model_formats']) is list and bool(row['model_formats'])
            and set(row['model_formats']) <= {'sbml', 'cobra_json'}
            and len(row['model_formats']) == len(set(row['model_formats'])), 'remote_fba_binding_invalid')
        row['software'] = validate_flux_balance_software(row['software'])
        result.append(row)
    require(len({row['id'] for row in result}) == len(result), 'duplicate_remote_fba_binding')
    return result


def catalog(bindings):
    if not bindings:
        return {}
    ref = {'type': 'string', 'format': 'reference'}
    fields = {'target_ref': ref, 'resource_id': {'enum': sorted({row['resource_id'] for row in bindings})},
        'binding_id': {'enum': [row['id'] for row in bindings]}, 'request': scientific_request_schema(),
        'calculation_parameters': flux_balance_schema('FBACalculationParameters'),
        'projection': fba_result_schema('FBAProjectionSelector')}
    return {TOOL: {'description': 'Freeze an actually received metabolic model and explicitly selected '
        'steady-state FBA question for the shared HPC owner. Original Cobra/GLPK capture, readers, '
        'calculations and selected projection are reused. No local solve or new scientific scalar.',
        'resources': 'local', 'input_schema': obj(fields),
        'instructions': 'Select only caller-configured remote software. Software availability and pins '
            'are checked by the original native driver inside the compute allocation; missing deployment '
            'remains an explicit operational failure. Use the returned HPC commission and its existing '
            'prediction/execution sisters. Scientific admission occurs automatically on receipt. Bounds, '
            'objective, solver settings and annotation-to-reaction mappings remain explicit assumptions. '
            'A steady-state linear optimum does not establish atom balance, thermodynamic feasibility '
            'or biological activity. The returned projection grants only its selected numerical data. '
            'A remote worksheet path or digest does not grant other cells or a local FBA receipt.'}}


def freeze(registry, args, *, context, known, invocation):
    store = registry.store
    selected = [row for row in registry.a110_flux_balance_bindings
        if row['id'] == args['binding_id'] and row['resource_id'] == args['resource_id']]
    require(len(selected) == 1, 'remote_fba_binding_not_configured')
    binding = selected[0]
    code_root = Path(__file__).parent
    selected_files = {row['path']: row for row in binding['software']['implementation_files']}
    for name in ('__init__.py', 'execution_contracts.py', 'flux_balance_contracts.py',
            'native_flux_balance_contracts.py', 'native_flux_balance_storage.py',
            'native_flux_balance_cobra_glpk.py', 'native_flux_balance_driver.py'):
        path = binding['software']['module_root']+'/gene_annotation_episode/'+name
        require(path in selected_files and selected_files[path]['sha256'] == sha((code_root/name).read_bytes()),
            'remote_fba_deployment_code_differs_from_selected_implementation:'+name)
    require(args['target_ref'] in known, 'remote_fba_target_not_received')
    footprint = store.coverage(args['target_ref'])
    require(footprint and store.scope_covers(footprint, plain(context.scope)), 'remote_fba_original_target_scope_required')
    roots = {row['target_ref'] for row in footprint}
    require(len(roots) == 1, 'remote_fba_single_original_target_required')
    # Reuse the existing file-selection resolver without starting its local
    # backend or manufacturing its private action/closure receipt records.
    from .flux_balance_tools import OrdinaryFluxBalanceTools
    from types import SimpleNamespace
    resolved, assets, refs, total = [], {}, {args['target_ref']}, 0
    for selection in _files(args['request']):
        require(selection['witness_ref'] in known, 'remote_fba_original_file_witness_not_received')
        try:
            row = OrdinaryFluxBalanceTools._resolve(SimpleNamespace(store=store), context, invocation[1], selection)
        except ValueError as error:
            witness = store.get(selection['witness_ref'])
            artifact = selection['witness_ref'] if selection['artifact_field'] is None else witness.get(selection['artifact_field'])
            raise ContractError('component_native_original_fba_file_not_admitted', detail={
                'input_admission': True, 'failure': str(error), 'witness_ref': selection['witness_ref'],
                'required_artifact_ref': artifact}) from error
        file = row['file']
        if file['sha256'] not in assets:
            total += file['size_bytes']
            require(total <= MAX_INPUT_BYTES, 'remote_fba_inputs_exceed_transfer_capacity; large_file_staging_required')
            raw = Path(row['path']).read_bytes()
            require(sha(raw) == file['sha256'] and len(raw) == file['size_bytes'], 'remote_fba_original_input_bytes_conflict')
            assets[file['sha256']] = {'file': file, 'bytes_base64': base64.b64encode(raw).decode()}
        refs.add(selection['witness_ref'])
        resolved.append({key: deepcopy(row[key]) for key in ('selection', 'file', 'witness')})
    primary = next(row for row in resolved if row['selection'] == args['request']['model_input']['file'])
    require(primary['file']['format'] in binding['model_formats'], 'remote_fba_model_format_not_bound')
    directory = Path(__file__).parent
    names = tuple(dict.fromkeys(['component_axis_native_contracts.py', *FBA_SOURCES]))
    sources = {'axis_native/'+name: (directory/name).read_text() for name in names}
    sources['axis_native/__init__.py'] = ''
    worker = (directory/'component_axis_native_worker.py').read_text()
    manifest = {name: sha(text.encode()) for name, text in sources.items()}
    manifest['component-worker.py'] = sha(worker.encode())
    snapshot = canonical(sources)+'\n'
    selection = {key: deepcopy(args[key]) for key in ('request', 'calculation_parameters', 'projection')}
    native = {'version': VERSION, 'axis': 'A110', 'operation': TOOL, 'scientific_profile': PROFILE,
        'run_id': context.run_id, 'episode_id': context.episode_id, 'operation_key': invocation[4],
        'scope': plain(context.scope), 'target_ref': next(iter(roots)), 'target_regions': footprint,
        'resource_id': args['resource_id'], 'binding': deepcopy(binding), 'selection': selection,
        'input': assets[primary['file']['sha256']], 'assets': assets, 'resolved_files': resolved,
        'jsonschema_version': version('jsonschema'), 'code_manifest': manifest,
        'code_manifest_sha256': sha(canonical(manifest).encode()), 'source_snapshot_sha256': sha(snapshot.encode())}
    raw_request = (canonical(native)+'\n').encode()
    body = {'version': VERSION, 'axis': 'A110', 'operation': TOOL, 'scientific_profile': PROFILE,
        'run_id': context.run_id, 'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': footprint, 'source_ref': primary['selection']['witness_ref'],
        'input_file': primary['file'], 'request': native, 'request_sha256': sha(raw_request),
        'worker_sha256': manifest['component-worker.py'], 'code_manifest_sha256': native['code_manifest_sha256'],
        'logical_work_sha256': sha(canonical({'selection': selection, 'files': [row['file'] for row in resolved],
            'software': binding['software'], 'profile': PROFILE, 'implementation': manifest}).encode()),
        'resource_id': args['resource_id'], 'evidence_refs': sorted(refs),
        'input_provenance': provenance(store, [row['selection']['witness_ref'] for row in resolved]),
        'arguments_sha256': sha(canonical(args).encode()),
        'features': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'worker_threads': 1},
        'files': {'component-worker.py': worker, 'component-sources.json': snapshot,
            'component-request.json': raw_request.decode()}, 'scientific_credit': None,
        'preparation': 'Prepare and execute this declared flux-balance request on Aurora. Choose the '
            'scripts, environment and commands needed for jsonschema '+native['jsonschema_version']
            +' and the caller-selected Cobra/GLPK deployment. Preserve all software pins, model/input '
            'identity, requested projection and original native-driver provenance. Keep preparation '
            'files within the assigned workspace. Flux-balance computation executes on allocated '
            'compute nodes and returns the original requested result through its existing readers.'}
    reference = publish(store, REQUEST_PROVIDER, body)
    return reference, body
