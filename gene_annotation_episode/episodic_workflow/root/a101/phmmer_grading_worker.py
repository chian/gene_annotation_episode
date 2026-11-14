"""Disk-backed associations for the existing bounded phmmer extraction worker.

This is custody/join plumbing, not another scientific calculator or operation.
The pure HMMER readers populate native rows; their sheet builder/calculator
remain the numerical authority. At most one native target and one published
alignment are hydrated. Complete event populations and ambiguous rows stay on
disk beside the retained original artifacts.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_graders import HMMER_DOMAIN_METRICS
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_search_inputs import build_hmmer_search_sheet, iter_hmmer_stdout_events, iter_hmmer_table_rows
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.episodic_workflow.root.a101.library.phmmer_grading_values import PhmmerGradingValues, domain_key, encoded, hit_key










class GradingRows(PhmmerGradingValues):
    def __init__(self, db, request, *, query_name, sequence, error):
        self.db, self.request, self.error = db, request, error
        self.query_name, self.sequence = query_name, sequence
        self.artifacts = deepcopy(request.get('grading_artifacts', {}))
        self.termination = {}
        self.version = None
        self.version_conflict = False
        self.invalid_roles = set()
        self.failed = None
        db.executescript('''
        CREATE TABLE grading_native_rows (
            ordinal INTEGER PRIMARY KEY,kind TEXT NOT NULL,role TEXT NOT NULL,
            record_key TEXT,query_key TEXT,query_occurrence INTEGER,target_name TEXT,
            match_key TEXT,data TEXT NOT NULL);
        CREATE INDEX grading_match ON grading_native_rows(kind,role,match_key);
        CREATE INDEX grading_query ON grading_native_rows(kind,query_key);
        CREATE INDEX grading_target ON grading_native_rows(kind,role,query_key,target_name);
        ''')

    def _ingest(self, event, role):
        kind, row = event['kind'], event['data']
        key = domain_key(row) if kind == 'domain' else hit_key(row) if kind == 'hit' else None
        with self.db:
            self.db.execute('INSERT INTO grading_native_rows VALUES(NULL,?,?,?,?,?,?,?,?)',
                (kind, role, row.get('record_key'), row.get('query_record_key'),
                 row.get('query_occurrence', row.get('occurrence')), row.get('target_name'), key, encoded(row)))
        if kind == 'issue':
            self.error({'code': row['code'], 'phase': 'hmmer_native_reader', 'native_issue': row})
        for issue in row.get('issues', []):
            self.error({'code': issue['code'], 'phase': 'hmmer_native_reader', 'native_issue': issue})
        if kind == 'query' and (row.get('occurrence') != 0 or row.get('name') != self.query_name
                or row.get('length') != len(self.sequence)):
            self.error({'code': 'phmmer_grading_unexpected_query', 'locator': row['locator']})
        if kind == 'annotation':
            text = row.get('text', row.get('raw_line', '')).strip()
            if text in {'[ok]', '# [ok]'}:
                self.termination[role] = True
            match = re.match(r'# (?:HMMER\s+|Version:\s*)(\S+)', text)
            if match:
                if self.version is None:
                    self.version = match[1]
                elif self.version != match[1]:
                    self.version_conflict = True
                    self.error({'code': 'phmmer_grading_native_version_conflict', 'locator': row['locator']})
            program = re.match(r'# Program:\s*(\S+)', text) or re.match(
                r'# (phmmer|hmmscan|hmmsearch|jackhmmer) ::', text)
            if program and program[1] != 'phmmer':
                self.invalid_roles.add(role)
                self.error({'code': 'hmmer_native_program_mismatch', 'artifact_role': role,
                    'reported': program[1], 'selected': 'phmmer', 'locator': row['locator']})

    def capture(self):
        for role, request_key in (('tblout', 'hit_table'), ('domtblout', 'domain_table'), ('stdout', 'native_text')):
            path = self.request.get(request_key)
            if not path or not Path(path).is_file():
                continue
            self.termination[role] = False
            with Path(path).open('rb') as stream:
                kwargs = {'program': 'phmmer', 'artifact_ref': self.artifacts.get(role, {}).get('artifact_ref')}
                events = (iter_hmmer_stdout_events(stream, **kwargs) if role == 'stdout'
                    else iter_hmmer_table_rows(stream, role=role, **kwargs))
                for event in events:
                    self._ingest(event, role)





