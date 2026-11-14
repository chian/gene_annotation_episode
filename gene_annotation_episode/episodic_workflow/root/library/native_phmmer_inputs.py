"""Original native PHMMER input custody from an authenticated job handoff."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NativePhmmerInput:
    query_ref: str
    query_fasta: Path
    reference_fasta: Path
    native_text: Path
    hit_table: Path
    database_sha256: str
    executable_sha256: str
    provenance: dict
    domain_table: Path | None = None

    @classmethod
    def from_job(cls, jobs, handoff):
        jobs.receive(handoff)
        job = jobs._row(handoff['job_ref'])
        directory = jobs._directory(handoff['job_ref'])
        handle = jobs._handle(handoff['job_ref']).read()
        return cls(job['query_ref'], directory/'query.faa', directory/'references.faa',
            jobs.result_file(handoff, 'native_text'), directory/'hits.tbl',
            jobs.config['reference_database']['sha256'], jobs.config['executable']['sha256'],
            {'job_ref': handoff['job_ref'], 'registry_ref': handoff['registry_ref'],
             'native_handle': handle,
             'native_parameters': {'command': handle['command'], 'cpu': job['cpu'],
                                   'search_mode': job['search_mode']}}, directory/'domains.tbl')


