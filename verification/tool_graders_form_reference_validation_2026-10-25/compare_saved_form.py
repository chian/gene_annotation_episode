"""Validate a complete original saved form with real custody on a private copy."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('variant', choices=('baseline', 'candidate', 'candidate-original-backend'))
parser.add_argument('case', choices=('genome', 'msa'))
parser.add_argument('--checks', action='store_true')
args = parser.parse_args()
EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
IMPORT = EVIDENCE / 'candidate' if args.variant == 'candidate' else ROOT
sys.path[:0] = [str(IMPORT), str(IMPORT / 'tests')]

import pytest
import gene_annotation_episode.communication as communication
from gene_annotation_episode.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.bvbrc_appservice_custody import _references
from test_genome_alignment_saved_structure import scientific_barrier
from test_bvbrc_alignment_episode_flow import block_saved_scientific_work
from test_public_search import Client

assert Path(communication.__file__).resolve().is_relative_to(IMPORT / 'gene_annotation_episode')
ORIGINAL = (ROOT / 'verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/runs/mauve-v4-d00v9ick'
    if args.case == 'genome' else ROOT / 'verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/runs/msa_dna-no78l7n3')
# Freeze one common input snapshot, then use disjoint copies for each process.
BASE = EVIDENCE / ('input-' + args.case)
if not BASE.exists():
    BASE.mkdir()
    (BASE / 'state').mkdir()
    with sqlite3.connect(f'file:{ORIGINAL / "state/state.sqlite3"}?mode=ro', uri=True) as source:
        with sqlite3.connect(BASE / 'state/state.sqlite3') as destination:
            source.backup(destination)
    for name in ('state/artifacts', 'run'):
        shutil.copytree(ORIGINAL / name, BASE / name)
    shutil.copy2(ORIGINAL / 'CONFIGURED_BINDINGS.json', BASE / 'CONFIGURED_BINDINGS.json')
snapshot = EVIDENCE / (args.variant + '-' + args.case + ('-checks' if args.checks else ''))
shutil.copytree(BASE, snapshot)
label = snapshot.name

def hashes():
    return {str(path.relative_to(snapshot)): hashlib.sha256(path.read_bytes()).hexdigest()
        for base in (snapshot / 'run', snapshot / 'state/artifacts')
        for path in base.rglob('*') if path.is_file()}

def forbidden(*_, **__):
    raise AssertionError('scientific or network work during saved form validation')

configuration = next(row['configuration'] for row in json.loads((BASE / 'CONFIGURED_BINDINGS.json').read_text())
    ['configured_episode_bindings'] if row['binding_id'] == 'execution_episodes')
receipt = {'variant': args.variant, 'case': args.case, 'original_run': str(ORIGINAL),
    'private_copy': str(snapshot), 'imported_communication': communication.__file__,
    'started_at': datetime.now(timezone.utc).isoformat(), 'profiled': False,
    'new_workflow_or_native_execution': False, 'checks': [], 'status': 'running'}
receipt_path = EVIDENCE / (label + '.json')

def write():
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')

with Store(snapshot / 'state') as store:
    row = store.db.execute("SELECT run_id,episode_id,state FROM runtime_episodes "
        "WHERE json_extract(path,'$[#-1][0]')='results'").fetchone()
    assert row['state'] == 'yielded'
    family = ExecutionEpisodes(None, store=store, run_id=row['run_id'], directory=snapshot / 'run',
        tool_registry=ToolRegistry(store, clients=Client()), **configuration)
    if args.variant == 'candidate-original-backend':
        # The backend's configured scientific implementation remains original.
        # This diagnostic installs only the candidate consumer, explicitly; it
        # never changes a hash, source result or authentication implementation.
        import importlib.util
        def load(name, filename):
            path = EVIDENCE / 'candidate/gene_annotation_episode' / filename
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            return module
        load('gene_annotation_episode.form_reference_validation', 'form_reference_validation.py')
        frontend = load('gene_annotation_episode._candidate_communication', 'communication.py')
        returns = load('gene_annotation_episode._candidate_genome_returns', 'bvbrc_genome_alignment_returns.py')
        validate_form = frontend.validate_form
        family.api_execution.genome_alignment_returns = returns.BVBRCGenomeAlignmentReturns(family.api_execution)
        receipt['instrumented_consumer'] = {'communication': frontend.__file__, 'returns': returns.__file__,
            'backend': str(ROOT), 'full_candidate_workflow': False,
            'changed_original_pins_or_authentication': False}
    store.db.execute('PRAGMA query_only=ON')
    provider = getattr(family.api_execution, 'genome_alignment_returns' if args.case == 'genome' else 'alignment_returns')
    context = family.api_execution.appservice.custody.context(row['episode_id'])
    form = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',
                                     (context.episode_id,)).fetchone()[0])
    schema = plain(context.request)['report_contract']['measurements']['schema']
    tables = ('runtime_actions', 'runtime_observations', 'runtime_model_calls',
              'runtime_report_attempts', 'runtime_record_receipts')
    counts = lambda: {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables}
    before_counts, before_hashes = counts(), hashes()
    receipt.update(original_form_sha256=digest(form), original_schema_sha256=digest(schema),
        reference_occurrences=len(list(_references(form, schema))), counts_before=before_counts)
    calls = Counter()
    original_facts, original_received = provider.facts, provider.received_context
    def counted_facts(ctx, requested):
        calls['facts:' + ctx.episode_id] += 1
        return original_facts(ctx, requested)
    def counted_received(ctx):
        calls['received:' + ctx.episode_id] += 1
        return original_received(ctx)
    def timed(name, callback):
        old = calls.copy()
        start, cpu = time.monotonic(), time.process_time()
        value = callback()
        result = {'name': name, 'wall_seconds': time.monotonic() - start,
            'cpu_seconds': time.process_time() - cpu, 'factory_calls': dict(calls - old)}
        receipt['checks'].append(result)
        write()
        print(json.dumps(result), flush=True)
        return value
    write()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(provider, 'facts', counted_facts)
        patch.setattr(provider, 'received_context', counted_received)
        blocked = scientific_barrier(patch)
        alignment_blocked = block_saved_scientific_work(patch, forbidden)
        receipt['blocked_scientific_aliases'] = list(blocked) + alignment_blocked
        resolver = lambda ref, ns: family.resolve(context, ref, ns)
        assert timed('complete_original_form', lambda: validate_form(form, schema, resolver)) == form
        if args.variant != 'baseline':
            assert calls['facts:' + context.episode_id] == 1
        if args.checks:
            assert timed('second_form_reauthenticates', lambda: validate_form(form, schema, resolver)) == form
            assert calls['facts:' + context.episode_id] == 2
            ref, ns = next((ref, ns) for ref, ns in _references(form, schema)
                          if ns.endswith('_field'))
            assert timed('direct_resolve_first', lambda: family.resolve(context, ref, ns)) is True
            assert timed('direct_resolve_second', lambda: family.resolve(context, ref, ns)) is True
            assert calls['facts:' + context.episode_id] == 4
            # Generic reference validation cannot establish numerical truth.
            # The unchanged semantic stage must still reject an altered value.
            forged = deepcopy(form)
            if args.case == 'genome':
                forged['numbers'][0]['value']['value']['value'] += 1
            else:
                forged['numbers'][0]['value']['value'] += 1
            def reject_forged():
                with pytest.raises(ValueError):
                    provider.validate_received_report(context, forged, schema)
            timed('semantic_stage_rejects_forged_number', reject_forged)
            parent_row = store.db.execute("SELECT episode_id FROM runtime_episodes "
                "WHERE json_extract(path,'$[#-1][0]')='scientific_process'").fetchone()
            parent = family.api_execution.appservice.custody.context(parent_row['episode_id'])
            saved_parent = store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',
                                           (parent.episode_id,)).fetchone()
            if saved_parent is not None and saved_parent['form'] is not None:
                parent_form = json.loads(saved_parent['form'])
                parent_schema = plain(parent.request)['report_contract']['measurements']['schema']
                parent_resolver = lambda ref, ns: family.resolve(parent, ref, ns)
                old = calls['received:' + parent.episode_id]
                assert timed('complete_received_form', lambda: validate_form(
                    parent_form, parent_schema, parent_resolver)) == parent_form
                assert calls['received:' + parent.episode_id] == old + 1
            else:
                receipt['received_form_check'] = 'pending original parent closure; not claimed'
    receipt.update(counts_after=counts(), immutable_files_unchanged=hashes() == before_hashes,
        query_only=store.db.execute('PRAGMA query_only').fetchone()[0] == 1)
    assert receipt['counts_after'] == before_counts and receipt['immutable_files_unchanged']
    receipt['status'] = 'passed'
    write()
    print(json.dumps({'status': 'passed', 'receipt': str(receipt_path)}), flush=True)
