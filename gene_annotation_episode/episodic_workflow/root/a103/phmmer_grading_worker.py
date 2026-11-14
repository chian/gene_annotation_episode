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

from .hmmer_graders import HMMER_DOMAIN_METRICS
from .hmmer_search_inputs import (build_hmmer_search_sheet,
    iter_hmmer_stdout_events, iter_hmmer_table_rows)
from .hmmer_search_grader import calculate_hmmer_search_scores


VERSION = 'phmmer_printed_alignment_with_hmmer_sheet_v1'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def domain_key(row):
    native = row.get('native', {})
    fields = ('reported_domain_ordinal', 'hmm_from', 'hmm_to', 'ali_from', 'ali_to')
    values = [row.get('query_name'), row.get('target_name'), *(native.get(k) for k in fields)]
    return encoded(values) if all(v is not None for v in values) else None


def hit_key(row):
    values = [row.get('query_name'), row.get('target_name'),
        row.get('native', {}).get('sequence_evalue'), row.get('native', {}).get('sequence_score_bits')]
    return encoded(values) if all(v is not None for v in values) else None


class GradingRows:
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

    def _matching(self, kind, role, key):
        # Fetch at most two rows: uniqueness is the only permission to join.
        rows = self.db.execute('SELECT data FROM grading_native_rows WHERE kind=? AND role=? AND match_key=? LIMIT 2',
            (kind, role, key)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def _merge(self, printed, kind, role):
        if role in self.invalid_roles:
            row = deepcopy(printed)
            row['issues'].append({'code': 'hmmer_native_artifact_identity_conflict', 'artifact_role': role})
            return row
        key = domain_key(printed) if kind == 'domain' else hit_key(printed)
        candidates = self._matching(kind, role, key) if key is not None else []
        reciprocal = self._matching(kind, 'stdout', key) if key is not None else []
        if len(candidates) == len(reciprocal) == 1:
            row = candidates[0]
            row['associations'] = [{'record_key': printed['record_key'], 'locator': deepcopy(printed['locator'])}]
            row['native_representations'] = [deepcopy(printed)]
            for name in ('query_record_key', 'query_occurrence', 'target_occurrence', 'iteration',
                         'is_included', 'alignment', 'hit_record_key'):
                if name in printed:
                    row[name] = deepcopy(printed[name])
            for name, value in printed['native'].items():
                if row['native'].get(name) is None:
                    row['native'][name] = value
            row['issues'].extend(printed.get('issues', []))
            return row
        row = deepcopy(printed)
        row['issues'].append({'code': ('hmmer_table_stdout_association_ambiguous' if candidates
            else 'hmmer_table_stdout_association_missing' if role in self.termination
            else 'hmmer_native_table_unavailable'), 'artifact_role': role,
            'record_key': printed['record_key'], 'match_key': key,
            'candidate_population': 'grading_native_rows on disk; complete original table retained'})
        return row

    def grade(self, alignment, reference, symbols):
        if self.failed is not None:
            raise ValueError(self.failed)
        if 'stdout' in self.invalid_roles:
            raise ValueError('phmmer_grading_native_program_mismatch')
        qs, qe = alignment['query_interval_aa_zero_based_half_open']
        rs, re_ = alignment['reference_interval_aa_zero_based_half_open']
        key = encoded([self.query_name, alignment['reference_id'], alignment['domain_index'], qs+1, qe, rs+1, re_])
        candidates = self._matching('domain', 'stdout', key)
        if len(candidates) != 1:
            raise ValueError('phmmer_grading_alignment_association_ambiguous' if candidates
                else 'phmmer_grading_alignment_association_missing')
        printed = candidates[0]
        if printed.get('query_occurrence') != 0:
            raise ValueError('phmmer_grading_unexpected_query')
        display = printed.get('alignment', {})
        if (display.get('model') != alignment['query_aligned'] or
                display.get('aseq') != alignment['reference_aligned']):
            raise ValueError('phmmer_grading_alignment_display_mismatch')
        query_rows = self.db.execute('SELECT data FROM grading_native_rows WHERE kind=? AND record_key=? LIMIT 2',
            ('query', printed['query_record_key'])).fetchall()
        if len(query_rows) != 1:
            raise ValueError('phmmer_grading_query_association_missing')
        query = json.loads(query_rows[0][0])
        if (query.get('occurrence'), query.get('name'), query.get('length')) != (0, self.query_name, len(self.sequence)):
            raise ValueError('phmmer_grading_unexpected_query')
        domain = self._merge(printed, 'domain', 'domtblout')
        hits = self.db.execute('SELECT data FROM grading_native_rows WHERE kind=? AND role=? AND query_key=? AND target_name=? LIMIT 2',
            ('hit', 'stdout', printed['query_record_key'], alignment['reference_id'])).fetchall()
        associated_hits = []
        if len(hits) == 1:
            hit = self._merge(json.loads(hits[0][0]), 'hit', 'tblout')
            associated_hits.append(hit)
            domain['hit_record_key'] = hit['record_key']
            for field, value in hit['native'].items():
                if field.startswith('sequence_'):
                    domain['native'].setdefault(field, value)
        else:
            domain['issues'].append({'code': 'hmmer_stdout_hit_association_ambiguous' if hits
                else 'hmmer_stdout_hit_association_missing', 'record_key': domain['record_key']})
        collections = {}
        for kind, plural in (('statistic', 'statistics'), ('iteration', 'iterations')):
            collections[plural] = [json.loads(row[0]) for row in self.db.execute(
                'SELECT data FROM grading_native_rows WHERE kind=? AND query_key=? ORDER BY ordinal',
                (kind, printed['query_record_key']))]
        # Native single-query summary and annotations are bounded independently
        # of the hit population. All per-target rows remain in the disk index.
        annotations = [json.loads(row[0]) for row in self.db.execute(
            "SELECT data FROM grading_native_rows WHERE kind='annotation' AND "
            "(query_key=? OR query_key IS NULL) ORDER BY ordinal", (printed['query_record_key'],))]
        query['complete'] = any(row.get('native_query_terminated') for row in annotations)
        complete = bool(self.termination) and all(self.termination.values()) and query['complete']
        native = {'schema': 'hmmer_search_native_v1',
            'operation': {'program': 'phmmer', 'format': 'hmmer3_protein_text',
                          'engine_version': None if self.version_conflict else self.version,
                          'alphabet': 'amino', 'mode': 'sequence_database_search'},
            'queries': [query], 'hits': associated_hits, 'domains': [domain], **collections,
            'annotations': annotations,
            'issues': ([{'code': 'phmmer_grading_native_version_conflict'}] if self.version_conflict else []),
            'checkpoints': [], 'artifacts': deepcopy(self.artifacts),
            'completion': {'native_termination': deepcopy(self.termination), 'output_complete': complete,
                           'hit_population_complete': None},
            'row_selection': {'kind': 'one_published_alignment', 'all_native_rows_retained_on_disk': True,
                             'original_alignment_byte_span': alignment['source_byte_span']}}
        inputs = {'query': {'name': self.query_name, 'occurrence': 0, 'kind': 'protein_sequence',
            'alphabet': 'amino', 'length': len(self.sequence), 'sequence': self.sequence,
            'sequence_digest': self.request['expected_query_sha256']},
            'targets': [{'name': alignment['reference_id'], 'kind': 'protein_sequence', 'alphabet': 'amino',
                         'length': reference['length'], 'sequence': symbols,
                         'sequence_digest': reference['sequence_sha256']}],
            'database': {'sha256': self.request.get('database_sha256')},
            'native_executable': {'sha256': self.request.get('executable_sha256')},
            'native_parameters': deepcopy(self.request.get('native_parameters', {})),
            'acquisition': {'output_complete': complete, 'hit_population_complete': False}}
        sheet = build_hmmer_search_sheet(native, inputs=inputs)
        scores = calculate_hmmer_search_scores(sheet)
        graded = scores['domains'][0]
        if (graded['target_name'] != alignment['reference_id'] or
                graded['intervals'].get('model') != [qs, qe] or graded['intervals'].get('sequence') != [rs, re_]):
            raise ValueError('phmmer_grading_published_coordinates_mismatch')
        if (graded.get('paired_positions') != alignment['paired_residues'] or
                not sheet['domains'][0]['quantities'].get('actual_sequence_correspondence')):
            raise ValueError('phmmer_grading_actual_sequence_correspondence_mismatch')
        return {'sheet': sheet, 'scores': scores}


def grading_identity(grading):
    """Numerical semantics, excluding capture-specific artifact/line identities.

    A new raw capture is another witness to unchanged scientific measurements.
    An actual component change is a new explicit measurement version.
    """
    if grading.get('failure'):
        content = {'failure': grading['failure']['code']}
    else:
        row = grading['scores']['domains'][0]
        content = {name: row.get(name) for name in HMMER_DOMAIN_METRICS}
        content['unavailable'] = row.get('unavailable', {})
        content['native'] = row.get('native', {})
        content['posterior_population'] = row.get('posterior_population')
        content['hit_measurements'] = [{key: hit.get(key) for key in ('native', 'is_reported', 'is_included')}
            for hit in grading['scores']['hits']]
    return hashlib.sha256(encoded({'version': VERSION, 'components': content}).encode()).hexdigest()
