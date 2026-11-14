"""One derived view of current scientific finding corrections.

Authoritative facts remain assessment revisions and their typed correction
links. This disk-backed index supports both annotation and information progress;
it neither assesses scientific truth nor admits work.
"""
import json
import sqlite3

from .domain import canonical
from .scientific_findings import finding_target_roots


VALIDITY_VERSION = 'owned_current_finding_replacement_closure_v1'


def target_eligible(store, assessment, scope):
    if 'context_account_scope' in assessment:
        allocation = assessment.get('context_scope')
        return bool(allocation and allocation['subject_refs'] and
                    store.context_mask_overlap(allocation, scope))
    if not finding_target_roots(store, assessment).intersection(scope['subject_refs']):
        return False
    extent = store._assessment_write_extent(assessment)
    if not extent:
        extent = store.record_coverage(store.get(assessment['hypothesis_ref']))
    return bool(extent) and store.context_mask_overlap({
        'subject_refs': sorted({row['target_ref'] for row in extent}), 'segments': extent}, scope)


def correction_eligible(store, assessment, scope):
    if 'context_account_scope' in assessment:
        allocation = assessment.get('context_scope')
        return (store.context_mask_overlap(allocation, scope) if allocation and allocation['subject_refs']
                else store.context_mask_overlap(assessment['context_account_scope'], scope))
    return target_eligible(store, assessment, scope)


class FindingValidity:
    """Build once within the caller's Store read snapshot; release on close."""

    def __init__(self, store, scope, *, spool=None):
        self.store, self.scope = store, store.validate_scope(scope)
        self.owns_spool = spool is None
        self.spool = sqlite3.connect('') if spool is None else spool
        self.spool.row_factory = sqlite3.Row
        try:
            self.spool.executescript('''PRAGMA temp_store=FILE; PRAGMA cache_size=-2048;
                CREATE TABLE fv_nodes(ref TEXT PRIMARY KEY,payload TEXT);
                CREATE TABLE fv_roots(ref TEXT PRIMARY KEY);
                CREATE TABLE fv_pending(ref TEXT PRIMARY KEY);
                CREATE TABLE fv_visited(ref TEXT PRIMARY KEY);
                CREATE TABLE fv_edges(replacer TEXT,prior TEXT,PRIMARY KEY(replacer,prior));
                CREATE INDEX fv_prior_edge ON fv_edges(prior,replacer);
                CREATE TABLE fv_retired(ref TEXT PRIMARY KEY);
            ''')
            self._build()
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self.owns_spool:
            self.spool.close()

    def _build(self):
        db, start = self.spool, 0
        while True:
            rows = self.store.current_assessments(self.scope, limit=100, offset=start)
            for row in rows:
                if 'investigation_finding' in row and correction_eligible(self.store, row, self.scope):
                    db.execute('INSERT OR IGNORE INTO fv_roots VALUES(?)', (row['id'],))
                    db.execute('INSERT OR IGNORE INTO fv_nodes VALUES(?,?)', (row['id'], canonical(row)))
                    db.execute('INSERT OR IGNORE INTO fv_pending VALUES(?)', (row['id'],))
            if len(rows) < 100:
                break
            start += len(rows)
        while True:
            pending = db.execute('SELECT ref FROM fv_pending ORDER BY ref LIMIT 1').fetchone()
            if pending is None:
                break
            ref = pending['ref']
            db.execute('DELETE FROM fv_pending WHERE ref=?', (ref,))
            if not db.execute('INSERT OR IGNORE INTO fv_visited VALUES(?)', (ref,)).rowcount:
                continue
            cached = db.execute('SELECT payload FROM fv_nodes WHERE ref=?', (ref,)).fetchone()
            row = json.loads(cached[0]) if cached else self.store.get(ref)
            if not correction_eligible(self.store, row, self.scope):
                continue
            db.execute('INSERT OR IGNORE INTO fv_nodes VALUES(?,?)', (ref, canonical(row)))
            for prior in row.get('investigation_finding', {}).get('replaces_refs', ()):
                old = self.store.get(prior)
                if not correction_eligible(self.store, old, self.scope):
                    continue
                db.execute('INSERT OR IGNORE INTO fv_edges VALUES(?,?)', (ref, prior))
                db.execute('INSERT OR IGNORE INTO fv_nodes VALUES(?,?)', (prior, canonical(old)))
                db.execute('INSERT OR IGNORE INTO fv_pending VALUES(?)', (prior,))
        db.execute('''INSERT INTO fv_retired WITH RECURSIVE ancestry(ref) AS (
            SELECT e.prior FROM fv_edges e JOIN fv_roots r ON r.ref=e.replacer
            UNION SELECT e.prior FROM fv_edges e JOIN ancestry a ON a.ref=e.replacer)
            SELECT ref FROM ancestry''')

    def current_records(self):
        for row in self.spool.execute('''SELECT n.payload FROM fv_nodes n JOIN fv_roots r ON r.ref=n.ref
                LEFT JOIN fv_retired x ON x.ref=n.ref WHERE x.ref IS NULL ORDER BY n.ref'''):
            yield json.loads(row['payload'])

    def is_replaced(self, ref):
        return self.spool.execute('SELECT 1 FROM fv_retired WHERE ref=?', (ref,)).fetchone() is not None

    def one_witness(self, ref):
        row = self.spool.execute('''WITH RECURSIVE descendants(ref) AS (
            SELECT replacer FROM fv_edges WHERE prior=?
            UNION SELECT e.replacer FROM fv_edges e JOIN descendants d ON e.prior=d.ref)
            SELECT r.ref FROM fv_roots r JOIN descendants d ON d.ref=r.ref ORDER BY r.ref LIMIT 1''',
            (ref,)).fetchone()
        return row[0] if row else None

    def update_basis(self, digest):
        if not self.spool.execute('SELECT 1 FROM fv_roots LIMIT 1').fetchone():
            return
        digest.update(VALIDITY_VERSION.encode())
        for row in self.spool.execute('SELECT ref FROM fv_roots ORDER BY ref'):
            digest.update(canonical(list(row)).encode())
        for row in self.spool.execute('SELECT replacer,prior FROM fv_edges ORDER BY replacer,prior'):
            digest.update(canonical(list(row)).encode())
