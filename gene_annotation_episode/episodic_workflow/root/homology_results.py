"""Original paged homology results, qualified grades and retained witnesses."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from .library.hmmer_graders import HMMER_DOMAIN_METRICS
from .library.homology_result_coverage import _execution_context, _error_counts, _native_complete
from .library.homology_result_publication import HomologyResultPublication
from .library.native_phmmer_preparation import NativePhmmerPreparation
from .library.tool_grading_artifacts import source_tool_gradings


class HomologyResults(NativePhmmerPreparation, HomologyResultPublication):
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
