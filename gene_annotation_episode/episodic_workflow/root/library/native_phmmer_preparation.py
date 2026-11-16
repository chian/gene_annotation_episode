"""Original retained native snapshots, parser identity, cache and explicit retry."""
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.local_jobs import run_cancellable_native
from gene_annotation_episode.materials import artifact_file, artifact_path
from .homology_job_inputs import digest
from .homology_result_coverage import _snapshot, recorded_coverage, _execution_context, _parse_inventory, _termination_seen
from .native_phmmer_parser import _parse
from .phmmer_grading_worker import VERSION as GRADING_VERSION


class NativePhmmerPreparation:
    def _snapshot(self, snapshot_ref, *, query_ref, scope, execution_context):
        return _snapshot(self.store, snapshot_ref, query_ref=query_ref, scope=scope,
            execution_context=execution_context)

    def coverage(self, snapshot_ref, *, query_ref, scope, execution_context=None):
        return recorded_coverage(self.store, snapshot_ref, query_ref=query_ref, scope=scope,
            execution_context=execution_context)

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
            'biopython_version': version('biopython')}
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

