"""A102's one-shot tool ``rna_structure_agreement`` (row R2 of ``a102_tree.md``; design note ``docs/plan/designs/a102_rna_tools.md``): can
the target form the consensus base pairs of each family a held ``rna_family_scan`` listed. SOP Step 3: the model fills out one JSON,
ONE deterministic check, ONE function that runs the unit and grades it.

THE REQUEST (controlled fields): ``scan_ref`` (a held ``rna_family_scan`` source that lists at least two families and is not yet
tested) and ``resource_id`` (a local resource). ``check_rna_structure_agreement_request`` is the one check. It refuses, with the fix
list (the field, a code and what to choose from): a scan that is not a held scan (``scan_is_not_a_held_scan``); a scan that lists
fewer than two families (``scan_lists_fewer_than_two_families``: one family has no other to be told from, so the test could earn
nothing); a scan already tested (``agreement_test_already_run``); a resource that is not local; a program, the python or a manifest
file that is not there. A request that passes it simply works.

THE UNIT. One local job (``infernal_align_driver``: ``cmfetch`` of each family's model out of the database of the scan, then
``cmalign`` of the span of the target the scan's best hit of that family covers; a span on the minus strand is reverse complemented)
through the job service, for EVERY family of the scan, as one call measures the candidate set. The alignments are kept as labelled
data products (``rna_family_alignments``, one per family), graded (``rna_structure_agreement_sheet``), and the grading retained with a
source record (provider ``rna_structure_agreement``, operand the query) and labelled a ``tool_grading_sheet``. A job that does not
end well is a ``failed`` outcome with its code, reported once. Writes only through ``ctx.store``; settings: ``python_executable``,
``infernal_executable_directory`` and ``covariance_databases``."""
import inspect
import json
import os
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence import rna_structure_agreement_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products, record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence import (
    infernal_align_driver, rna_family_scan)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    _choose)

PROVIDER = sheets.PROVIDER
JOB_NAME = 'rna_structure_agreement'
REQUEST_FIELDS = ('scan_ref', 'resource_id')
PLAN_FILE, DRIVER_FILE = 'plan.json', 'driver.py'
DRIVER_SOURCE = Path(inspect.getsourcefile(infernal_align_driver)).read_bytes()
ALIGNMENTS_KIND = 'rna_family_alignments'
COMPLEMENT = {'A': 'U', 'U': 'A', 'G': 'C', 'C': 'G'}
MINIMUM_FAMILIES = 2
OWN_FAILURE_CODES = ('job_not_accepted', 'job_not_fetched', 'driver_exit_nonzero', 'alignment_report_missing',
                     'family_alignment_failed', 'grading_refused')


def _programs(directory, names):
    return [{'code': 'program_missing', 'field': 'settings', 'detail': name} for name in names
            if not os.access(Path(directory) / name, os.X_OK)]


def check_rna_structure_agreement_request(request, *, scans, tested, resources, executable_directory, python):
    """The things to fix in an ``rna_structure_agreement`` request, before anything runs; an empty list means it can run.

    ``request`` holds ``scan_ref`` and ``resource_id``. ``scans`` is ``rna_family_scan.rna_scan_inputs``; ``tested`` the scan
    references already tested (``candidate_measurements.held_rna_agreements``); ``resources`` ``{resource id: kind}``."""
    scan, resource = request['scan_ref'], request['resource_id']
    offered = [ref for ref, held in scans.items() if len(held['families']) >= MINIMUM_FAMILIES and ref not in tested]
    problems = []
    if scan not in scans:
        problems.append(_choose('scan_ref', 'scan_is_not_a_held_scan', choose_from=offered))
    elif len(scans[scan]['families']) < MINIMUM_FAMILIES:
        problems.append(_choose('scan_ref', 'scan_lists_fewer_than_two_families', choose_from=offered))
    elif scan in tested:
        problems.append(_choose('scan_ref', 'agreement_test_already_run', choose_from=offered))
    if resources.get(resource) != 'local':
        problems.append(_choose('resource_id', 'resource_is_not_local', choose_from=[name for name, kind in resources.items()
                                                                                       if kind == 'local']))
    problems.extend(_programs(executable_directory, ('cmfetch', 'cmalign')))
    if not os.access(python, os.X_OK):
        problems.append({'code': 'python_missing', 'field': 'settings'})
    return problems


def span_of(residues, hit):
    """The residues of the hit's span of the target, in the orientation of the model: the span as is for a ``+`` hit, its reverse
    complement for a ``-`` hit (the table gives sequence from > to there)."""
    span = residues[min(hit['seq_from'], hit['seq_to']) - 1:max(hit['seq_from'], hit['seq_to'])]
    return span if hit['strand'] == '+' else ''.join(COMPLEMENT[mark] for mark in reversed(span))


def best_hits(sheet):
    """``[(accession, name, the scan sheet's row of its best hit)]``, the candidates in the scan sheet's order."""
    return [(item['identifier'], item['name'], sheet['rows'][item['best_row']]) for item in sheet['candidates']]


def _failed(code, record_refs=(), **detail):
    """The outcome of a unit that failed after its check passed (the code is one of ``OWN_FAILURE_CODES``)."""
    return {'status': 'failed', 'failure_code': code, 'retryable': False, 'record_refs': list(record_refs), 'graded_refs': [],
            'detail': detail}


async def rna_structure_agreement(ctx, *, scan_ref, resource_id):
    """Align the span of each family of the held scan ``scan_ref`` to its model, grade the consensus pairs the target can form and
    keep the alignments and the grading through custody (see the module). ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    source = store.get(scan_ref)
    query_ref = source['operand_refs'][0]
    (entry,) = source_tool_grading_entries(store, scan_ref)
    scan = entry['grading']['sheet']
    manifest_path = Path(ctx.settings['covariance_databases'][scan['database']])
    manifest = json.loads(manifest_path.read_text())
    sequence_ref = store.get(query_ref)['sequence_ref']
    residues = store.get_artifact(sequence_ref).decode('ascii').strip().upper()
    chosen = best_hits(scan)
    manifest_ref = store.artifact(manifest_path.read_bytes(), 'application/json')   # the database's identity
    spans = {accession: store.artifact(('>' + accession + '_' + str(hit['seq_from']) + '-' + str(hit['seq_to']) + '\n'
                                        + span_of(residues, hit) + '\n').encode(), 'text/x-fasta') for accession, _, hit in chosen}
    plan = {'cmfetch': str((Path(ctx.settings['infernal_executable_directory']) / 'cmfetch').resolve()),
            'cmalign': str((Path(ctx.settings['infernal_executable_directory']) / 'cmalign').resolve()),
            'database': manifest['files']['covariance_database']['path'],
            'families': [{'accession': accession, 'span': 'span_' + accession + '.fa', 'model': 'model_' + accession + '.cm',
                          'alignment': accession + '.sto'} for accession, _, _ in chosen]}
    plan_ref = store.artifact(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode(), 'application/json')
    driver_ref = store.artifact(DRIVER_SOURCE, 'text/x-python')
    ran = await execute_on_local_resource(
        ctx, resource_id, [ctx.settings['python_executable'], DRIVER_FILE, PLAN_FILE], {}, wait=True,
        inputs={PLAN_FILE: plan_ref, DRIVER_FILE: driver_ref, **{'span_' + accession + '.fa': ref for accession, ref in spans.items()}},
        name=JOB_NAME)
    if ran['status'] != 'completed':
        return _failed('job_not_accepted' if ran['launch']['status'] != 'completed' else 'job_not_fetched', [plan_ref])
    jobs = [ran['launch']['handoff_ref'], ran['fetch']['closure_ref']]
    if ran['returncode'] != 0:
        return _failed('driver_exit_nonzero', [plan_ref, *jobs], returncode=ran['returncode'], stderr=ran['stderr'][-2000:])
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    if infernal_align_driver.OUTPUT_FILE not in fetched:
        return _failed('alignment_report_missing', [plan_ref, *jobs])
    report_ref = fetched[infernal_align_driver.OUTPUT_FILE]
    results = json.loads(store.get_artifact(report_ref))['families']
    failed = [row['accession'] for row in results if row['status'] != 'aligned']
    if failed:
        return _failed('family_alignment_failed', [plan_ref, report_ref, *jobs], families=failed)
    try:
        sheet = sheets.grade_rna_structure_agreement(
            [{'accession': accession, 'name': name, 'hit': hit,
              'stockholm': store.get_artifact(fetched[accession + '.sto']).decode()} for accession, name, hit in chosen],
            scan_source_ref=scan_ref, query_ref=query_ref)
    except ValueError as error:
        return _failed('grading_refused', [plan_ref, report_ref, *jobs], reason=str(error))
    grading = {'sheet': sheet}
    scan_tables = [row['id'] for row in products(store, rna_family_scan.TABLE_KIND) if row['generated_by'] == scan_ref]
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=report_ref, grading=grading)
        record = store.put('source', {
            'provider': PROVIDER, 'accession': manifest['name'], 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': manifest['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, plan_ref], 'operand_refs': [query_ref]}, origin='tool')
        alignments = [record_product(
            store, artifact_ref=fetched[accession + '.sto'], kind=ALIGNMENTS_KIND, generated_by=record['id'],
            used=[spans[accession], manifest_ref, plan_ref], derived_from=scan_tables,
            settings={'program': 'cmalign', 'database': manifest['name'], 'database_version': manifest['version'],
                      'family': accession, 'span_from': min(hit['seq_from'], hit['seq_to']),
                      'span_to': max(hit['seq_from'], hit['seq_to']), 'strand': hit['strand']}) for accession, _, hit in chosen]
        grading_product = record_grading_product(
            store, grading_ref=grading_ref, grading=grading, provider=PROVIDER, source_ref=record['id'],
            used=[report_ref, *spans.values(), manifest_ref], derived_from=[row['id'] for row in alignments])
    graded = [record['id'], grading_ref, *(row['id'] for row in alignments), grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': graded, 'record_refs': [*graded, *jobs],
            'source_ref': record['id'], 'family_count': sheet['family_count'], 'candidates_measured': sheet['candidates_measured'],
            'families_without_pairs': sheet['families_without_pairs'],
            'consensus_pairs': sum(row['consensus_pairs'] for row in sheet['rows']),
            'pairs_canonical': sum(row['pairs_canonical'] for row in sheet['rows'])}


__all__ = ['ALIGNMENTS_KIND', 'MINIMUM_FAMILIES', 'OWN_FAILURE_CODES', 'PROVIDER', 'REQUEST_FIELDS',
           'check_rna_structure_agreement_request', 'rna_structure_agreement', 'span_of']
