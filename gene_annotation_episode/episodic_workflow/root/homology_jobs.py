"""Durable one-query registry with its original selected execution semantics."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import uuid
from gene_annotation_episode._local_job_worker import atomic_json
from gene_annotation_episode.local_jobs import LocalJobPolicy
from .library.homology_job_contracts import VERSION
from .library.homology_job_inputs import FileAsset, normalize_query_fasta, ref
from .library.homology_job_execution import HomologyJobExecution
from .library.homology_job_receipts import HomologyJobReceipts


SEARCH_MODES = {'native_defaults': (), 'maximum_sensitivity': ('--max',)}


class HomologyJobs(HomologyJobExecution, HomologyJobReceipts):
    @classmethod
    def create(cls, directory, *, executable: FileAsset, reference_database: FileAsset,
               policy: LocalJobPolicy, max_cpu: int, search_modes=None):
        if type(max_cpu) is not int or max_cpu < 1 or type(policy) is not LocalJobPolicy:
            raise ValueError('caller_owned_homology_resources_required')
        if search_modes is not None and (not isinstance(search_modes, (list, tuple)) or not search_modes
                or any(type(mode) is not str or mode not in SEARCH_MODES for mode in search_modes)
                or len(set(search_modes)) != len(search_modes)):
            raise ValueError('caller_owned_homology_search_modes_required')
        directory = Path(directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=False)
        configuration = {'version': VERSION, 'registry_ref': 'execution_registry_'+uuid.uuid4().hex,
            'executable': executable.as_record(), 'reference_database': reference_database.as_record(),
            'job_limits': policy.to_dict(), 'max_cpu': max_cpu}
        if search_modes is not None:
            configuration['search_modes'] = list(search_modes)
        atomic_json(directory/'configuration.json', configuration)
        with sqlite3.connect(directory/'jobs.sqlite') as db:
            db.executescript('''
            CREATE TABLE orders (job_ref TEXT PRIMARY KEY, operation_key TEXT UNIQUE NOT NULL,
                query_ref TEXT NOT NULL, query_fasta TEXT NOT NULL, cpu INTEGER NOT NULL, staged INTEGER NOT NULL,
                submission_requested INTEGER NOT NULL);
            CREATE TABLE handoffs (receipt_ref TEXT PRIMARY KEY,job_ref TEXT NOT NULL,body TEXT NOT NULL);
            CREATE TABLE samples (sample_ref TEXT PRIMARY KEY,operation_key TEXT UNIQUE NOT NULL,
                job_ref TEXT NOT NULL,body TEXT NOT NULL);
            ''')
            if search_modes is not None:
                db.execute('ALTER TABLE orders ADD COLUMN search_mode TEXT NOT NULL')
        return cls(directory)

    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.config = json.loads((self.directory/'configuration.json').read_text())
        if self.config['version'] != VERSION:
            raise ValueError('unsupported_homology_job_registry')
        self.db = sqlite3.connect((self.directory/'jobs.sqlite').as_uri()+'?mode=rw', uri=True)
        self.db.row_factory = sqlite3.Row

    def close(self):
        self.db.close()

    def _row(self, job_ref):
        row = self.db.execute('SELECT * FROM orders WHERE job_ref=?', (job_ref,)).fetchone()
        if row is None:
            raise ValueError('job_not_registered_here')
        return {**dict(row), 'search_mode': row['search_mode'] if 'search_mode' in row.keys() else 'native_defaults'}

    @property
    def search_modes(self):
        return tuple(self.config.get('search_modes', ['native_defaults']))

    def _command(self, row):
        if row.get('search_mode', 'native_defaults') not in self.search_modes:
            raise ValueError('registered_search_mode_outside_caller_configuration')
        return [self.config['executable']['path'], '--cpu', str(row['cpu']),
            *SEARCH_MODES[row.get('search_mode', 'native_defaults')], '--tblout', 'hits.tbl',
            '--domtblout', 'domains.tbl', 'query.faa', 'references.faa']

    def _directory(self, job_ref):
        self._row(job_ref)
        return self.directory/job_ref

    def order(self, *, query_ref, query_fasta, cpu, operation_key, search_mode=None):
        """Record selected query/allocation; this does not stage or submit."""
        if type(query_ref) is not str or not query_ref or type(operation_key) is not str or not operation_key:
            raise ValueError('homology_operand_and_operation_required')
        if type(cpu) is not int or cpu < 1:
            raise ValueError('cpu_outside_caller_allocation')
        if search_mode is None and 'search_modes' not in self.config:
            search_mode = 'native_defaults'
        if type(search_mode) is not str or search_mode not in self.search_modes:
            raise ValueError('search_mode_outside_caller_configuration_or_not_selected')
        normalized = normalize_query_fasta(query_fasta)
        old = self.db.execute('SELECT * FROM orders WHERE operation_key=?', (operation_key,)).fetchone()
        if old:
            old_mode = old['search_mode'] if 'search_mode' in old.keys() else 'native_defaults'
            if (old['query_ref'] != query_ref or old['query_fasta'] != normalized or old['cpu'] != cpu
                    or old_mode != search_mode):
                raise ValueError('homology_order_identity_conflict')
            return old['job_ref']
        operands = [self.config['registry_ref'], operation_key, query_ref, normalized, cpu]
        if 'search_modes' in self.config:
            operands.append(search_mode)
        job_ref = ref('homology_job', operands)
        with self.db:
            if 'search_modes' in self.config:
                self.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,0,0,?)',
                                (job_ref, operation_key, query_ref, normalized, cpu, search_mode))
            else:
                self.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,0,0)',
                                (job_ref, operation_key, query_ref, normalized, cpu))
        return job_ref

    def environment(self, job_ref):
        row = self._row(job_ref)
        return {'job_ref': job_ref, 'executable_exists': Path(self.config['executable']['path']).is_file(),
            'reference_database_exists': Path(self.config['reference_database']['path']).is_file(),
            'max_cpu': self.config['max_cpu'], 'configured_cpu': row['cpu'], 'staged': bool(row['staged']),
            'submission_requested': self._has_intent(row), 'job_limits': self.config['job_limits'],
            **({'configured_search_mode': row['search_mode']} if 'search_modes' in self.config else {})}

