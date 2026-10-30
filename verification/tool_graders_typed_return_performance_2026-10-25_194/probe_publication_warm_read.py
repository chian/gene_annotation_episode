"""One complete original publication read with a no-write effect-lock facade.

Concurrency limitation: the probe deliberately takes no live effect lock. Every
read file is hashed on first access and again at completion; concurrent changes
would invalidate the claimed input equality. No lock or directory is created.
The original _job/_all/_intent/_state methods and all semantic checks execute.
"""
from __future__ import annotations

import ast
from collections import Counter
from contextlib import closing, contextmanager
import cProfile
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import pstats
import sqlite3
import sys
import time

sys.dont_write_bytecode = True
from probe_saved_validation import ROOT, OWN, BASE, CANDIDATE, digest, records
from gene_annotation_episode import communication, bvbrc_appservice_custody
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects
from gene_annotation_episode.bvbrc_appservice_host import BVBRCAppServiceHost
from gene_annotation_episode.bvbrc_proteome_returns import BVBRCProteomeReturns
from gene_annotation_episode.bvbrc_appservice_custody import _references
from gene_annotation_episode.bvbrc_proteome_bundle_adapter_v2 import implementation_sha256
from gene_annotation_episode.execution_contracts import digest as contract_digest
from gene_annotation_episode.state import Store


class NoWriteProbeEffects(SelectedAPIEffects):
    @contextmanager
    def _locked(self, owner):
        # Only replace filesystem creation/locking. _job validates the owner;
        # inherited read invokes _all -> _intent -> _state exactly as before.
        directory = self._job(owner)
        if not directory.is_dir():
            raise ValueError('probe_original_effect_directory_missing')
        self.probe_lock_entries += 1
        yield directory


def main():
    directory = (BASE / 'final_workflow_001/temporary/test_actual_selected_tool_shar0').resolve()
    output = OWN / 'publication_warm_probe_001'
    output.mkdir()
    evidence = {'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'input_directory': str(directory),
        'scope': 'A cold priming read followed by one same-process warm AppServicePublications.read, no Workflow/native run',
        'concurrency_limitation': 'Probe replaces only SelectedAPIEffects._locked with no-write/no-lock context; every opened input file is checked unchanged afterward',
        'sqlite_uri': (directory / 'state/state.sqlite3').as_uri() + '?mode=ro'}
    (output / 'command.json').write_text(json.dumps(evidence, indent=2) + '\n')
    source_files = [Path(__file__), OWN / 'probe_saved_validation.py',
                    CANDIDATE / 'tests/test_api_bvbrc_appservice.py',
                    CANDIDATE / 'tests/test_bvbrc_proteome_directional_episode_path.py',
                    *(CANDIDATE / 'gene_annotation_episode').rglob('*.py'),
                    *(CANDIDATE / 'gene_annotation_episode').rglob('*.json')]
    def source_hashes():
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(source_files))}
    evidence['source_hashes_before'] = source_hashes()
    frozen_test = CANDIDATE / 'tests/test_api_bvbrc_appservice.py'
    config = next(ast.literal_eval(node.value) for node in ast.parse(frozen_test.read_text()).body
                  if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'CONFIG'
                                                         for target in node.targets))
    config['scientific_adapters'] = [{'adapter_id': 'bvbrc_proteome', 'adapter_version': '2',
                                     'implementation_sha256': implementation_sha256()}]
    evidence['configuration'] = {'selected-api': config}
    evidence['configuration_origin'] = 'Exact CONFIG literal and v2 adapter binding from frozen Workflow test constructor'
    file_before, schema_calls = {}, []
    active, inside_hash = False, False

    def audit(event, args):
        nonlocal inside_hash
        if not active or inside_hash:
            return
        if event.startswith('socket.'):
            raise RuntimeError('probe_network_forbidden')
        if event == 'open':
            value, mode, flags = args
            if not isinstance(value, (str, bytes, os.PathLike)):
                return
            path = Path(os.fsdecode(value)).resolve()
            writes = isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writes and not path.is_relative_to(output):
                raise RuntimeError('probe_external_write_forbidden')
            if not writes and path.is_relative_to(directory) and path.is_file() and str(path) not in file_before:
                inside_hash = True
                try:
                    file_before[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
                finally:
                    inside_hash = False
        if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.truncate', 'os.link', 'os.symlink'}:
            path = Path(os.fsdecode(args[0])).resolve()
            if not path.is_relative_to(output):
                raise RuntimeError('probe_external_mutation_forbidden')

    sys.addaudithook(audit)
    original_schema = communication.validate_closed_schema
    def counted_schema(schema):
        key = digest(communication.plain(schema))
        caller = inspect.currentframe().f_back
        location = f'{Path(caller.f_code.co_filename).name}:{caller.f_code.co_name}:{caller.f_lineno}'
        start = time.perf_counter()
        try:
            return original_schema(schema)
        finally:
            schema_calls.append({'sha256': key, 'caller': location, 'seconds': time.perf_counter() - start})
    communication.validate_closed_schema = counted_schema
    bvbrc_appservice_custody.validate_closed_schema = counted_schema
    with closing(sqlite3.connect(evidence['sqlite_uri'], uri=True)) as db:
        db.row_factory = sqlite3.Row
        store = object.__new__(Store)
        store.path, store.db = directory / 'state', db
        before = records(db)
        evidence['input_records_before_sha256'] = digest(before)
        run_id = before['runtime_episodes'][0]['run_id']
        api = object.__new__(APIServiceExecution)
        api.store, api.run_id = store, run_id
        api.directory = directory / 'run/api-service-execution' / contract_digest(run_id)
        api.configuration = evidence['configuration']
        api.legacy, api.services = None, {}
        api.selected_effects = NoWriteProbeEffects(directory / 'run', run_id=run_id)
        api.selected_effects.probe_lock_entries = 0
        api.appservice = BVBRCAppServiceHost(api)
        api.proteome_returns = BVBRCProteomeReturns(api)
        episode = next(row for row in before['runtime_episodes'] if json.loads(row['path'])[-1][0] == 'results')
        selected = next(row for row in before['runtime_forms'] if row['episode_id'] == episode['episode_id'])
        schema = json.loads(episode['request'])['report_contract']['measurements']['schema']
        form = json.loads(selected['form'])
        reference = next(row[0]['source_ref'] for row in form.values() if isinstance(row, list) and row and isinstance(row[0], dict) and 'source_ref' in row[0])
        evidence.update(result_reference=reference, episode_id=episode['episode_id'],
                        input_form_sha256=digest(form), input_schema_sha256=digest(schema))
        from gene_annotation_episode import bvbrc_appservice_contracts as contracts
        cache_counts = Counter()
        original_cache_lookup = contracts._already_validated
        def counted_cache_lookup(key):
            hit = original_cache_lookup(key)
            name = inspect.currentframe().f_back.f_locals.get('name', 'unknown')
            cache_counts[(name, hit)] += 1
            return hit
        contracts._already_validated = counted_cache_lookup
        active = True
        warmup_start = time.perf_counter()
        warmup = api.appservice.publications.read(reference,
            json.loads(episode['request'])['message']['scope'], episode_id=episode['episode_id'])
        evidence['cold_priming_seconds_unprofiled'] = time.perf_counter() - warmup_start
        evidence['cold_priming_cache_checks'] = [{'contract': name, 'hit': hit, 'count': count}
            for (name, hit), count in cache_counts.items()]
        evidence['cold_priming_schema_counts'] = dict(Counter(row['sha256'] for row in schema_calls))
        evidence['cold_priming_schema_validation_seconds'] = sum(row['seconds'] for row in schema_calls)
        schema_calls.clear()
        cache_counts.clear()
        api.selected_effects.probe_lock_entries = 0
        profiler = cProfile.Profile()
        start = time.perf_counter()
        active = True
        try:
            result = profiler.runcall(api.appservice.publications.read, reference,
                                     json.loads(episode['request'])['message']['scope'], episode_id=episode['episode_id'])
            evidence.update(terminal_status='completed', result_sha256=digest(result),
                            original_publication_origin=result['publication']['origin'])
        except Exception as error:
            evidence.update(terminal_status='failed', exception_type=type(error).__name__, exception=str(error))
        finally:
            evidence['seconds'] = time.perf_counter() - start
            active = False
        profiler.dump_stats(str(output / 'publication.prof'))
        stats = pstats.Stats(profiler)
        evidence['function_counts'] = [{'file': key[0], 'line': key[1], 'function': key[2],
             'primitive_calls': row[0], 'total_calls': row[1], 'own_seconds': row[2], 'cumulative_seconds': row[3]}
             for key,row in stats.stats.items() if str(CANDIDATE) in key[0] and key[2] in {
                 'read','read_handoff','read_target','_origin','_native','_commission','authenticate',
                 '_possession','_attempt','_content','_validate_inputs','validate_closed_schema','validate_form',
                 '_job','_all','_intent','_state'}]
        with (output / 'publication.txt').open('w') as stream:
            pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(70)
        evidence['warm_equals_cold_result'] = evidence.get('result_sha256') == digest(warmup)
        evidence['warm_cache_checks'] = [{'contract': name, 'hit': hit, 'count': count} for (name, hit), count in cache_counts.items()]
        evidence['schema_calls'] = schema_calls
        evidence['schema_counts'] = dict(Counter(row['sha256'] for row in schema_calls))
        evidence['schema_validation_seconds'] = sum(row['seconds'] for row in schema_calls)
        evidence['probe_effect_lock_entries'] = api.selected_effects.probe_lock_entries
        evidence['input_file_hashes_before'] = file_before
        evidence['input_file_hashes_after'] = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in file_before}
        evidence['input_files_equal'] = evidence['input_file_hashes_before'] == evidence['input_file_hashes_after']
        after = records(db)
        evidence['input_records_after_sha256'] = digest(after)
        evidence['input_records_equal'] = before == after
        evidence['source_hashes_after'] = source_hashes()
        evidence['source_hashes_equal'] = evidence['source_hashes_before'] == evidence['source_hashes_after']
    evidence['finished_at'] = datetime.now(timezone.utc).isoformat()
    (output / 'receipt.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({key: evidence[key] for key in ('terminal_status','seconds','input_files_equal','input_records_equal',
              'source_hashes_equal','schema_validation_seconds','schema_counts','probe_effect_lock_entries')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
