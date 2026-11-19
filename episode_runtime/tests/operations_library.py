"""Test-only library functions that use the system operations of the scoped store the way a support-library
function does: each receives the custody-scoped store (or the read-only reader) and calls only what it offers.

Each function names the raw-Store pattern it stands in for (``carry_over_guide/store-access.md``)."""
import json
from pathlib import Path
import time

from episode_runtime import TableDeclaration
from gene_annotation_episode.domain import identity

from .sheet_library import write_cell

# Was: ``CREATE TABLE IF NOT EXISTS provider_jobs``, ``provider_job_failures`` and ``store.db.commit()`` in a
# constructor. A declared table needs no statement and no commit.
JOBS = TableDeclaration(name='probe_provider_jobs', columns=('job', 'state', 'request_ref'), key=('job',),
                        record_refs=('request_ref',))
FAILURES = TableDeclaration(name='probe_provider_job_failures', columns=('job', 'cause'), key=('job',))
SOURCE = {'provider': 'probe', 'accession': None, 'uri': None, 'request_ref': None, 'version': None,
          'retrieved_at': None}


def register_job(store, job, request):
    """Record a job and its request in one step (was: ``INSERT INTO provider_jobs`` then ``store.db.commit()``)."""
    with store.transaction():
        request_ref = store.artifact(json.dumps(request, sort_keys=True), 'application/json')
        return store.table(JOBS).put({'job': job, 'state': 'submitted', 'request_ref': request_ref})


def record_failure(store, job, cause):
    """The one current cause of a job's failure (was: ``INSERT OR REPLACE INTO provider_job_failures``)."""
    return store.table(FAILURES).put({'job': job, 'cause': cause})


def clear_failure(store, job):
    """The job has no current failure any more (was: ``DELETE FROM provider_job_failures WHERE job_ref=?``)."""
    return store.table(FAILURES).withdraw({'job': job})


def current_failure(reader, job):
    """The current cause of the job's failure, or ``None`` (was: ``SELECT data FROM provider_job_failures``)."""
    rows = reader.table(FAILURES).select({'job': job})
    return rows[0]['cause'] if rows else None


def failure_history(reader, job):
    """Every failure row of the job, withdrawn ones too, with its mark and revision."""
    return [[row['cause'], row['withdrawn'], row['revision']]
            for row in reader.table(FAILURES).select({'job': job}, withdrawn=True)]


def newest_jobs_first(reader, states):
    """A wider query done on the selected rows: the jobs in one of ``states``, newest first (was: ``WHERE state IN
    (...) ORDER BY rowid DESC``)."""
    return [row['job'] for row in reversed(reader.table(JOBS).select()) if row['state'] in states]


def publish(store, kind, record, created):
    """Write a record and note it in ``created`` when the Episode did not hold it before (was: ``SELECT 1 FROM
    records WHERE id=?`` on the identity the write will have, then ``store.put``)."""
    candidate = identity(kind, {'origin': 'tool', 'record': record})
    new = not store.holds(candidate)
    row = store.put(kind, record, origin='tool')
    if new:
        created.append(row['id'])
    return row['id']


def update_sheet(store, sheet, cell, value, source_ref, dependents):
    """Write a cell and refresh the dependent sheets, each by this same function; only the outermost call
    refreshes (was: the attribute ``store._literature_sheet_updating`` set on the Store object)."""
    with store.section('probe_sheet_updating') as outer:
        with store.transaction():
            write_cell(store, sheet, cell, value, source_ref)
            if not outer:
                return ['inner:' + sheet]
            done = ['outer:' + sheet]
            for dependent in dependents:
                done += update_sheet(store, dependent, cell, value, source_ref, dependents)
            return done


def count_residues(sequence_path, counts_path, *, cancel_event):
    """The computation of ``residue_counts``, run in a worker thread: it is given files, never the Store."""
    text = Path(sequence_path).read_text()
    counts = {residue: text.count(residue) for residue in sorted(set(text))}
    Path(counts_path).write_text(json.dumps(counts, sort_keys=True))
    return {'residues': len(text), 'cancelled': cancel_event.is_set()}


async def residue_counts(store, sequence_ref):
    """Count the residues of a held sequence artifact in a worker thread (was: ``Store(store_path)`` opened in the
    thread). The input is read through custody into a scratch file, the thread computes on files of its own,
    and the unit writes the result."""
    with store.scratch('residues') as scratch:
        sequence = scratch.copy_artifact(sequence_ref, 'inputs/sequence.txt')
        summary = await scratch.compute(count_residues, sequence, scratch.path / 'counts.json')
        counts_ref = store.artifact_file(scratch.path / 'counts.json', 'application/json')
        where = scratch.path
    return {**summary, 'counts_ref': counts_ref, 'scratch_removed': not where.exists()}


def wait_for_cancel(directory, seen, started, *, cancel_event):
    """A computation that works until it is cancelled, then finishes its file: the directory must still be there."""
    started.set()
    cancel_event.wait()
    time.sleep(0.3)
    (directory / 'finished.txt').write_text('finished after the cancellation')
    seen.update(path=str(directory), directory_existed=directory.is_dir(),
                finished=(directory / 'finished.txt').read_text())


def read_in_thread(store, ref, *, cancel_event):
    """What a worker thread must not do: read the Store."""
    return store.get_artifact(ref).decode()


def write_in_thread(store, *, cancel_event):
    return store.artifact('written by a worker thread', 'text/plain')


def capture_download(store, chunks, media_type):
    """Keep a download that arrives in chunks as an artifact (was: a temporary file in the artifact directory
    and a raw ``INSERT INTO artifacts``)."""
    return store.artifact_stream(chunks, media_type)


def fetch(store, cache, url, download):
    """The bytes of ``url`` as an artifact this Episode holds; ``download`` is asked only when no Episode kept
    them in the cache (was: a lookup in ``records`` for a source another Episode had fetched)."""
    data = cache.get('fetched', {'url': url})
    asked = data is None
    if asked:
        data = download(url)
        cache.put('fetched', {'url': url}, data)
    return store.artifact(data, 'text/plain'), asked


def scope_spans(reader, scope, target_ref=None):
    return list(reader.iter_scope_coverage(scope, target_ref))


# -- the original reads of a read library ------------------------------------------------------------------------
def read_page(reader, library_ref, **page):
    """One page of the original reads of a held read library (was: ``libraries.member_page(store, library_ref,
    scope=..., selection_ref=..., offset=..., limit=...)``, the nine copies of ``library_targets.py`` joining
    ``material_members`` with ``library_selection_members`` on the raw connection)."""
    return reader.library_members(library_ref, **page)


def freeze_reads(store, library_ref, **chosen):
    """Freeze an explicit selection of a held library's reads (was: ``libraries.select(store, library_ref,
    scope=..., member_refs=... | ordinal_ranges=...)``, a ``read_selection`` record and an ``INSERT`` of its rows
    into ``library_selection_members``)."""
    return store.select_library_members(library_ref, **chosen)


def selected_reads(reader, selection_ref):
    """The references of the reads a held selection froze, in order (was: ``SELECT read_ref FROM
    library_selection_members WHERE selection_ref=? ORDER BY read_ref``)."""
    return reader.selection_members(selection_ref)


def selected_fasta(reader, selection_ref):
    """The reads of a held selection as FASTA, in the order of their references (was: the ``queries.fasta`` of a
    read mapping, written from that ``SELECT`` with a ``store.get`` of each read). The Episode holds the
    selection, the library and its collections, not each read: a read's record comes with the library's page of
    the selection, and its sequence is read through its collection."""
    selection = reader.require(selection_ref, {'read_selection'})
    reads, offset = {}, 0
    while offset is not None:
        page = reader.library_members(selection['library_ref'], selection_ref=selection_ref, offset=offset)
        reads.update((row['id'], row) for row in page['members'])
        offset = page['next_offset']
    return ''.join(
        '>' + ref + '\n' + reader.material_member(reads[ref]['member_ref'], limit=reads[ref]['length'])['sequence']
        + '\n' for ref in reader.selection_members(selection_ref))


# -- the diagnostics of tool outcomes ---------------------------------------------------------------------------
def may_be_read_as_a_source(reader, reference):
    """Whether a held reference may be handed on as source material: not when it is the diagnostic of one of the
    Episode's tool outcomes (was: ``SELECT 1 FROM tool_operations WHERE
    json_extract(result,'$.feedback.diagnostic_ref')=?`` on the deleted operation ledger)."""
    return not reader.is_diagnostic_ref(reference)
