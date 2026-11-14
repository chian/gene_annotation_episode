"""Store-free, bounded extraction of native phmmer measurements to disk.

SQLite commits each independent row. A damaged later domain or a resource
failure cannot erase preceding committed rows. Pure HMMER graders calculate
native numerical components without scientific interpretation, selection,
yield estimation or episode decisions.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from Bio import SeqIO

from .phmmer_format import alignment_rows, hit_rows, paired_segments, sequence_hits
from .phmmer_grading_worker import VERSION, GradingRows, grading_identity


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def file_digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def extract(request):
    directory = Path(request['directory'])
    db = sqlite3.connect(directory/'measurements.sqlite')
    db.executescript('''
    CREATE TABLE hits (id TEXT PRIMARY KEY,data TEXT NOT NULL,ambiguous INTEGER NOT NULL,aligned INTEGER NOT NULL);
    CREATE TABLE refs (id TEXT PRIMARY KEY,data TEXT NOT NULL);
    CREATE TABLE measurements (ordinal INTEGER PRIMARY KEY,data TEXT NOT NULL);
    CREATE TABLE errors (ordinal INTEGER PRIMARY KEY,data TEXT NOT NULL);
    ''')
    def error(data):
        with db:
            db.execute('INSERT INTO errors VALUES(NULL,?)', (encoded(data),))
    def emit(data):
        with db:
            db.execute('INSERT INTO measurements VALUES(NULL,?)', (encoded(data),))
    query = SeqIO.read(request['query_fasta'], 'fasta')
    sequence = str(query.seq).upper()
    if hashlib.sha256(sequence.encode()).hexdigest() != request['expected_query_sha256']:
        raise ValueError('native_query_does_not_match_canonical_operand')
    grading_rows = GradingRows(db, request, query_name=query.id, sequence=sequence, error=error)
    try:
        grading_rows.capture()
    except (ValueError, OSError, UnicodeError) as failure:
        grading_rows.failed = 'phmmer_grading_native_capture_failed'
        error({'code': grading_rows.failed, 'phase': 'tool_grading',
               'exception_type': type(failure).__name__, 'detail': str(failure)})
    def ingest(event):
        row = event['data']
        if event['kind'] == 'error':
            error(row)
            return
        old = db.execute('SELECT data FROM hits WHERE id=?', (row['reference_id'],)).fetchone()
        with db:
            if old is None:
                db.execute('INSERT INTO hits VALUES(?,?,0,0)', (row['reference_id'], encoded(row)))
            elif {k:v for k,v in json.loads(old[0]).items() if k != 'table_byte_span'} != {
                    k:v for k,v in row.items() if k != 'table_byte_span'}:
                db.execute('UPDATE hits SET ambiguous=1 WHERE id=?', (row['reference_id'],))
                error({'code': 'native_reference_identifier_ambiguous', 'reference_id': row['reference_id']})
    try:
        for event in hit_rows(request['hit_table'], query_id=query.id):
            ingest(event)
    except FileNotFoundError:
        error({'code': 'native_hit_table_unavailable'})
    for row in sequence_hits(request['native_text'], query_id=query.id, query_length=len(sequence)):
        with db:
            db.execute('INSERT OR IGNORE INTO hits VALUES(?,?,0,0)', (row['reference_id'], encoded(row)))
    try:
        if request.get('database_sha256') and file_digest(request['reference_fasta']) != request['database_sha256']:
            raise ValueError('native_reference_database_identity_changed')
        selected = db.execute('SELECT count(*) FROM hits').fetchone()[0]
        for reference in (SeqIO.parse(request['reference_fasta'], 'fasta') if selected else ()):
            hit = db.execute('SELECT data,ambiguous FROM hits WHERE id=?', (reference.id,)).fetchone()
            if hit is None or hit[1]:
                continue
            symbols = str(reference.seq).upper()
            sha = hashlib.sha256(symbols.encode('ascii')).hexdigest()
            old = db.execute('SELECT data FROM refs WHERE id=?', (reference.id,)).fetchone()
            if old:
                if json.loads(old[0])['sequence_sha256'] != sha:
                    error({'code': 'native_reference_identifier_ambiguous', 'reference_id': reference.id})
                    with db:
                        db.execute('UPDATE hits SET ambiguous=1 WHERE id=?', (reference.id,))
                continue
            path = directory/('reference-'+hashlib.sha256(reference.id.encode()).hexdigest()+'.symbols')
            path.write_text(symbols, encoding='ascii')
            row = {**json.loads(hit[0]), 'database_description': reference.description,
                   'sequence_file': path.name, 'sequence_sha256': sha,
                   'length': len(symbols)}
            with db:
                db.execute('INSERT INTO refs VALUES(?,?)', (reference.id, encoded(row)))
        if request.get('database_sha256') and file_digest(request['reference_fasta']) != request['database_sha256']:
            # No selected reference can be published under an old database
            # identity after a concurrent modification of the live input.
            with db:
                db.execute('DELETE FROM refs')
            raise ValueError('native_reference_database_identity_changed')
    except (ValueError, UnicodeError) as failure:
        if str(failure) == 'native_reference_database_identity_changed':
            raise
        error({'code': 'native_reference_fasta_incomplete_or_invalid'})
    # Emit only unambiguous selected source identities after the full scan has
    # had a chance to reveal duplicate identifiers. Keep successful siblings.
    for (body,) in db.execute('SELECT refs.data FROM refs JOIN hits USING(id) WHERE hits.ambiguous=0 ORDER BY refs.rowid'):
        emit({'kind': 'reference', **json.loads(body)})
    for event in alignment_rows(request['native_text'], query_id=query.id, query_length=len(sequence)):
        if event['kind'] == 'error':
            error(event['data'])
            continue
        row = event['data']
        native_id = row['reference_id']
        found = db.execute('SELECT refs.data FROM refs JOIN hits USING(id) WHERE id=? AND hits.ambiguous=0',
                           (native_id,)).fetchone()
        if found is None:
            error({'code': 'native_alignment_reference_unresolved', 'reference_id': native_id,
                   'domain_index': row['domain_index'], 'byte_span': row['source_byte_span']})
            continue
        reference = json.loads(found[0])
        symbols = (directory/reference['sequence_file']).read_text(encoding='ascii')
        qs, qe = row['query_interval_aa_zero_based_half_open']
        rs, re = row['reference_interval_aa_zero_based_half_open']
        try:
            if not (0 <= qs < qe <= len(sequence) and 0 <= rs < re <= len(symbols)):
                raise ValueError('native_alignment_interval_outside_operand')
            intervals, paired, identical = paired_segments(row, sequence, symbols)
        except ValueError as failure:
            error({'code': str(failure), 'reference_id': native_id, 'domain_index': row['domain_index'],
                   'byte_span': row['source_byte_span']})
            continue
        measured = {'kind': 'alignment', **row, 'paired_intervals': intervals, 'paired_residues': paired,
            'identical_paired_residues': identical, 'query_length': len(sequence),
            'reference_length': reference['length'], 'sequence_evalue': reference['sequence_evalue'],
            'sequence_bitscore': reference['sequence_bitscore']}
        try:
            grading = grading_rows.grade(measured, reference, symbols)
        except (ValueError, KeyError, TypeError) as failure:
            code = str(failure) if isinstance(failure, ValueError) else 'phmmer_grading_representation_failed'
            grading = {'sheet': None, 'scores': None, 'failure': {'code': code,
                'exception_type': type(failure).__name__, 'reference_id': native_id,
                'domain_index': row['domain_index'], 'byte_span': row['source_byte_span']}}
            error({'code': 'phmmer_grading_failed', 'phase': 'tool_grading', 'grading_failure': grading['failure']})
        try:
            body = encoded(grading)
            name = 'grading-'+hashlib.sha256(encoded([native_id, row['domain_index'],
                row['source_byte_span']]).encode()).hexdigest()+'.json'
            (directory/name).write_text(body)
            measured.update(grading_file=name, grading_sha256=hashlib.sha256(body.encode()).hexdigest(),
                grading_version=VERSION, grading_identity=grading_identity(grading))
        except OSError as failure:
            measured['grading_failure'] = {'code': 'phmmer_grading_storage_failed', 'errno': failure.errno}
            error({'code': 'phmmer_grading_storage_failed', 'phase': 'tool_grading', 'reference_id': native_id,
                   'domain_index': row['domain_index'], 'errno': failure.errno})
        emit(measured)
        with db:
            db.execute('UPDATE hits SET aligned=aligned+1 WHERE id=?', (native_id,))
    for native_id, ambiguous, aligned in db.execute('SELECT id,ambiguous,aligned FROM hits ORDER BY rowid'):
        if not ambiguous and aligned == 0:
            error({'code': 'native_reported_hit_without_complete_alignment', 'reference_id': native_id})
    summary = {'version': VERSION, 'rows': db.execute('SELECT count(*) FROM measurements').fetchone()[0],
               'errors': db.execute('SELECT count(*) FROM errors').fetchone()[0],
               'query_length': len(sequence), 'query_sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest()}
    db.close()
    (directory/'summary.json').write_text(encoded(summary))


if __name__ == '__main__':
    request = json.loads(Path(sys.argv[1]).read_text())
    try:
        extract(request)
    except (ValueError, OSError, UnicodeError, sqlite3.Error, MemoryError) as failure:
        code = (str(failure) if str(failure) in {'native_query_does_not_match_canonical_operand',
                                               'native_reference_database_identity_changed'}
                else 'native_memory_allocation_failed' if isinstance(failure, MemoryError)
                else 'native_parser_input_unavailable' if isinstance(failure, OSError)
                else 'native_parser_representation_failed')
        (Path(request['directory'])/'failure.json').write_text(encoded({'code': code,
            'exception_type': type(failure).__name__, 'errno': getattr(failure, 'errno', None)}))
        raise SystemExit(2)
