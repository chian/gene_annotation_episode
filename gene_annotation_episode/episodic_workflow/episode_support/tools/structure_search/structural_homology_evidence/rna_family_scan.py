"""A102's one-shot tool ``rna_family_scan`` (row R1 of ``a102_tree.md``; design note ``docs/plan/designs/a102_rna_tools.md``): which
structured RNA family (Rfam) is the target, by Infernal's covariance models. The shape of A101's ``hmmer_profile_scan``: a local job
through the job service, the database found through a manifest named in the head's settings; SOP Step 3: the model fills out one
JSON, ONE deterministic check, ONE function that runs the unit and grades it.

THE REQUEST (controlled fields): ``query_ref`` (an RNA sequence of the scope), ``database`` (a covariance database of the settings'
``covariance_databases``) and ``resource_id`` (a local resource). ``check_rna_family_scan_request`` is the one check. It refuses,
with the fix list (the field, a code and what to choose from): a query that is not a sequence of the scope, or not RNA (or not of
the molecules the caller names: ``molecules``, RNA by default); a database
that is not configured; a resource that is not local; a target already scanned (one scan of a target: a repeat adds nothing); a
program or a manifest file that is not there. A request that passes it simply works.

THE UNIT. One local job, ``cmscan`` by Rfam's documented command for annotating a sequence (docs.rfam.org, genome annotation):
``cmscan -Z <Mb> --cut_ga --rfam --nohmmonly --cpu 1 --tblout cmscan.tblout --fmt 2 --clanin Rfam.clanin -o cmscan.out Rfam.cm
query.fa`` with ``Z`` as Rfam defines it (the nucleotides searched, in millions, times 2 for the two strands: the query's length
times 2 over a million). The table and the report are kept as labelled data products (``rna_family_scan_results``, the table;
``rna_family_scan_report``, the program's report, written with ``-o``), the table is graded (``rna_family_scan_sheet``), and the
grading retained with a source record (provider ``rna_family_scan``, operand the query) and labelled a ``tool_grading_sheet``. A scan
that finds no family is completed with outcome ``no_family``. A job that does not end well is a ``failed`` outcome with its code,
reported once. Writes only through ``ctx.store``; settings: ``infernal_executable_directory`` and ``covariance_databases``."""
import hashlib
import json
import os
from pathlib import Path

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence import rna_family_scan_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    _choose)

PROVIDER = sheets.PROVIDER
JOB_NAME = 'rna_family_scan'
PROGRAM = 'cmscan'
REQUEST_FIELDS = ('query_ref', 'database', 'resource_id')
QUERY_FILE, TBLOUT_FILE, REPORT_FILE = 'query.fa', 'cmscan.tblout', 'cmscan.out'
# Rfam's documented command with one CPU; the clan file and the database follow, then the query (``job_argv``).
OPTIONS = ['--cut_ga', '--rfam', '--nohmmonly', '--cpu', '1']
TABLE_KIND, REPORT_KIND = 'rna_family_scan_results', 'rna_family_scan_report'
# The record types that carry a sequence: what the query is found among.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')
OWN_FAILURE_CODES = ('job_not_accepted', 'job_not_fetched', 'cmscan_exit_nonzero', 'output_missing', 'grading_refused')


def z_megabases(length):
    """``-Z`` as Rfam defines it: the nucleotides searched in millions, times two for the two strands."""
    return 2 * length / 1_000_000


def job_argv(executable, manifest, length):
    """The command of the scan: ``cmscan -Z <Mb> --cut_ga --rfam --nohmmonly --cpu 1 --tblout <file> --fmt 2 --clanin <file> -o
    <file> <database> <query>`` (paths of the database as the manifest gives them; the query and the outputs in the job's directory)."""
    files = manifest['files']
    return [str(executable), '-Z', '%.6f' % z_megabases(length), *OPTIONS, '--tblout', TBLOUT_FILE, '--fmt', '2',
            '--clanin', files['clan_file']['path'], '-o', REPORT_FILE, files['covariance_database']['path'], QUERY_FILE]


def scan_settings(manifest, length):
    """The settings of a scan's data products (closed JSON): the program, the database's name and version, the cut-off and the
    mode options and ``Z``."""
    return {'program': PROGRAM, 'database': manifest['name'], 'database_version': manifest['version'], 'cutoff': OPTIONS[0],
            'mode': OPTIONS[1:3], 'z_megabases': z_megabases(length)}


def rna_scan_inputs(reader):
    """The scans the caller holds, as ``{scan source reference: {'query_ref', 'database', 'outcome', 'families'}}`` (``families``:
    ``[{'accession', 'name', 'best_value'}]``, the sheet's candidates in its order), read from the retained sheets."""
    held = {}
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        (entry,) = source_tool_grading_entries(reader, source['id'])
        sheet = entry['grading']['sheet']
        held[source['id']] = {'query_ref': sheet['query_ref'], 'database': sheet['database'], 'outcome': sheet['outcome'],
                              'families': [{'accession': item['identifier'], 'name': item['name'], 'best_value': item['best_value']}
                                           for item in sheet['candidates']]}
    return held


def _programs(directory, names):
    return [{'code': 'program_missing', 'field': 'settings', 'detail': name} for name in names
            if not os.access(Path(directory) / name, os.X_OK)]


def check_rna_family_scan_request(request, *, sequences, scope_subjects, resources, scanned, databases, executable_directory,
                                  molecules=('rna',)):
    """The things to fix in an ``rna_family_scan`` request, before anything runs; an empty list means it can run.

    ``request`` holds ``query_ref``, ``database`` and ``resource_id``. ``sequences`` is ``{record: molecule}`` of the sequence
    records the caller holds, ``scope_subjects`` the subjects of its scope, ``resources`` ``{resource id: kind}``, ``scanned`` the
    targets already scanned and ``databases`` ``{name: manifest path}`` (the settings' ``covariance_databases``). ``molecules`` are
    the molecules of a sequence the caller scans: RNA by default; a caller that scans DNA names ``dna`` (``cmscan`` reads a T as a U,
    Easel's RNA alphabet, and searches both strands, and ``-Z`` is the letters searched times two whatever the molecule, so the scan
    itself is the same)."""
    query, database, resource = request['query_ref'], request['database'], request['resource_id']
    admitted = [ref for ref in scope_subjects if sequences.get(ref) in molecules and ref not in scanned]
    problems = []
    if query not in scope_subjects or sequences.get(query) not in molecules:
        problems.append(_choose('query_ref', 'query_is_not_an_' + '_or_'.join(molecules) + '_sequence_of_the_scope',
                                choose_from=admitted))
    elif query in scanned:
        problems.append(_choose('query_ref', 'target_already_scanned', choose_from=admitted))
    if database not in databases:
        problems.append(_choose('database', 'database_is_not_configured', choose_from=sorted(databases)))
    elif not os.access(databases[database], os.R_OK):
        problems.append({'code': 'manifest_missing', 'field': 'settings', 'detail': database})
    if resources.get(resource) != 'local':
        problems.append(_choose('resource_id', 'resource_is_not_local', choose_from=[name for name, kind in resources.items()
                                                                                       if kind == 'local']))
    problems.extend(_programs(executable_directory, (PROGRAM,)))
    return problems


def _failed(code, record_refs=(), **detail):
    """The outcome of a unit that failed after its check passed (the code is one of ``OWN_FAILURE_CODES``)."""
    return {'status': 'failed', 'failure_code': code, 'retryable': False, 'record_refs': list(record_refs), 'graded_refs': [],
            'detail': detail}


async def rna_family_scan(ctx, *, query_ref, database, resource_id):
    """Scan the held RNA ``query_ref`` against the covariance database ``database`` on the local resource, grade the table and keep the
    answer and the grading through custody (see the module). ``ctx`` is the tool's ``UnitContext``; ``ctx.settings`` holds
    ``infernal_executable_directory`` and ``covariance_databases``."""
    store = ctx.store
    manifest_path = Path(ctx.settings['covariance_databases'][database])
    manifest = json.loads(manifest_path.read_text())
    index = json.loads(Path(manifest['files']['family_index']['path']).read_text())
    record = store.get(query_ref)
    residues = store.get_artifact(record['sequence_ref']).decode('ascii').strip().upper()
    manifest_ref = store.artifact(manifest_path.read_bytes(), 'application/json')   # the database's identity
    executable = (Path(ctx.settings['infernal_executable_directory']) / PROGRAM).resolve()
    argv = job_argv(executable, manifest, len(residues))
    query = store.artifact(('>' + query_ref + '\n' + residues + '\n').encode(), 'text/x-fasta')
    request_ref = store.artifact(canonical({'argv': argv, 'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                                            'job': job_handle(ctx.operation_key, resource_id, JOB_NAME)}), 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, argv, {}, wait=True, inputs={QUERY_FILE: query}, name=JOB_NAME)
    if ran['status'] != 'completed':
        return _failed('job_not_accepted' if ran['launch']['status'] != 'completed' else 'job_not_fetched', [request_ref])
    jobs = [ran['launch']['handoff_ref'], ran['fetch']['closure_ref']]
    if ran['returncode'] != 0:
        return _failed('cmscan_exit_nonzero', [request_ref, *jobs], returncode=ran['returncode'], stderr=ran['stderr'][-2000:])
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    if TBLOUT_FILE not in fetched or REPORT_FILE not in fetched:
        return _failed('output_missing', [request_ref, *jobs])
    try:
        sheet = sheets.grade_rna_family_scan(
            store.get_artifact(fetched[TBLOUT_FILE]).decode(), index=index, query={'query_ref': query_ref, 'length': len(residues)},
            database=manifest, z_megabases=z_megabases(len(residues)))
    except ValueError as error:
        return _failed('grading_refused', [request_ref, *jobs], reason=str(error))
    grading = {'sheet': sheet}
    settings = scan_settings(manifest, len(residues))
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=fetched[TBLOUT_FILE], grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': manifest['name'], 'uri': None, 'artifact_ref': fetched[TBLOUT_FILE], 'text_ref': None,
            'request_ref': None, 'version': manifest['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, request_ref, fetched[REPORT_FILE]], 'operand_refs': [query_ref]}, origin='tool')
        used = [record['sequence_ref'], manifest_ref]
        table, report = (record_product(store, artifact_ref=fetched[name], kind=kind, generated_by=source['id'], used=used,
                                        settings=settings) for name, kind in ((TBLOUT_FILE, TABLE_KIND), (REPORT_FILE, REPORT_KIND)))
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[fetched[TBLOUT_FILE], fetched[REPORT_FILE], *used],
                                                 derived_from=[table['id'], report['id']])
    graded = [source['id'], grading_ref, table['id'], report['id'], grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': graded, 'record_refs': [*graded, *jobs],
            'source_ref': source['id'], 'rna_scan_outcome': sheet['outcome'], 'hit_count': sheet['hit_count'],
            'overlapped_hit_count': sheet['overlapped_hit_count'], 'candidates_measured': sheet['candidates_measured'],
            'families_in_database': sheet['families_in_database']}


__all__ = ['OWN_FAILURE_CODES', 'PROVIDER', 'REQUEST_FIELDS', 'TABLE_KIND', 'REPORT_KIND', 'check_rna_family_scan_request', 'job_argv',
           'rna_family_scan', 'rna_scan_inputs', 'z_megabases']
