"""The parts-discovery tool ``find_rna_genes``: the RNA genes of the piece, by Infernal's covariance models of Rfam. One fixed
workflow, called the same way for any piece: ONE local job through the job service, ``cmscan`` over the whole piece by Rfam's own
documented command for annotating a sequence (docs.rfam.org, genome annotation): ``cmscan -Z <Mb> --cut_ga --rfam --nohmmonly
--cpu 1 --tblout cmscan.tblout --fmt 2 --clanin Rfam.clanin -o cmscan.out Rfam.cm query.fa`` with ``Z`` as Rfam defines it (the
nucleotides searched in millions, times 2 for the two strands). Each family's own gathering threshold decides what is reported;
both strands are searched and reported.

THE REQUEST: ``piece_ref`` and ``resource_id`` (a local resource of the job service). ``check_find_rna_genes_request`` is the one
check: it refuses a piece that is not the scope's piece, a resource that is not local, a piece already scanned (one scan of a
piece: a repeat adds nothing), and a program or database file that is not there. A request that passes simply works.

THE UNIT: stage the piece, run the job, read the table, grade (``rna_gene_sheet``), keep the table and the program's report as the
data products ``rna_family_scan_results`` and ``rna_family_scan_report`` and the grading with a source record (provider
``rna_gene_finding``, operand the piece) labelled a ``tool_grading_sheet`` product. A job that does not end well is a ``failed``
outcome with its code, reported once. Writes only through ``ctx.store``. Settings: ``infernal_executable_directory`` (the
directory of ``cmscan``) and ``covariance_database_manifest`` (the path of the Rfam manifest: the database, its clan file and its
family index)."""
import hashlib
import json
import os
from pathlib import Path

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery import rna_gene_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.held_sheets import piece_sequence
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product

PROVIDER = sheets.PROVIDER
TOOL_NAME = 'find_rna_genes'
PROGRAM = 'cmscan'
QUERY_FILE, TBLOUT_FILE, REPORT_FILE = 'query.fa', 'cmscan.tblout', 'cmscan.out'
OPTIONS = ['--cut_ga', '--rfam', '--nohmmonly', '--cpu', '1']
TABLE_KIND, REPORT_KIND = 'rna_family_scan_results', 'rna_family_scan_report'
OWN_FAILURE_CODES = ('job_not_accepted', 'job_not_fetched', 'cmscan_exit_nonzero', 'output_missing', 'grading_refused')


def z_megabases(length):
    """``-Z`` as Rfam defines it: the nucleotides searched in millions, times two for the two strands."""
    return 2 * length / 1_000_000


def job_argv(executable, manifest, length):
    """The command of the scan (paths of the database as the manifest gives them; the query and the outputs in the job's
    directory)."""
    files = manifest['files']
    return [str(executable), '-Z', '%.6f' % z_megabases(length), *OPTIONS, '--tblout', TBLOUT_FILE, '--fmt', '2',
            '--clanin', files['clan_file']['path'], '-o', REPORT_FILE, files['covariance_database']['path'], QUERY_FILE]


def scan_settings(manifest, length):
    """The settings of a scan's data products (closed JSON)."""
    return {'program': PROGRAM, 'database': manifest['name'], 'database_version': manifest['version'], 'cutoff': OPTIONS[0],
            'mode': OPTIONS[1:3], 'z_megabases': z_megabases(length)}


def check_find_rna_genes_request(request, *, piece_ref, resources, scanned, manifest_path, executable_directory):
    """The things to fix in a ``find_rna_genes`` request, before anything runs; an empty list means it can run. ``resources`` is
    ``{resource id: kind}``, ``scanned`` the pieces already scanned."""
    problems = []
    if request['piece_ref'] != piece_ref:
        problems.append({'code': 'piece_is_not_the_scope_piece', 'field': 'piece_ref', 'choose_from': [piece_ref]})
    elif request['piece_ref'] in scanned:
        problems.append({'code': 'piece_already_scanned', 'field': 'piece_ref', 'choose_from': []})
    if resources.get(request['resource_id']) != 'local':
        problems.append({'code': 'resource_is_not_local', 'field': 'resource_id',
                         'choose_from': [name for name, kind in resources.items() if kind == 'local']})
    if not os.access(manifest_path, os.R_OK):
        problems.append({'code': 'manifest_missing', 'field': 'settings', 'detail': 'covariance_database_manifest'})
    if not os.access(Path(executable_directory) / PROGRAM, os.X_OK):
        problems.append({'code': 'program_missing', 'field': 'settings', 'detail': PROGRAM})
    return problems


def _failed(code, record_refs=(), **detail):
    """The outcome of a unit that failed after its check passed (the code is one of ``OWN_FAILURE_CODES``)."""
    return {'status': 'failed', 'failure_code': code, 'retryable': False, 'record_refs': list(record_refs), 'graded_refs': [],
            'detail': detail}


async def find_rna_genes(ctx, *, piece_ref, resource_id):
    """Scan the held piece ``piece_ref`` against the covariance database on the local resource, grade the table and keep the answer
    and the grading through custody (see the module). ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    manifest_path = Path(ctx.settings['covariance_database_manifest'])
    manifest = json.loads(manifest_path.read_text())
    index = json.loads(Path(manifest['files']['family_index']['path']).read_text())
    sequence_ref = store.get(piece_ref)['sequence_ref']
    residues = piece_sequence(store, piece_ref)
    manifest_ref = store.artifact(manifest_path.read_bytes(), 'application/json')   # the database's identity
    executable = (Path(ctx.settings['infernal_executable_directory']) / PROGRAM).resolve()
    argv = job_argv(executable, manifest, len(residues))
    query = store.artifact(('>' + piece_ref + '\n' + residues + '\n').encode(), 'text/x-fasta')
    request_ref = store.artifact(canonical({'argv': argv, 'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                                            'job': job_handle(ctx.operation_key, resource_id, TOOL_NAME)}), 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, argv, {}, wait=True, inputs={QUERY_FILE: query}, name=TOOL_NAME)
    if ran['status'] != 'completed':
        return _failed('job_not_accepted' if ran['launch']['status'] != 'completed' else 'job_not_fetched', [request_ref])
    jobs = [ran['launch']['handoff_ref'], ran['fetch']['closure_ref']]
    if ran['returncode'] != 0:
        return _failed('cmscan_exit_nonzero', [request_ref, *jobs], returncode=ran['returncode'], stderr=ran['stderr'][-2000:])
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    if TBLOUT_FILE not in fetched or REPORT_FILE not in fetched:
        return _failed('output_missing', [request_ref, *jobs])
    try:
        sheet = sheets.grade_rna_gene_finding(
            store.get_artifact(fetched[TBLOUT_FILE]).decode(), index=index, piece={'piece_ref': piece_ref, 'length': len(residues)},
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
            'auxiliary_artifact_refs': [grading_ref, request_ref, fetched[REPORT_FILE]], 'operand_refs': [piece_ref]}, origin='tool')
        used = [sequence_ref, manifest_ref]
        table, report = (record_product(store, artifact_ref=fetched[name], kind=kind, generated_by=source['id'], used=used,
                                        settings=settings) for name, kind in ((TBLOUT_FILE, TABLE_KIND), (REPORT_FILE, REPORT_KIND)))
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[fetched[TBLOUT_FILE], fetched[REPORT_FILE], *used],
                                                 derived_from=[table['id'], report['id']])
    graded = [source['id'], grading_ref, table['id'], report['id'], grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': graded, 'record_refs': [*graded, *jobs],
            'source_ref': source['id'], 'hit_count': sheet['hit_count'], 'part_count': sheet['part_count'],
            'part_bit_score_sum': sheet['part_bit_score_sum']}


__all__ = ['OWN_FAILURE_CODES', 'PROVIDER', 'TOOL_NAME', 'check_find_rna_genes_request', 'find_rna_genes', 'job_argv',
           'z_megabases']
