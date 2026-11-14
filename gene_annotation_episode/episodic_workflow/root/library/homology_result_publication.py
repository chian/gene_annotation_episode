"""Original PHMMER source, reference, grade and publication-witness custody."""
import hashlib
import json
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.materials import artifact_file
from .phmmer_format import VERSION
from .tool_grading_artifacts import retain_tool_grading


class HomologyResultPublication:
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

