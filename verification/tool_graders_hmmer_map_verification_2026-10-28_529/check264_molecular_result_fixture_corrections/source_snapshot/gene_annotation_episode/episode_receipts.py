"""Durable semantic receipts, separate from records and completed actions.

An episode inherits a frozen prefix of its parent's receipts. Only references
and original typed-return identities/digests are retained here; source bytes,
model contexts and closed child trees stay out of this index. This component
records delivery, not scientific validity/value.
"""
import json
import re


RECEIPT_VERSION = 'frozen_parent_receipt_prefix_v1'
RECEIVED_REPORT_PREFIX_VERSION = 'frozen_received_report_prefix_v1'


def _validate_report_prefix(value):
    """Check stored metadata without looking up or admitting additional data."""
    if (type(value) is not dict or set(value) != {'version', 'attempts'}
            or value['version'] != RECEIVED_REPORT_PREFIX_VERSION
            or type(value['attempts']) is not list):
        raise ValueError('invalid_received_report_prefix')
    previous = -1
    for attempt in value['attempts']:
        if (type(attempt) is not dict or set(attempt) != {'decision_index',
                'delivery_ref', 'child_episode_id', 'contract_sha256', 'form_sha256'}
                or type(attempt['decision_index']) is not int
                or attempt['decision_index'] <= previous
                or any(type(attempt[key]) is not str or not attempt[key]
                       for key in ('delivery_ref', 'child_episode_id'))
                or any(type(attempt[key]) is not str or re.fullmatch(
                    r'[0-9a-f]{64}', attempt[key]) is None
                       for key in ('contract_sha256', 'form_sha256'))):
            raise ValueError('invalid_received_report_prefix')
        previous = attempt['decision_index']
    return value


class EpisodeReceipts:
    def __init__(self, store, run_id):
        self.store, self.db, self.run_id = store, store.db, run_id
        schema = '''
            CREATE TABLE IF NOT EXISTS runtime_receipt_inheritance(
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                parent_episode_id TEXT, through_receipt_index INTEGER,
                received_report_prefix TEXT,
                PRIMARY KEY(run_id,episode_id));
            CREATE TABLE IF NOT EXISTS runtime_record_receipts(
                receipt_index INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                record_ref TEXT NOT NULL, receipt_kind TEXT NOT NULL,
                source_index INTEGER,
                UNIQUE(run_id,episode_id,record_ref));
        '''
        # Read-side consumers also construct this helper inside a commission.
        # executescript/commit would publish that caller's unfinished work.
        with self.store.transaction():
            for statement in schema.split(';'):
                if statement.strip():
                    self.db.execute(statement)
            if 'received_report_prefix' not in {row[1] for row in self.db.execute(
                    'PRAGMA table_info(runtime_receipt_inheritance)')}:
                # Existing rows remain NULL: no retrospective receipt-time claim.
                self.db.execute('ALTER TABLE runtime_receipt_inheritance '
                                'ADD COLUMN received_report_prefix TEXT')

    def _received_report_prefix(self, parent_episode_id):
        # This is the set actually received at construction, not the set of
        # children commissioned at smaller decision indices. A delayed return
        # can have an earlier decision index than an already constructed child.
        from .execution_contracts import digest

        attempts = []
        if parent_episode_id is not None and self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_report_attempts'").fetchone() is not None:
            for row in self.db.execute('SELECT decision_index,delivery_ref,child_episode_id,'
                    'contract,form FROM runtime_report_attempts WHERE run_id=? '
                    'AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
                    'ORDER BY decision_index', (self.run_id, parent_episode_id)):
                attempts.append({'decision_index': row[0], 'delivery_ref': row[1],
                    'child_episode_id': row[2], 'contract_sha256': digest(json.loads(row[3])),
                    'form_sha256': digest(json.loads(row[4]))})
        return _validate_report_prefix({'version': RECEIVED_REPORT_PREFIX_VERSION,
                                        'attempts': attempts})

    def bind(self, episode_id, parent_episode_id=None):
        """Freeze inheritance once, recovering the original prefix on replay."""
        # Child construction participates in the caller's commission
        # transaction. An unconditional commit would invalidate its savepoint
        # and publish inheritance even if commissioning subsequently fails.
        with self.store.transaction():
            row = self.db.execute('SELECT parent_episode_id,through_receipt_index '
                'FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                (self.run_id, episode_id)).fetchone()
            if row is not None:
                if row[0] != parent_episode_id:
                    raise ValueError('episode_receipt_parent_changed')
                return self.manifest(episode_id)
            if parent_episode_id is None:
                through = None
            else:
                if parent_episode_id == episode_id or self.db.execute(
                        'SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                        (self.run_id, parent_episode_id)).fetchone() is None:
                    raise ValueError('existing_receipt_parent_required')
                through = self.db.execute('SELECT coalesce(max(receipt_index),0) '
                    'FROM runtime_record_receipts WHERE run_id=? AND episode_id=?',
                    (self.run_id, parent_episode_id)).fetchone()[0]
            prefix = self._received_report_prefix(parent_episode_id)
            self.db.execute('INSERT INTO runtime_receipt_inheritance '
                '(run_id,episode_id,parent_episode_id,through_receipt_index,received_report_prefix) '
                'VALUES(?,?,?,?,?)', (self.run_id, episode_id, parent_episode_id, through,
                                     json.dumps(prefix, sort_keys=True, separators=(',', ':'))))
            return self.manifest(episode_id)

    def manifest(self, episode_id):
        return self.read_manifest(self.db, self.run_id, episode_id)

    @staticmethod
    def read_manifest(db, run_id, episode_id):
        """Read the frozen manifest without schema changes or transaction commits."""
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_receipt_inheritance'").fetchone() is None:
            raise ValueError('episode_receipts_not_bound')
        cursor = db.execute('SELECT * '
            'FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
            (run_id, episode_id))
        row = cursor.fetchone()
        if row is None:
            raise ValueError('episode_receipts_not_bound')
        columns = dict(zip((column[0] for column in cursor.description), row))
        manifest = {'version': RECEIPT_VERSION, 'parent_episode_id': columns['parent_episode_id'],
                    'through_receipt_index': columns['through_receipt_index']}
        saved = columns.get('received_report_prefix')
        if saved is not None:
            manifest['received_report_prefix'] = _validate_report_prefix(json.loads(saved))
        return manifest

    def selection(self, episode_id, *, record_type=None, baseline=False):
        """SQL selection of known handles, without copying an inherited ledger."""
        lineage, seen = [], set()
        current, through = episode_id, None
        while current is not None:
            if current in seen:
                raise ValueError('cyclic_receipt_inheritance')
            seen.add(current)
            lineage.append({'episode_id': current, 'through': through})
            manifest = self.manifest(current)
            current, through = manifest['parent_episode_id'], manifest['through_receipt_index']
        query = '''SELECT DISTINCT receipts.record_ref FROM runtime_record_receipts receipts
            JOIN json_each(?) ancestor
              ON receipts.episode_id=json_extract(ancestor.value,'$.episode_id')
            WHERE receipts.run_id=? AND (json_extract(ancestor.value,'$.through') IS NULL
                OR receipts.receipt_index<=json_extract(ancestor.value,'$.through'))'''
        parameters = [json.dumps(lineage), self.run_id]
        if baseline:
            # The same frozen inheritance prefix plus this episode's original
            # caller inputs. Later own work/child forms are not initial knowledge.
            query += ' AND (receipts.episode_id<>? OR receipts.receipt_kind=?)'
            parameters.extend([episode_id, 'initial'])
        if record_type is not None:
            query += ' AND EXISTS (SELECT 1 FROM records record WHERE record.id=receipts.record_ref AND record.record_type=?)'
            parameters.append(record_type)
        return query, parameters

    def known(self, episode_id, *, record_type=None, baseline=False):
        query, parameters = self.selection(episode_id, record_type=record_type, baseline=baseline)
        return (row[0] for row in self.db.execute(query+' ORDER BY receipts.record_ref', parameters))

    def receive(self, episode_id, references, *, kind, source_index=None):
        """Record actual reference delivery and its declared semantic dependencies.

        A requested annotation/account carries its cited assessments; a source
        does not carry every observation ever derived from it. Traversal follows
        existing forward reference fields only and never reads artifact bytes.
        The caller admits a form or records a selected operation before calling.
        """
        if kind not in {'initial', 'decision_input', 'own_action', 'child_form', 'report_redelivery'}:
            raise ValueError('unknown_receipt_kind')
        self.manifest(episode_id)
        pending, seen = list(references), set()
        with self.store.transaction():
            while pending:
                reference = pending.pop()
                if reference in seen:
                    continue
                seen.add(reference)
                record = self.store.get(reference)
                # Native collection members use their existing paged interface.
                if record.get('record_type') == 'collection_member':
                    continue
                self.db.execute('INSERT OR IGNORE INTO runtime_record_receipts '
                    '(run_id,episode_id,record_ref,receipt_kind,source_index) VALUES(?,?,?,?,?)',
                    (self.run_id, episode_id, reference, kind, source_index))
                restriction_custody = (record.get('provider'), record.get('version')) in {
                    ('episode.restriction_input', 'restriction_input_source_v1'),
                    ('episode.restriction_result', 'restriction_published_result_v1')}
                if (restriction_custody or record.get('provider') == 'episode.execution_result'
                        and record.get('version') in {'native_infernal_preparation_bundle_v1',
                                                     'native_hmmer_preparation_bundle_v1',
                                                     'native_blast_masking_bundle_v1',
                                                     'native_blast_utility_bundle_v1',
                                                     'native_blast_database_bundle_v1',
                                                     'native_protein_structure_bundle_v1',
                                                     'native_rna_structure_bundle_v1'}):
                    # Custody retains the full bundle and auxiliary data. This
                    # source alone delivers none of those unrequested artifacts.
                    # Explicit selected artifact references remain in pending.
                    continue
                pending.extend(ref for ref in self.store._refs(record) if ref not in seen)
