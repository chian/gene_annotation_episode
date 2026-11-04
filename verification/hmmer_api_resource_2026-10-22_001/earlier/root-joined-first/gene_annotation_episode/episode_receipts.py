"""Durable semantic receipts, separate from records and completed actions.

An episode inherits a frozen prefix of its parent's receipts. Only references
are retained here; source bytes, model contexts and closed child trees stay out
of this index. This component records delivery, not scientific validity/value.
"""
import json


RECEIPT_VERSION = 'frozen_parent_receipt_prefix_v1'


class EpisodeReceipts:
    def __init__(self, store, run_id):
        self.store, self.db, self.run_id = store, store.db, run_id
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS runtime_receipt_inheritance(
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                parent_episode_id TEXT, through_receipt_index INTEGER,
                PRIMARY KEY(run_id,episode_id));
            CREATE TABLE IF NOT EXISTS runtime_record_receipts(
                receipt_index INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                record_ref TEXT NOT NULL, receipt_kind TEXT NOT NULL,
                source_index INTEGER,
                UNIQUE(run_id,episode_id,record_ref));
        ''')
        self.db.commit()

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
            self.db.execute('INSERT INTO runtime_receipt_inheritance VALUES(?,?,?,?)',
                (self.run_id, episode_id, parent_episode_id, through))
            return self.manifest(episode_id)

    def manifest(self, episode_id):
        row = self.db.execute('SELECT parent_episode_id,through_receipt_index '
            'FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
            (self.run_id, episode_id)).fetchone()
        if row is None:
            raise ValueError('episode_receipts_not_bound')
        return {'version': RECEIPT_VERSION, 'parent_episode_id': row[0],
                'through_receipt_index': row[1]}

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
                pending.extend(ref for ref in self.store._refs(record) if ref not in seen)
