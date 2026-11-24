"""Original phmmer scientific associations over the caller-supplied row index.

Restored from ``phmmer_grading_values.py`` at ``97308b94c`` (``grading_identity`` and
``PhmmerGradingValues``), with the disk-backed associations of ``phmmer_grading_worker.py``
(``GradingRows``) and the bounded extraction of ``phmmer_result_worker.py`` (``extract``), owner text and
logic unchanged. What changed is where the native rows live: the old ``grading_native_rows`` SQLite table of the
worker's directory is the declared work table ``NATIVE_ROWS``, written through the scoped store the tool hands
this module and read through ``reader.table(NATIVE_ROWS).select(...)``. A capture's rows are keyed by the capture's
identity and the row ordinal, so a repeated capture of the same bytes writes the same rows. The worker's own
bookkeeping (selected hits, resolved references, measurements, errors) is in-process Python state, and its input
files are the paths of a scratch directory the calling tool copied the held artifacts into.

This is custody/join plumbing, not another scientific calculator or operation. The pure HMMER readers populate
native rows; their sheet builder/calculator remain the numerical authority."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from Bio import SeqIO

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_graders import HMMER_DOMAIN_METRICS
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.phmmer_alignment_values import alignment_geometry, alignment_measurement
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.phmmer_format import alignment_rows, hit_rows, sequence_hits
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.hmmer_search_inputs import build_hmmer_search_sheet, iter_hmmer_stdout_events, iter_hmmer_table_rows

VERSION = 'phmmer_printed_alignment_with_hmmer_sheet'
NATIVE_ROWS = TableDeclaration(
    name='a101_phmmer_native_rows',
    columns=('capture', 'ordinal', 'kind', 'role', 'record_key', 'query_key', 'query_occurrence', 'target_name',
             'match_key', 'data'),
    key=('capture', 'ordinal'))


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


class PhmmerGradingValues:
    def _rows(self, kind, limit=None, **where):
        """The native rows of this capture of ``kind`` whose columns equal ``where``, in ordinal order."""
        rows = self.store.table(NATIVE_ROWS).select({'capture': self.capture, 'kind': kind, **where}, limit=limit)
        return [deepcopy(row['data']) for row in sorted(rows, key=lambda row: row['ordinal'])]

    def _matching(self, kind, role, key):
        # Fetch at most two rows: uniqueness is the only permission to join.
        return self._rows(kind, limit=2, role=role, match_key=key)

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
        query_rows = self._rows('query', limit=2, record_key=printed['query_record_key'])
        if len(query_rows) != 1:
            raise ValueError('phmmer_grading_query_association_missing')
        query = query_rows[0]
        if (query.get('occurrence'), query.get('name'), query.get('length')) != (0, self.query_name, len(self.sequence)):
            raise ValueError('phmmer_grading_unexpected_query')
        domain = self._merge(printed, 'domain', 'domtblout')
        hits = self._rows('hit', limit=2, role='stdout', query_key=printed['query_record_key'],
                          target_name=alignment['reference_id'])
        associated_hits = []
        if len(hits) == 1:
            hit = self._merge(hits[0], 'hit', 'tblout')
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
            collections[plural] = self._rows(kind, query_key=printed['query_record_key'])
        # Native single-query summary and annotations are bounded independently
        # of the hit population. All per-target rows remain in the disk index.
        annotations = [deepcopy(row['data']) for row in sorted(
            self.store.table(NATIVE_ROWS).select({'capture': self.capture, 'kind': 'annotation'}),
            key=lambda row: row['ordinal']) if row['query_key'] in (printed['query_record_key'], None)]
        query['complete'] = any(row.get('native_query_terminated') for row in annotations)
        complete = bool(self.termination) and all(self.termination.values()) and query['complete']
        native = {'schema': 'hmmer_search_native',
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


class GradingRows(PhmmerGradingValues):
    """The worker's associations (``phmmer_grading_worker.GradingRows``): the native rows of one capture, ingested
    into ``NATIVE_ROWS`` through ``store`` (the tool's scoped store)."""

    def __init__(self, store, request, *, capture, query_name, sequence, error):
        self.store, self.request, self.error, self.capture = store, request, error, capture
        self.query_name, self.sequence = query_name, sequence
        self.artifacts = deepcopy(request.get('grading_artifacts', {}))
        self.termination = {}
        self.version = None
        self.version_conflict = False
        self.invalid_roles = set()
        self.failed = None
        self._ordinal = 0

    def _ingest(self, event, role):
        kind, row = event['kind'], event['data']
        key = domain_key(row) if kind == 'domain' else hit_key(row) if kind == 'hit' else None
        self._ordinal += 1
        self.store.table(NATIVE_ROWS).put({
            'capture': self.capture, 'ordinal': self._ordinal, 'kind': kind, 'role': role,
            'record_key': row.get('record_key'), 'query_key': row.get('query_record_key'),
            'query_occurrence': row.get('query_occurrence', row.get('occurrence')),
            'target_name': row.get('target_name'), 'match_key': key, 'data': json.loads(encoded(row))})
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

    def capture_rows(self):
        """The old ``capture``: every native row of the retained stdout and tables."""
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


def file_digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def extract(store, request, *, capture):
    """Bounded extraction of native phmmer measurements (the old ``phmmer_result_worker.extract``).

    Each independent row is kept: a damaged later domain or a resource failure cannot erase preceding rows. Pure
    HMMER graders calculate native numerical components without scientific interpretation, selection, yield
    estimation or episode decisions. Returns the measurements (references, then alignments, each with its grading
    and ``grading_identity``), the errors and the summary of the old ``summary.json``."""
    hits, refs, measurements, errors = {}, {}, [], []

    def error(data):
        errors.append(data)

    def emit(data):
        measurements.append(data)
    query = SeqIO.read(request['query_fasta'], 'fasta')
    sequence = str(query.seq).upper()
    if hashlib.sha256(sequence.encode()).hexdigest() != request['expected_query_sha256']:
        raise ValueError('native_query_does_not_match_canonical_operand')
    grading_rows = GradingRows(store, request, capture=capture, query_name=query.id, sequence=sequence, error=error)
    try:
        grading_rows.capture_rows()
    except (ValueError, OSError, UnicodeError) as failure:
        grading_rows.failed = 'phmmer_grading_native_capture_failed'
        error({'code': grading_rows.failed, 'phase': 'tool_grading',
               'exception_type': type(failure).__name__, 'detail': str(failure)})

    def ingest(event):
        row = event['data']
        if event['kind'] == 'error':
            error(row)
            return
        old = hits.get(row['reference_id'])
        if old is None:
            hits[row['reference_id']] = {'data': row, 'ambiguous': False, 'aligned': 0}
        elif {k: v for k, v in old['data'].items() if k != 'table_byte_span'} != {
                k: v for k, v in row.items() if k != 'table_byte_span'}:
            old['ambiguous'] = True
            error({'code': 'native_reference_identifier_ambiguous', 'reference_id': row['reference_id']})
    try:
        for event in hit_rows(request['hit_table'], query_id=query.id):
            ingest(event)
    except FileNotFoundError:
        error({'code': 'native_hit_table_unavailable'})
    for row in sequence_hits(request['native_text'], query_id=query.id, query_length=len(sequence)):
        hits.setdefault(row['reference_id'], {'data': row, 'ambiguous': False, 'aligned': 0})
    try:
        if request.get('database_sha256') and file_digest(request['reference_fasta']) != request['database_sha256']:
            raise ValueError('native_reference_database_identity_changed')
        for reference in (SeqIO.parse(request['reference_fasta'], 'fasta') if hits else ()):
            hit = hits.get(reference.id)
            if hit is None or hit['ambiguous']:
                continue
            symbols = str(reference.seq).upper()
            sha = hashlib.sha256(symbols.encode('ascii')).hexdigest()
            old = refs.get(reference.id)
            if old:
                if old['sequence_sha256'] != sha:
                    error({'code': 'native_reference_identifier_ambiguous', 'reference_id': reference.id})
                    hit['ambiguous'] = True
                continue
            refs[reference.id] = {**hit['data'], 'database_description': reference.description,
                                  'symbols': symbols, 'sequence_sha256': sha, 'length': len(symbols)}
        if request.get('database_sha256') and file_digest(request['reference_fasta']) != request['database_sha256']:
            # No selected reference can be published under an old database
            # identity after a concurrent modification of the live input.
            refs.clear()
            raise ValueError('native_reference_database_identity_changed')
    except (ValueError, UnicodeError) as failure:
        if str(failure) == 'native_reference_database_identity_changed':
            raise
        error({'code': 'native_reference_fasta_incomplete_or_invalid'})
    # Emit only unambiguous selected source identities after the full scan has
    # had a chance to reveal duplicate identifiers. Keep successful siblings.
    for identifier, body in refs.items():
        if not hits[identifier]['ambiguous']:
            emit({'kind': 'reference', **body})
    for event in alignment_rows(request['native_text'], query_id=query.id, query_length=len(sequence)):
        if event['kind'] == 'error':
            error(event['data'])
            continue
        row = event['data']
        native_id = row['reference_id']
        found = refs.get(native_id) if native_id in hits and not hits[native_id]['ambiguous'] else None
        if found is None:
            error({'code': 'native_alignment_reference_unresolved', 'reference_id': native_id,
                   'domain_index': row['domain_index'], 'byte_span': row['source_byte_span']})
            continue
        reference = found
        symbols = reference['symbols']
        qs, qe = row['query_interval_aa_zero_based_half_open']
        rs, re_ = row['reference_interval_aa_zero_based_half_open']
        try:
            intervals, paired, identical = alignment_geometry(row, sequence, symbols, qs, qe, rs, re_)
        except ValueError as failure:
            error({'code': str(failure), 'reference_id': native_id, 'domain_index': row['domain_index'],
                   'byte_span': row['source_byte_span']})
            continue
        measured = alignment_measurement(row, reference, sequence, intervals, paired, identical)
        try:
            grading = grading_rows.grade(measured, reference, symbols)
        except (ValueError, KeyError, TypeError) as failure:
            code = str(failure) if isinstance(failure, ValueError) else 'phmmer_grading_representation_failed'
            grading = {'sheet': None, 'scores': None, 'failure': {'code': code,
                'exception_type': type(failure).__name__, 'reference_id': native_id,
                'domain_index': row['domain_index'], 'byte_span': row['source_byte_span']}}
            error({'code': 'phmmer_grading_failed', 'phase': 'tool_grading', 'grading_failure': grading['failure']})
        measured.update(grading=grading, grading_version=VERSION, grading_identity=grading_identity(grading))
        emit(measured)
        hits[native_id]['aligned'] += 1
    for native_id, hit in hits.items():
        if not hit['ambiguous'] and hit['aligned'] == 0:
            error({'code': 'native_reported_hit_without_complete_alignment', 'reference_id': native_id})
    summary = {'version': VERSION, 'rows': len(measurements), 'errors': len(errors),
               'query_length': len(sequence), 'query_sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest()}
    return {'measurements': measurements, 'errors': errors, 'summary': summary, 'query_name': query.id,
            'termination': dict(grading_rows.termination)}
