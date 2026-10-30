#!/usr/bin/env python3
"""Explicit single-phase engineering verification; importing this file does no work.

Root selects one phase per invocation. No phase dispatches a subsequent phase.
Target/job identities are read from actual helper, tool and provider records.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import uuid


CHECKOUT = Path('/tmp/gene-annotation-hmmer-api-20261022-002')
EVIDENCE = Path('/tmp/hmmer-real-service-verification-20261022-001')
WORKSPACE = Path('/tmp/hmmer-real-service-fixed-target-20261022-001')
CASE = Path('/home/chia/repos/gene_annotation_episode/cases/gene_001')
WITNESS = CASE/'workspace'
PROTEIN_SHA256 = 'f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a'
LIMITS = {'memory_bytes': 20*1024**3, 'scratch_bytes': 4*1024**3,
          'wall_seconds': None}
BINDING_FILE = EVIDENCE/'selected-binding.json'
SELECTION_FILE = EVIDENCE/'caller-selection.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def source_identity():
    paths = sorted(path for package in ('gene_annotation_episode', 'method_loop')
                   for path in (CHECKOUT/package).rglob('*.py'))
    if not paths or any(path.is_symlink() for path in paths):
        raise ValueError('isolated_source_files_required')
    digest, files = hashlib.sha256(), {}
    for path in paths:
        name, body = str(path.relative_to(CHECKOUT)), path.read_bytes()
        files[name] = sha(body)
        digest.update(name.encode()+b'\0')
        digest.update(hashlib.sha256(body).digest())
    return {'runtime_implementation_sha256': digest.hexdigest(), 'source_files': files}


def save_new(path, value):
    """Keep every invocation and original selected binding; never overwrite one."""
    body = (canonical(value)+'\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def same_or_save(path, value):
    if path.exists():
        if read_json(path) != value:
            raise ValueError('saved_selection_identity_conflict')
    else:
        save_new(path, value)


def no_symlink_path(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('symlink_path_not_permitted')
    if path.resolve() != path:
        raise ValueError('exact_absolute_path_required')


def pin_and_import(expected):
    # No application import, Store construction or HTTP precedes this comparison.
    if re.fullmatch('[0-9a-f]{64}', expected) is None:
        raise ValueError('explicit_expected_runtime_implementation_pin_required')
    no_symlink_path(CHECKOUT)
    actual = source_identity()
    if actual['runtime_implementation_sha256'] != expected:
        raise ValueError('runtime_implementation_pin_mismatch')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(CHECKOUT))
    package = importlib.import_module('gene_annotation_episode')
    if Path(package.__file__).resolve() != CHECKOUT/'gene_annotation_episode/__init__.py':
        raise ValueError('application_import_outside_selected_checkout')
    from gene_annotation_episode.independent_execution import implementation_sha256
    if implementation_sha256() != expected:
        raise ValueError('imported_runtime_implementation_pin_mismatch')
    from gene_annotation_episode.acquisition import PublicClients
    from gene_annotation_episode.fixed_target_seed import prepare_fixed_target_seed
    from gene_annotation_episode.public_search_operations import (
        describe_hmmer_client_binding, hmmer_client_binding_sha256)
    from gene_annotation_episode.resource_service_setup import bind_public_search_ports
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    for name, module in tuple(sys.modules.items()):
        if name.split('.')[0] in {'gene_annotation_episode', 'method_loop'}:
            filename = getattr(module, '__file__', None)
            if filename and not Path(filename).resolve().is_relative_to(CHECKOUT):
                raise ValueError('runtime_import_outside_selected_checkout')
    return actual, dict(Store=Store, ToolRegistry=ToolRegistry, PublicClients=PublicClients,
        prepare_seed=prepare_fixed_target_seed, bind_ports=bind_public_search_ports,
        describe_client=describe_hmmer_client_binding, client_digest=hmmer_client_binding_sha256)


def fixed_case():
    case = read_json(CASE/'case.json')
    if (case['target_kind'] != 'single_gene' or case['case_ref'] != 'gene_001'
            or case['dna_length_nt'] != 762 or case['protein_length_aa'] != 253
            or case['source_protein'] != 'P0AAW1' or case['translation_table'] != 11):
        raise ValueError('original_fixed_case_identity_conflict')
    for name, expected in case['target_files'].items():
        if sha((CASE/name).read_bytes()) != expected:
            raise ValueError('original_fixed_case_file_changed')
    return case


def qualify_seed(seed, case):
    identity = seed['fixed_identity']
    if (seed['workspace'] != str(WORKSPACE)
            or seed['source']['workspace'] != str(WITNESS)
            or seed['source']['case_directory'] != str(CASE)
            or seed['source']['case_sha256'] != sha((CASE/'case.json').read_bytes())
            or identity['target_ref'] != case['target_ref']
            or identity['problem_ref'] != case['problem_ref']
            or identity['dna_length_nt'] != 762 or identity['protein_length_aa'] != 253
            or identity['source_protein'] != 'P0AAW1'
            or identity['protein_sequence_sha256'] != PROTEIN_SHA256):
        raise ValueError('exact_fixed_seed_required')


def actual_client(api):
    # Preserve the existing PublicClients timeout/configuration (currently its
    # own 90-second transport default). This adds no work or episode budget.
    client = api['PublicClients']()
    return client, api['describe_client'](client)


def open_selected(api, binding, client):
    no_symlink_path(WORKSPACE)
    if not (WORKSPACE/'state.sqlite3').is_file():
        raise ValueError('prepared_workspace_required')
    if (binding['workspace'] != str(WORKSPACE) or binding['checkout'] != str(CHECKOUT)
            or binding['registry']['client_binding_sha256'] != api['client_digest'](client)):
        raise ValueError('original_client_and_workspace_binding_required')
    if read_json(SELECTION_FILE) != {'caller_selection': binding['caller_selection'],
            'sources': binding['sources'], 'workspace': str(WORKSPACE)}:
        raise ValueError('original_saved_caller_selection_required')
    seed_file = WORKSPACE/'fixed-target-seed.json'
    if (sha(seed_file.read_bytes()) != binding['seed_receipt_sha256']
            or read_json(seed_file) != binding['seed']):
        raise ValueError('original_retained_seed_receipt_required')
    return api['Store'](WORKSPACE)


def ports_for(api, store, client, registry):
    tools = api['ToolRegistry'](store, clients=client, job_limits=LIMITS)
    ports = api['bind_ports'](store, tools, registry=registry)
    if (ports.operations.remote_searches is not tools.remote_searches
            or ports.result_publisher.tools is not tools
            or ports.operations.remote_searches.clients is not client):
        raise ValueError('same_actual_client_and_importer_owner_required')
    return tools, ports


def verify_original_order(store, ports, binding):
    if store.problem()['id'] != binding['seed']['fixed_identity']['problem_ref']:
        raise ValueError('prepared_problem_identity_conflict')
    if ports.operations.open_order(binding['order']['job_ref']) != binding['order']:
        raise ValueError('original_order_identity_conflict')
    if ports.operations.open_scope(binding['order']['job_ref']) != binding['order_scope']:
        raise ValueError('original_order_scope_conflict')
    if ports.operations.inspect(binding['order']['job_ref'])['request'] != binding['request']:
        raise ValueError('original_request_identity_conflict')
    sequence = ports.sequence_symbols(binding['product_ref'], scope=binding['scope'])
    if (store.get(binding['product_ref']) != binding['product_record']
            or len(sequence) != 253 or sha(sequence.encode()) != PROTEIN_SHA256):
        raise ValueError('original_exact_product_changed')


def prepare_order(args, api, sources, invocation):
    no_symlink_path(WORKSPACE)
    case = fixed_case()
    selection = {'order_operation_key': args.operation_key,
        'translation_operation_key': args.translation_operation_key,
        'registry_ref': args.registry_ref, 'resource_id': args.resource_id}
    if WORKSPACE.exists() and not SELECTION_FILE.exists():
        raise ValueError('preexisting_workspace_not_owned_by_this_verification')
    same_or_save(SELECTION_FILE, {'caller_selection': selection,
        'sources': sources, 'workspace': str(WORKSPACE)})
    if BINDING_FILE.exists() and read_json(BINDING_FILE)['caller_selection'] != selection:
        raise ValueError('one_original_engineering_job_selection_required')
    if WORKSPACE.exists():
        seed = read_json(WORKSPACE/'fixed-target-seed.json')
        seed_origin = 'reopened_original_retained_seed'
    else:
        seed = api['prepare_seed'](case_directory=CASE, source_workspace=WITNESS,
            destination_workspace=WORKSPACE)
        seed_origin = 'prepared_by_public_exact_seed_helper'
    qualify_seed(seed, case)
    save_new(invocation/'seed.json', {'origin': seed_origin, 'receipt': seed})
    client, client_binding = actual_client(api)
    registry = {'version': 'public_search_registry_v1', 'registry_ref': args.registry_ref,
        'resource_id': args.resource_id, 'provider': 'hmmer',
        'client_binding_sha256': api['client_digest'](client)}
    # Store is constructed only on the newly declared destination, never WITNESS.
    with api['Store'](WORKSPACE) as store:
        if store.problem()['id'] != seed['fixed_identity']['problem_ref']:
            raise ValueError('seed_problem_changed')
        scope = store.validate_scope({'subject_refs': [seed['fixed_identity']['target_ref']]})
        tools, ports = ports_for(api, store, client, registry)
        translation_args = {'subject_ref': seed['fixed_identity']['target_ref'],
            'code': case['translation_table'], 'strand': '+', 'frame': 0,
            'start': 0, 'end': case['dna_length_nt'], 'cds': True}
        translation = tools.execute('sequence.translate', translation_args,
            scope=scope, operation_key=args.translation_operation_key)
        save_new(invocation/'translation.json', {'arguments': translation_args, 'outcome': translation})
        if translation['status'] not in {'completed', 'partial'}:
            raise ValueError('translation_not_completed')
        records = translation['result']['records']
        if len(records) != 1:
            raise ValueError('one_actual_translated_product_required')
        product_ref = records[0]['product_ref']
        product = store.get(product_ref)
        protein = store.get_artifact(product['sequence_ref'])
        if len(protein) != 253 or sha(protein) != PROTEIN_SHA256:
            raise ValueError('exact_P0AAW1_translation_witness_mismatch')
        fasta = '>'+product_ref+'\n'+ports.sequence_symbols(product_ref, scope=scope)
        order = ports.operations.order(operation_key=args.operation_key, provider='hmmer',
            subject_ref=product_ref, query_fasta=fasta, algorithm='phmmer', database='pdb',
            parameters={}, page_size=2, scope=scope)
        inspected = ports.operations.inspect(order['job_ref'])
        binding = {'version': 'explicit_hmmer_service_verification_v1',
            'checkout': str(CHECKOUT), 'workspace': str(WORKSPACE),
            'sources': sources, 'caller_selection': selection, 'seed': seed,
            'seed_receipt_sha256': sha((WORKSPACE/'fixed-target-seed.json').read_bytes()),
            'client_binding': client_binding, 'registry': registry, 'local_limits': LIMITS,
            'scope': scope, 'translation_arguments': translation_args,
            'translation_outcome': translation, 'product_ref': product_ref,
            'product_record': product, 'protein_sha256': sha(protein), 'protein_length': len(protein),
            'submitted_fasta_sha256': sha(fasta.encode()), 'order': order,
            'order_scope': ports.operations.open_scope(order['job_ref']), 'request': inspected['request']}
        same_or_save(BINDING_FILE, binding)
        return {'binding': binding, 'original_job_inspection': inspected}


async def selected_phase(args, api, binding, invocation):
    client, described = actual_client(api)
    if described != binding['client_binding'] or binding['local_limits'] != LIMITS:
        raise ValueError('original_effective_client_configuration_required')
    with open_selected(api, binding, client) as store:
        _, ports = ports_for(api, store, client, binding['registry'])
        verify_original_order(store, ports, binding)
        job = binding['order']['job_ref']
        before = ports.operations.inspect(job)
        save_new(invocation/'before.json', before)
        try:
            if args.phase == 'submit_once':
                outcome = await ports.operations.submit_once(job, operation_key=args.operation_key,
                    retry_of=None)
            elif args.phase == 'recover_submission':
                outcome = ports.operations.recover_submission(job, operation_key=args.operation_key)
            elif args.phase == 'status_once':
                outcome = await ports.operations.status_once(job, operation_key=args.operation_key)
            elif args.phase == 'result_once':
                outcome = await ports.operations.result_once(job, operation_key=args.operation_key,
                    page=args.page, page_size=2)
            else:
                receipt = ports.operations.read_operation(args.receipt_ref)
                if receipt['job_ref'] != job:
                    raise ValueError('publication_receipt_for_original_job_required')
                outcome = ports.result_publisher.publish(args.receipt_ref, scope=binding['scope'],
                    operation_key=args.operation_key)
        finally:
            # This is a pure original-job read, including failed/in-progress
            # delivery; it neither refreshes remote status nor creates a receipt.
            save_new(invocation/'after.json', ports.operations.inspect(job))
        save_new(invocation/'selected-outcome.json', outcome)
        return {'outcome': outcome, 'original_job_inspection': ports.operations.inspect(job)}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-runtime-pin', required=True)
    parser.add_argument('--operation-key', required=True)
    commands = parser.add_subparsers(dest='phase', required=True)
    prepare = commands.add_parser('prepare-order')
    prepare.add_argument('--translation-operation-key', required=True)
    prepare.add_argument('--registry-ref', required=True)
    prepare.add_argument('--resource-id', required=True)
    commands.add_parser('submit_once')
    commands.add_parser('recover_submission', help='Explicit no-network recovery of the same original job')
    commands.add_parser('status_once')
    result = commands.add_parser('result_once')
    result.add_argument('--page', required=True, type=int)
    publish = commands.add_parser('publish')
    publish.add_argument('--receipt-ref', required=True)
    args = parser.parse_args()
    for key in ('operation_key', 'translation_operation_key', 'registry_ref', 'resource_id', 'receipt_ref'):
        if hasattr(args, key) and not getattr(args, key).strip():
            parser.error('nonempty explicit '+key+' required')
    if args.phase == 'result_once' and args.page < 1:
        parser.error('positive explicit page required')
    return args


def main():
    args = arguments()
    sources, api = pin_and_import(args.expected_runtime_pin)
    no_symlink_path(EVIDENCE)
    if Path(__file__).resolve() != EVIDENCE/'verify_hmmer_service.py':
        raise ValueError('declared_verification_script_path_required')
    invocation = EVIDENCE/'invocations'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex)
    intent = {'version': 'explicit_verification_phase_v1', 'selected_at': now(),
        'arguments': vars(args), 'sources': sources, 'workspace': str(WORKSPACE),
        'script_sha256': sha(Path(__file__).read_bytes()),
        'meaning': 'Engineering interface verification; no scientific conclusion or episode credit.'}
    save_new(invocation/'intent.json', intent)
    try:
        if args.phase == 'prepare-order':
            result = prepare_order(args, api, sources, invocation)
        else:
            binding = read_json(BINDING_FILE)
            if binding['sources'] != sources:
                raise ValueError('original_saved_implementation_required')
            qualify_seed(binding['seed'], fixed_case())
            result = asyncio.run(selected_phase(args, api, binding, invocation))
        save_new(invocation/'result.json', {'finished_at': now(), 'result': result})
        print(canonical({'evidence_directory': str(invocation), 'result': result}))
    except BaseException as error:
        failure = {'finished_at': now(), 'exception_type': type(error).__name__,
            'code': getattr(error, 'code', None), 'detail': str(error),
            'failure': getattr(error, 'failure', None), 'structured_detail': getattr(error, 'detail', None)}
        save_new(invocation/'failure.json', failure)
        raise
    finally:
        after = source_identity()
        save_new(invocation/'sources-after.json', {'identity': after, 'unchanged': after == sources})


if __name__ == '__main__':
    main()
