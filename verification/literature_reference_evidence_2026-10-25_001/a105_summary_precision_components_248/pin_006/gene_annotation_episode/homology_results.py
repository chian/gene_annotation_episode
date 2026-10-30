"""Ordinary results-acquisition tool: bounded parsing, canonical facts, paging.

The parent still integrates scientific interpretations. Numerical native-tool
components extend the existing observations; no annotation score or additional
action is created. Input paths are infrastructure-owned, never child form fields.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from importlib.metadata import version

from ._local_job_worker import atomic_json
from .acquisition import AcquisitionError
from .domain import ContractError, canonical
from .homology_jobs import digest
from .local_jobs import LocalJobPolicy, run_cancellable_native
from .materials import artifact_file, artifact_path
from .native_lifecycle import NativeJobHandle, resume_start, start_job, wait_job
from .phmmer_format import VERSION
from .phmmer_grading_worker import VERSION as GRADING_VERSION
from .hmmer_graders import HMMER_DOMAIN_METRICS
from .tool_grading_artifacts import retain_tool_grading, source_tool_gradings


@dataclass(frozen=True)
class NativePhmmerInput:
    query_ref: str
    query_fasta: Path
    reference_fasta: Path
    native_text: Path
    hit_table: Path
    database_sha256: str
    executable_sha256: str
    provenance: dict
    domain_table: Path | None = None

    @classmethod
    def from_job(cls, jobs, handoff):
        jobs.receive(handoff)
        job = jobs._row(handoff['job_ref'])
        directory = jobs._directory(handoff['job_ref'])
        handle = jobs._handle(handoff['job_ref']).read()
        return cls(job['query_ref'], directory/'query.faa', directory/'references.faa',
            jobs.result_file(handoff, 'native_text'), directory/'hits.tbl',
            jobs.config['reference_database']['sha256'], jobs.config['executable']['sha256'],
            {'job_ref': handoff['job_ref'], 'registry_ref': handoff['registry_ref'],
             'native_handle': handle,
             'native_parameters': {'command': handle['command'], 'cpu': job['cpu'],
                                   'search_mode': job['search_mode']}}, directory/'domains.tbl')


def _parse(directory, request, policy, *, cancel_event=None):
    outcome_path = directory/'parse_outcome.json'
    if outcome_path.is_file():
        return json.loads(outcome_path.read_text())
    handle = NativeJobHandle(directory/'parser.handle.json')
    try:
        if not handle.path.exists():
            atomic_json(directory/'request.json', request)
            environment = {'PYTHONPATH': str(Path(__file__).resolve().parent.parent)+os.pathsep+os.environ.get('PYTHONPATH', '')}
            start_job([sys.executable, '-m', 'gene_annotation_episode.phmmer_result_worker', str(directory/'request.json')],
                cwd=directory, policy=policy, handle_path=handle.path, env=environment,
                stdout_path=directory/'parser.stdout', stderr_path=directory/'parser.stderr', cancel_event=cancel_event)
        else:
            resume_start(handle, cancel_event=cancel_event)
        result = wait_job(handle, cancel_event=cancel_event)
        failure = None if result.returncode == 0 else {'code': 'phmmer_parser_nonzero_exit', 'native_returncode': result.returncode}
        if failure and (directory/'failure.json').is_file():
            failure.update(json.loads((directory/'failure.json').read_text()))
        outcome = {'native': result.metadata, 'failure': failure}
    except AcquisitionError as error:
        outcome = {'native': error.operational, 'failure': {'code': error.code, 'phase': error.phase,
                                                         'resource': (error.operational or {}).get('resource')}}
    atomic_json(outcome_path, outcome)
    return outcome


def _execution_context(provenance):
    """Only actual physical-job identities constrain job-bound captures."""
    keys = ('job_ref', 'registry_ref')
    if provenance is None:
        return None
    if not isinstance(provenance, dict):
        raise ContractError('native_result_requires_complete_execution_context')
    if not any(key in provenance for key in keys):
        return None
    if any(type(provenance.get(key)) is not str or not provenance[key] for key in keys):
        raise ContractError('native_result_requires_complete_execution_context')
    return {key: provenance[key] for key in keys}


def _termination_seen(path):
    """Retained one-query output contains its query/program terminators."""
    terminated, completed, continued = False, False, False
    with path.open('rb') as stream:
        while chunk := stream.readline(65536):
            full_line = not continued and (chunk.endswith(b'\n') or len(chunk) < 65536)
            continued = not chunk.endswith(b'\n')
            if full_line:
                line = chunk.strip()
                completed = completed or terminated and line == b'[ok]'
                terminated = terminated or line == b'//'
    return completed


def _error_counts(db):
    """A calculator failure cannot change observed native completion facts."""
    total, grading = db.execute("SELECT count(*),coalesce(sum("
        "json_extract(data,'$.phase')='tool_grading'),0) FROM errors").fetchone()
    return total-grading, grading


def _parse_inventory(directory):
    """Freeze what this completed parser attempt actually committed."""
    path = directory/'measurements.sqlite'
    if not path.is_file():
        return {'parsed_row_count': None, 'native_error_count': None, 'grading_error_count': None,
                'parser_finished': False}
    db = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True)
    try:
        rows = db.execute('SELECT count(*) FROM measurements').fetchone()[0]
        errors, grading_errors = _error_counts(db)
    except sqlite3.Error:
        return {'parsed_row_count': None, 'native_error_count': None, 'grading_error_count': None,
                'parser_finished': False}
    finally:
        db.close()
    summary_path = directory/'summary.json'
    try:
        summary = json.loads(summary_path.read_text()) if summary_path.is_file() else None
    except (ValueError, OSError):
        summary = None
    return {'parsed_row_count': rows, 'native_error_count': errors, 'grading_error_count': grading_errors,
        'parser_finished': bool(isinstance(summary, dict) and summary.get('version') == GRADING_VERSION
            and summary.get('rows') == rows and summary.get('errors') == errors+grading_errors)}


def _snapshot(store, snapshot_ref, *, query_ref, scope, execution_context):
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone() is None:
        raise ContractError('native_result_snapshot_does_not_resolve_for_query')
    saved = store.db.execute('SELECT * FROM homology_result_snapshots WHERE source_ref=? AND query_ref=?',
        (snapshot_ref, query_ref)).fetchone()
    if saved is None:
        raise ContractError('native_result_snapshot_does_not_resolve_for_query')
    store.validate_scope(scope)
    if store.roots(query_ref) and not store.scope_covers(store.coverage(query_ref), scope):
        raise ContractError('homology_query_outside_assigned_scope')
    snapshot = json.loads(saved['body'])
    # This is the retained capture's source, never today's physical output.
    source = store.get(snapshot['execution_source_ref'])
    with artifact_path(store, source['artifact_ref']).open() as stream:
        actual_context = _execution_context(json.load(stream))
    if actual_context != _execution_context(execution_context):
        raise ContractError('native_result_snapshot_execution_context_mismatch')
    return saved, snapshot, actual_context


def _native_complete(snapshot):
    inventory = snapshot.get('parse_inventory', {})
    errors = inventory.get('native_error_count')
    terminated = snapshot.get('native_termination_seen')
    if snapshot['parse_execution']['failure'] or errors or terminated is False:
        return False
    if inventory.get('parser_finished') is True and terminated is True and errors == 0:
        return True
    return None


def recorded_coverage(store, snapshot_ref, *, query_ref, scope, execution_context=None):
    """Read captured parse facts and published native ordinals, without work.

    Native ordinals start at one; intervals are [start, end). Acquiring all
    parsed rows can include only a valid prefix of an incomplete native set.
    Historical snapshots without captured inventory keep unknowns as null.
    """
    _, snapshot, actual_context = _snapshot(store, snapshot_ref, query_ref=query_ref, scope=scope,
        execution_context=execution_context)
    intervals, acquired = None, None
    if snapshot.get('publication_witness_version') == 'native_row_publication_v1':
        intervals, acquired = [], 0
        for (ordinal,) in store.db.execute(
                'SELECT ordinal FROM homology_result_witnesses WHERE snapshot_ref=? ORDER BY ordinal', (snapshot_ref,)):
            acquired += 1
            if intervals and intervals[-1][1] == ordinal:
                intervals[-1][1] += 1
            else:
                intervals.append([ordinal, ordinal+1])
    inventory = snapshot.get('parse_inventory', {})
    parsed = inventory.get('parsed_row_count')
    errors = inventory.get('native_error_count')
    finished = inventory.get('parser_finished')
    terminated = snapshot.get('native_termination_seen')
    failure = snapshot['parse_execution']['failure']
    return {'snapshot_ref': snapshot_ref, 'query_ref': query_ref,
        'execution_source_ref': snapshot['execution_source_ref'], 'native_source_ref': snapshot['native_source_ref'],
        'execution_context': actual_context, 'status': 'available' if parsed is not None else 'unavailable',
        'parsed_row_count': parsed, 'acquired_row_count': acquired, 'acquired_ordinal_intervals': intervals,
        'all_parsed_rows_acquired': acquired == parsed if parsed is not None and acquired is not None else None,
        'parser_finished': finished, 'native_error_count': errors, 'parse_execution_failure': failure,
        'native_termination_seen': terminated, 'native_result_complete': _native_complete(snapshot)}


class HomologyResults:
    def __init__(self, store, *, policy: LocalJobPolicy):
        self.store, self.policy = store, policy
        store.db.executescript('''
        CREATE TABLE IF NOT EXISTS homology_result_snapshots (
            source_ref TEXT PRIMARY KEY REFERENCES records(id),signature TEXT NOT NULL,
            query_ref TEXT NOT NULL,directory TEXT NOT NULL,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS homology_parse_cache (
            signature TEXT PRIMARY KEY,directory TEXT NOT NULL,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS homology_measurements (
            measurement_key TEXT PRIMARY KEY,observation_ref TEXT NOT NULL REFERENCES records(id));
        CREATE TABLE IF NOT EXISTS homology_reference_bindings (
            binding_key TEXT PRIMARY KEY,reference_ref TEXT NOT NULL REFERENCES records(id));
        CREATE TABLE IF NOT EXISTS homology_result_witnesses (
            snapshot_ref TEXT NOT NULL REFERENCES records(id),ordinal INTEGER NOT NULL CHECK(ordinal>0),
            record_ref TEXT NOT NULL REFERENCES records(id),record_type TEXT NOT NULL,
            source_byte_spans TEXT NOT NULL,PRIMARY KEY(snapshot_ref,ordinal));
        CREATE INDEX IF NOT EXISTS homology_result_witness_records ON homology_result_witnesses(record_ref);
        ''')

    def _source(self, provider, body, *, parents=(), operands=(), artifact=None,
                tool_grading=None, parser_version=VERSION):
        request = self.store.artifact(canonical(body), 'application/json') if artifact is not None else None
        artifact = artifact or self.store.artifact(canonical(body), 'application/json')
        auxiliary = ([retain_tool_grading(self.store, provider=provider,
            native_artifact_ref=artifact, grading=tool_grading)] if tool_grading is not None else [])
        return self.store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request, 'version': parser_version,
            'retrieved_at': None, 'parent_source_refs': list(parents), 'operand_refs': list(operands),
            **({'auxiliary_artifact_refs': auxiliary} if auxiliary else {})}, origin='tool')

    def _snapshot(self, snapshot_ref, *, query_ref, scope, execution_context):
        return _snapshot(self.store, snapshot_ref, query_ref=query_ref, scope=scope,
            execution_context=execution_context)

    def coverage(self, snapshot_ref, *, query_ref, scope, execution_context=None):
        return recorded_coverage(self.store, snapshot_ref, query_ref=query_ref, scope=scope,
            execution_context=execution_context)

    def _publication(self, snapshot_ref, ordinal, record_ref, record_type, row, snapshot):
        spans = []
        for key, role, artifact_key in (('source_byte_span', 'native_text', 'native_text_artifact'),
                ('text_byte_span', 'native_text', 'native_text_artifact'),
                ('table_byte_span', 'hit_table', 'hit_table_artifact')):
            if key in row:
                spans.append({'role': role, 'artifact_ref': snapshot[artifact_key], 'byte_span': row[key]})
        value = {'ordinal': ordinal, 'record_ref': record_ref, 'record_type': record_type, 'source_byte_spans': spans}
        encoded = canonical(spans)
        existing = self.store.db.execute('SELECT record_ref,record_type,source_byte_spans FROM homology_result_witnesses '
            'WHERE snapshot_ref=? AND ordinal=?', (snapshot_ref, ordinal)).fetchone()
        if existing is not None and tuple(existing) != (record_ref, record_type, encoded):
            raise ContractError('native_result_publication_witness_changed')
        self.store.db.execute('INSERT OR IGNORE INTO homology_result_witnesses VALUES(?,?,?,?,?)',
            (snapshot_ref, ordinal, record_ref, record_type, encoded))
        return value

    async def prepare(self, inputs, scope, *, retry_from=None, attempt_key=None):
        if self.store.db.in_transaction:
            raise ContractError('native_result_work_requires_no_active_store_transaction')
        execution_context = _execution_context(inputs.provenance)
        query = self.store.get(inputs.query_ref)
        if self.store.subject_unit(inputs.query_ref) != 'aa' or not query.get('sequence_ref'):
            raise ContractError('explicit_protein_sequence_operand_required')
        if self.store.roots(inputs.query_ref) and not self.store.scope_covers(self.store.coverage(inputs.query_ref), scope):
            raise ContractError('homology_query_outside_assigned_scope')
        # Retain native bytes even if parsing or later reference resolution fails.
        text = artifact_file(self.store, inputs.native_text, 'text/plain')
        table = artifact_file(self.store, inputs.hit_table, 'text/plain') if Path(inputs.hit_table).exists() else None
        domain_table = (artifact_file(self.store, inputs.domain_table, 'text/plain')
            if inputs.domain_table is not None and Path(inputs.domain_table).is_file() else None)
        query_file = artifact_file(self.store, inputs.query_fasta, 'text/plain')
        query_hash = hashlib.sha256()
        with artifact_path(self.store, query['sequence_ref']).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                query_hash.update(chunk.upper())
        worker_fingerprint = hashlib.sha256(b''.join(Path(__file__).with_name(name).read_bytes()
            for name in ('phmmer_format.py', 'phmmer_result_worker.py', 'phmmer_grading_worker.py',
                         'hmmer_search_inputs.py', 'hmmer_search_grader.py', 'hmmer_graders.py'))).hexdigest()
        supplied = inputs.provenance or {}
        native_parameters = supplied.get('native_parameters')
        if native_parameters is None:
            original = supplied.get('original_job_manifest', supplied.get('native_handle', {}))
            native_parameters = {key: original[key] for key in ('command', 'cpu', 'search_mode', 'native_policy')
                                 if key in original}
        metadata = {'query_ref': inputs.query_ref, 'native_text_artifact': text, 'hit_table_artifact': table,
            'domain_table_artifact': domain_table,
            'query_fasta_artifact': query_file, 'database_sha256': inputs.database_sha256,
            'query_sequence_artifact': query['sequence_ref'], 'query_sequence_sha256': query_hash.hexdigest(),
            'executable_sha256': inputs.executable_sha256, 'parser_version': GRADING_VERSION,
            'native_parameters': native_parameters,
            'biopython_version': version('biopython'),
            'parser_implementation_sha256': worker_fingerprint}
        # Supplied command metadata describes this capture. The pure numerical
        # readers/calculators consume native bytes and explicit operands, which
        # remain in this key; they do not consume native_parameters. A new
        # provenance wrapper must not rerun the same bounded native extraction.
        parse_identity = {key: value for key, value in metadata.items() if key != 'native_parameters'}
        signature = hashlib.sha256(canonical(parse_identity).encode()).hexdigest()
        if retry_from is not None:
            self._snapshot(retry_from, query_ref=inputs.query_ref, scope=scope,
                execution_context=execution_context)
            if type(attempt_key) is not str or not attempt_key:
                raise ContractError('parse_retry_requires_selected_operation_identity')
        provenance = self._source('native.phmmer.execution', inputs.provenance, operands=[inputs.query_ref])
        native = self._source('native.phmmer.snapshot', metadata, parents=[provenance['id']],
                              operands=[inputs.query_ref], artifact=text, parser_version=GRADING_VERSION)
        directory = self.store.path/'cache'/'phmmer_results'/signature
        if retry_from is not None:
            directory = directory/('attempt-'+hashlib.sha256(attempt_key.encode()).hexdigest())
        directory.mkdir(parents=True, exist_ok=True)
        request = {'directory': str(directory), 'query_fasta': str(artifact_path(self.store, query_file)),
            'reference_fasta': str(Path(inputs.reference_fasta).resolve()),
            'native_text': str(artifact_path(self.store, text)),
            'hit_table': str(artifact_path(self.store, table)) if table else str(directory/'missing-hit-table'),
            'domain_table': str(artifact_path(self.store, domain_table)) if domain_table else None,
            'expected_query_sha256': query_hash.hexdigest(), 'database_sha256': inputs.database_sha256,
            'executable_sha256': inputs.executable_sha256, 'native_parameters': native_parameters,
            'grading_artifacts': {role: {'artifact_ref': reference,
                'availability': 'retained' if reference else 'unavailable'} for role, reference in (
                ('stdout', text), ('tblout', table), ('domtblout', domain_table),
                ('query_fasta', query_file), ('query_sequence', query['sequence_ref']))}}
        cached = self.store.db.execute('SELECT directory,body FROM homology_parse_cache WHERE signature=?', (signature,)).fetchone()
        if cached and retry_from is None:
            directory, parsed = Path(cached[0]), json.loads(cached[1])
        else:
            if digest(inputs.reference_fasta) != inputs.database_sha256:
                raise ContractError('native_reference_database_identity_changed', detail={'retained_source_ref': native['id']})
            parsed = await run_cancellable_native(_parse, directory, request, self.policy)
            with self.store.transaction():
                self.store.db.execute('INSERT INTO homology_parse_cache VALUES(?,?,?) ON CONFLICT(signature) DO UPDATE SET directory=excluded.directory,body=excluded.body',
                                      (signature, str(directory), canonical(parsed)))
        details = {**metadata, 'execution_source_ref': provenance['id'], 'native_source_ref': native['id'],
                   'parse_execution': parsed, 'retry_of_snapshot_ref': retry_from,
                   'execution_context': execution_context, 'parse_inventory': _parse_inventory(directory),
                   'publication_witness_version': 'native_row_publication_v1',
                   'native_termination_seen': _termination_seen(artifact_path(self.store, text))}
        snapshot = self._source('native.phmmer.parsed_snapshot', details,
                                parents=[native['id'], *([retry_from] if retry_from else [])],
                                operands=[inputs.query_ref], parser_version=GRADING_VERSION)
        with self.store.transaction():
            self.store.db.execute('INSERT OR IGNORE INTO homology_result_snapshots VALUES(?,?,?,?,?)',
                (snapshot['id'], signature, inputs.query_ref, str(directory), canonical(details)))
        return snapshot['id']

    def _reference(self, native, snapshot, directory):
        binding = hashlib.sha256(canonical({'database_sha256': snapshot['database_sha256'],
            **{key: native[key] for key in ('reference_id', 'database_description', 'sequence_sha256', 'length')}}).encode()).hexdigest()
        old = self.store.db.execute('SELECT reference_ref FROM homology_reference_bindings WHERE binding_key=?', (binding,)).fetchone()
        if old:
            return self.store.get(old[0])
        database = self._source('native.phmmer.database_manifest', {'database_sha256': snapshot['database_sha256']})
        seq = artifact_file(self.store, directory/native['sequence_file'], 'text/plain')
        if self.store._require(seq, {'artifact'})['sha256'] != native['sequence_sha256']:
            raise ContractError('parsed_native_reference_sequence_changed')
        body = {'native_identifier': native['reference_id'], 'database_description': native['database_description'],
                'sequence_sha256': native['sequence_sha256'], 'length': native['length']}
        source = self._source('native.phmmer.reference', body, parents=[database['id']])
        # This is explicitly a local source identity, never an invented public
        # accession. The full native identifier/header stays in its source.
        accession = 'phmmer.reference.'+hashlib.sha256(native['reference_id'].encode()).hexdigest()
        row = self.store.put('reference', {'reference_type': 'protein', 'source_ref': source['id'],
            'accession': accession, 'label': accession, 'sequence_ref': seq, 'molecule': 'protein',
            'length': native['length'], 'term_refs': [], 'context_refs': []}, origin='tool')
        self.store.db.execute('INSERT INTO homology_reference_bindings VALUES(?,?)', (binding, row['id']))
        return row

    def _grading(self, row, reference, directory, snapshot):
        """Read one saved sheet and qualify its association before projection."""
        if 'grading_file' not in row:
            if row.get('grading_failure'):
                return {'sheet': None, 'scores': None, 'failure': row['grading_failure']}
            return None  # Historical worker semantics, not an unperformed grade.
        try:
            path = directory/row['grading_file']
            if path.parent != directory or path.name != row['grading_file']:
                raise ValueError('phmmer_grading_path_invalid')
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != row['grading_sha256']:
                raise ValueError('phmmer_grading_saved_bytes_changed')
            grading = json.loads(body)
            if grading.get('failure'):
                return grading
            sheet, scores = grading['sheet'], grading['scores']
            if len(sheet['domains']) != 1 or len(scores['domains']) != 1:
                raise ValueError('phmmer_grading_domain_association_invalid')
            domain, score = sheet['domains'][0], scores['domains'][0]
            if (domain['record_key'] != score['record_key'] or score['target_name'] != row['reference_id']
                    or score['intervals']['model'] != row['query_interval_aa_zero_based_half_open']
                    or score['intervals']['sequence'] != row['reference_interval_aa_zero_based_half_open']):
                raise ValueError('phmmer_grading_domain_association_invalid')
            artifact = self.store.get(reference['sequence_ref'])
            if sheet['inputs']['targets'][0]['sequence_digest'] != artifact['sha256']:
                raise ValueError('phmmer_grading_reference_sequence_mismatch')
            # This artifact is the exact already validated sequence consumed by
            # the bounded worker, now retained under its canonical Store ID.
            sheet['artifacts']['reference_sequence'] = {'artifact_ref': artifact['id'],
                'sha256': artifact['sha256'], 'availability': 'retained'}
            # Cached numbers may be shared across captures with different
            # descriptive provenance. Retain only this capture's supplied
            # settings in a newly published sheet; saved grade bytes and any
            # existing source remain unchanged.
            sheet['inputs']['native_parameters'] = snapshot.get('native_parameters', {})
            return grading
        except (ValueError, KeyError, TypeError, OSError) as error:
            return {'sheet': None, 'scores': None, 'failure': {'code': str(error)
                if isinstance(error, ValueError) else 'phmmer_grading_saved_result_unavailable',
                'exception_type': type(error).__name__}}

    async def extract(self, inputs, *, scope, limit, offset=0, snapshot_ref=None, retry_from=None, attempt_key=None):
        if type(limit) is not int or limit < 0 or type(offset) is not int or offset < 0:
            raise ContractError('native_result_page_requires_nonnegative_integers')
        if snapshot_ref is None:
            if offset:
                raise ContractError('native_result_page_requires_snapshot_reference')
            snapshot_ref = await self.prepare(inputs, scope, retry_from=retry_from, attempt_key=attempt_key)
        elif retry_from is not None:
            raise ContractError('parse_retry_requires_new_snapshot_capture')
        saved, snapshot, _ = self._snapshot(snapshot_ref, query_ref=inputs.query_ref, scope=scope,
            execution_context=_execution_context(inputs.provenance))
        directory = Path(saved['directory'])
        if (snapshot['database_sha256'] != inputs.database_sha256 or
                snapshot['executable_sha256'] != inputs.executable_sha256):
            raise ContractError('native_result_snapshot_execution_dependencies_mismatch')
        refs, comparisons, changed, errors, publications = [], [], [], [], []
        database = directory/'measurements.sqlite'
        if not database.exists():
            return {'status': 'failed', 'record_refs': [snapshot_ref], 'changed_record_refs': [],
                    'result': {'snapshot_ref': snapshot_ref},
                    'feedback': {**(snapshot['parse_execution']['failure'] or {'code':'native_parse_store_unavailable'}),
                                 'retained_snapshot_ref': snapshot_ref, 'explicit_retry_available': True}}
        db = sqlite3.connect(database.as_uri()+'?mode=rw', uri=True)  # Also recovers a killed worker's committed prefix.
        try:
            total = db.execute('SELECT count(*) FROM measurements').fetchone()[0]
            failures, grading_failures = _error_counts(db)
            for ordinal, raw in db.execute('SELECT ordinal,data FROM measurements ORDER BY ordinal LIMIT ? OFFSET ?', (limit, offset)):
                row = json.loads(raw)
                checkpoint = len(refs), len(comparisons), len(changed), len(publications)
                try:
                    with self.store.transaction():
                        if row['kind'] == 'reference':
                            reference = self._reference(row, snapshot, directory)
                            refs.append(reference['id'])
                            publications.append(self._publication(snapshot_ref, ordinal, reference['id'],
                                'reference', row, snapshot))
                            continue
                        native_ref = db.execute('SELECT data FROM refs WHERE id=?', (row['reference_id'],)).fetchone()
                        reference = self._reference(json.loads(native_ref[0]), snapshot, directory)
                        refs.append(reference['id'])
                        grading = self._grading(row, reference, directory, snapshot)
                        semantic = {k:v for k,v in row.items() if k not in {
                            'source_byte_span', 'kind', 'grading_file', 'grading_sha256'}}
                        if grading and grading.get('failure'):
                            semantic['grading_publication_failure'] = grading['failure']['code']
                            errors.append({'ordinal': ordinal, 'code': 'phmmer_grading_unavailable',
                                           'grading_failure': grading['failure']})
                        key = hashlib.sha256(canonical({'measurement': semantic, 'query_ref': inputs.query_ref,
                            'database_sha256': snapshot['database_sha256'], 'executable_sha256': snapshot['executable_sha256'],
                            'parser_version': snapshot['parser_version']}).encode()).hexdigest()
                        old = self.store.db.execute('SELECT observation_ref FROM homology_measurements WHERE measurement_key=?', (key,)).fetchone()
                        if old:
                            observation_ref = old[0]
                            source = self.store.get(self.store.get(observation_ref)['source_ref'])
                            retained = json.loads(self.store.get_artifact(source['artifact_ref']))
                            if retained.get('numerical_projection_version') == 'hmmer_shared_paired_aliases_v1':
                                for saved_grading in source_tool_gradings(self.store, source['id']):
                                    failure = saved_grading.get('failure')
                                    if failure and failure.get('code') == 'phmmer_shared_grading_unavailable':
                                        errors.append({'ordinal': ordinal, 'code': 'phmmer_grading_unavailable',
                                                       'grading_failure': failure})
                        else:
                            if grading is None:
                                grading = {'sheet': None, 'scores': None, 'failure': {
                                    'code': 'phmmer_shared_grading_unavailable', 'category': 'grading_input'}}
                                errors.append({'ordinal': ordinal, 'code': 'phmmer_grading_unavailable',
                                               'grading_failure': grading['failure']})
                            source = self._source('native.phmmer.alignment', {**semantic, 'measurement_key': key,
                                'numerical_projection_version': 'hmmer_shared_paired_aliases_v1'},
                                parents=[snapshot_ref], operands=[inputs.query_ref, reference['id']],
                                tool_grading=grading, parser_version=snapshot['parser_version'])
                            values = {'evalue': row['independent_domain_evalue'], 'bitscore': row['domain_bitscore']}
                            if grading and not grading.get('failure'):
                                graded = grading['scores']['domains'][0]
                                values.update({name: graded[name] for name in HMMER_DOMAIN_METRICS
                                    if graded.get(name) is not None})
                                # These native aliases describe actual paired residues;
                                # the API publisher's endpoint-span aliases are distinct.
                                values.update({alias: graded[component] for alias, component in (
                                    ('query_coverage', 'paired_model_coverage'),
                                    ('target_coverage', 'paired_sequence_coverage'),
                                    ('identity_fraction', 'sequence_identity_fraction'))
                                    if graded.get(component) is not None})
                            measurements = [{'name': k, 'value': {'type': 'number', 'value': v, 'unit_ref': None}} for k,v in values.items()]
                            measurements.append({'name': 'reference_ref', 'value': {'type': 'reference', 'ref': reference['id']}})
                            operands = [{'role': role, 'subject_ref': ref, 'start': start, 'end': end, 'unit': 'aa', 'model_unit': 'aa'}
                                for role, ref in (('query', inputs.query_ref), ('reference', reference['id']))
                                for start,end in row['paired_intervals'][role]]
                            observation = self.store.put('observation', {'subject_refs': [inputs.query_ref],
                                'source_subject_refs': [reference['id']], 'kind': 'alignment', 'source_ref': source['id'],
                                'measurements': measurements, 'dependencies': [inputs.query_ref, reference['id']],
                                'anchor': None, 'operand_intervals': operands}, origin='tool', scope=scope)
                            observation_ref = observation['id']
                            self.store.db.execute('INSERT INTO homology_measurements VALUES(?,?)', (key, observation_ref))
                            changed.append(observation_ref)
                        publications.append(self._publication(snapshot_ref, ordinal, observation_ref,
                            'observation', row, snapshot))
                        comparisons.append(observation_ref)
                except (ContractError, ValueError, KeyError) as error:
                    del refs[checkpoint[0]:]
                    del comparisons[checkpoint[1]:]
                    del changed[checkpoint[2]:]
                    del publications[checkpoint[3]:]
                    errors.append({'ordinal': ordinal, 'code': str(error) if isinstance(error, ContractError) else 'native_row_publication_failed'})
            feedback = ({'code': 'phmmer_extraction_incomplete', 'native_error_count': failures,
                         **({'grading_error_count': grading_failures}
                            if 'grading_error_count' in snapshot.get('parse_inventory', {}) else {}),
                         'publication_errors': errors, 'parse_execution_failure': snapshot['parse_execution']['failure']}
                        if failures or grading_failures or errors or snapshot['parse_execution']['failure'] else None)
            count = min(limit, max(0, total-offset))
            next_offset = offset+count if offset+count < total else None
            result = {'snapshot_ref': snapshot_ref, 'execution_source_ref': snapshot['execution_source_ref'],
                'native_source_ref': snapshot['native_source_ref'], 'reference_refs': list(dict.fromkeys(refs)),
                'comparison_refs': list(dict.fromkeys(comparisons)), 'offset': offset, 'limit': limit,
                'publication_rows': publications,
                'native_result_complete': _native_complete(snapshot),
                'total': total, 'next_offset': next_offset, 'native_error_count': failures,
                'changed_record_semantics': 'new_canonical_alignment_observations_only',
                'error_query': {'snapshot_ref': snapshot_ref, 'offset': 0, 'limit': limit}}
            return {'status': ('partial' if total else 'failed') if feedback else 'completed',
                'record_refs': list(dict.fromkeys([snapshot_ref, *refs, *comparisons])),
                'changed_record_refs': changed, 'result': result, 'feedback': feedback}
        finally:
            db.close()

    def errors(self, snapshot_ref, *, scope, offset, limit, query_ref=None, execution_context=None):
        if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 0:
            raise ContractError('native_result_page_requires_nonnegative_integers')
        if query_ref is None:
            saved_query = self.store.db.execute('SELECT query_ref FROM homology_result_snapshots WHERE source_ref=?',
                (snapshot_ref,)).fetchone()
            if saved_query is None:
                raise ContractError('unknown_native_result_snapshot')
            query_ref = saved_query[0]
        saved, snapshot, _ = self._snapshot(snapshot_ref, query_ref=query_ref, scope=scope,
            execution_context=execution_context)
        path = Path(saved['directory'])/'measurements.sqlite'
        if not path.exists():
            return {'snapshot_ref': snapshot_ref, 'status': 'unavailable', 'errors': [], 'total': None,
                    'next_offset': None, 'parse_execution_failure': snapshot['parse_execution']['failure']}
        db = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True)
        try:
            total = db.execute('SELECT count(*) FROM errors').fetchone()[0]
            rows = []
            for ordinal, raw in db.execute('SELECT ordinal,data FROM errors ORDER BY ordinal LIMIT ? OFFSET ?', (limit, offset)):
                body = json.loads(raw)
                source = self._source('native.phmmer.parser_error', body, parents=[snapshot_ref], operands=[saved['query_ref']])
                rows.append({'ordinal': ordinal, 'source_ref': source['id'], 'code': body['code']})
            next_offset = offset+len(rows) if offset+len(rows) < total else None
            return {'snapshot_ref': snapshot_ref, 'status': 'available', 'errors': rows, 'total': total, 'next_offset': next_offset}
        finally:
            db.close()

    def witnesses(self, record_ref, *, scope, offset, limit):
        if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 0:
            raise ContractError('native_result_page_requires_nonnegative_integers')
        observed = self.store.get(record_ref)
        if observed['record_type'] not in {'reference', 'observation'}:
            raise ContractError('native_result_reference_or_observation_required')
        self.store.validate_scope(scope)
        if observed['record_type'] == 'observation' and not self.store.scope_covers(self.store.record_coverage(observed), scope):
            raise ContractError('homology_query_outside_assigned_scope')
        rows = self.store.db.execute('SELECT witnesses.snapshot_ref,witnesses.ordinal,witnesses.source_byte_spans,snapshots.query_ref '
            'FROM homology_result_witnesses witnesses JOIN homology_result_snapshots snapshots '
            'ON snapshots.source_ref=witnesses.snapshot_ref WHERE witnesses.record_ref=? ORDER BY witnesses.rowid', (record_ref,))
        values, total = [], 0
        for snapshot_ref, ordinal, raw, query_ref in rows:
            if self.store.roots(query_ref) and not self.store.scope_covers(self.store.coverage(query_ref), scope):
                continue
            if offset <= total < offset+limit:
                spans = json.loads(raw)
                values.append({'snapshot_ref': snapshot_ref, 'ordinal': ordinal, 'source_byte_spans': spans,
                    'native_text_byte_span': next((span['byte_span'] for span in spans if span['role'] == 'native_text'), None)})
            total += 1
        return {'record_ref': record_ref, 'record_type': observed['record_type'], 'witnesses': values, 'total': total,
                'next_offset': offset+len(values) if offset+len(values) < total else None}
