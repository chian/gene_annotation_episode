"""One co-folding job of the target with several held ligand candidates on a PBS resource (Polaris), as plain library functions that the
actions of the ``partner_cofolding`` episode call (design note ``docs/plan/designs/a102_partner_cofolding.md``). The five job actions,
their checks, the estimate gate, the credit and the ledger are ``structure_search_child`` (A102's job-child machinery); this module is
the binding of the application to it (``APPLICATION``, with ``route_kind`` ``pbs`` and no model sources: the child has no
``get_model``, the target sequence is read from the subject record) and what is specific:

* ``prepare`` (in the launch unit): the target sequence from the subject record; each ligand's SMILES from the RCSB chemical-component
  service (``partner_cofolding_inputs.chemcomp_smiles``; a failure raises and fails the run, nothing repairs it); the staged files
  ``target.fasta``, ``ligands.json`` and ``run_chai.py`` (``partner_cofolding_job.RUN_CHAI_PY``) kept through custody as the job's
  inputs; the PBS batch job (``partner_cofolding_job.cofolding_batch_job``) under the run's allocation, the python of the chai
  environment and its exports, all of the episode's settings (``allocation``, ``chai_python_executable``, ``chai_environment``).
* the ledger kind ``partner_cofolding:chai1:<number of ligands>`` with the size field ``residues`` (the target's length). The job's
  duration is observed (``structure_search_child.monitor_job``): the launch to the first status that showed the end, the wait in the
  queue included. The first figure is ``FIRST_JOB_SECONDS``.
* ``extract`` (ONE unit): fetch ``scores.json`` through the route, keep it as the data product ``cofolding_results``, grade it
  (``partner_cofolding_sheet.grade_partner_cofolding``: sheet ``a102_partner_cofolding_sheet``, with the SMILES used and their
  source) and retain the grading (``retain_tool_grading``, a source record of provider ``partner_cofolding``) as a ``tool_grading_sheet``
  data product (``record_grading_product``).
"""
import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.partner_cofolding_sheet import (
    PROVIDER, grade_partner_cofolding)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import find_reusable, record_product
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding_inputs import (
    DESCRIPTOR_PROGRAM, DESCRIPTOR_TYPE, chemcomp_smiles)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding_job import (
    INPUT_FILES, OUTPUT_FILE, PROGRAM_NAME, RUN_CHAI_PY, SEED, cofolding_batch_job)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    JobApplication, _choose, _failed, check_resource_and_continuation)

CHILD = 'partner_cofolding'
SERVICE = 'chai1'
ROUTE_KIND = 'pbs'
APPLICATION_NAME = 'run_chai'
RESULTS_KIND = 'cofolding_results'
REQUEST_FIELDS = ('ligands', 'resource_id')
LIGAND_PREFIX = 'ligand:'
LIGAND_COUNT = (2, 4)
# The seconds of the first job of a kind, when the ledger has measured none: the run only (the GPU check of 2026-11-22: 133 s for
# five samples of one ligand); the queue wait is learned from the first measured jobs (their duration includes it).
FIRST_JOB_SECONDS = 600
SMILES_SOURCE = 'rcsb_chemcomp:' + DESCRIPTOR_TYPE + ':' + DESCRIPTOR_PROGRAM
STATES = ('ready', 'estimated', 'launched', 'finished', 'extracted', 'failed')
LIGAND_PATTERN = '^' + LIGAND_PREFIX + '[A-Za-z0-9]{1,5}$'


def target_sequence(reader, query_ref):
    """The target's sequence (upper case) read from the held subject record."""
    return reader.get_artifact(reader.get(query_ref)['sequence_ref']).decode('ascii').strip().upper()


def component_id(ligand):
    """The chemical component id of the candidate name ``ligand:<id>``."""
    return ligand[len(LIGAND_PREFIX):]


def cofolding_settings(ligands):
    """The settings of a result as a data product (closed JSON): the reuse key with the target's sequence artifact."""
    return {'service': SERVICE, 'application': APPLICATION_NAME, 'ligands': sorted(ligands), 'seed': SEED}


def reusable_cofolding(reader, query_ref, ligands):
    """The held result product of exactly this target and these ligands, or ``None``."""
    return find_reusable(reader, RESULTS_KIND, [reader.get(query_ref)['sequence_ref']], cofolding_settings(ligands))


def field_problems(request, commission):
    """The ligands: two to four, distinct, each named ``ligand:<component id>``."""
    ligands = request['ligands']
    problems = []
    if not LIGAND_COUNT[0] <= len(ligands) <= LIGAND_COUNT[1]:
        problems.append(_choose('ligands', 'ligand_count_out_of_range', minimum=LIGAND_COUNT[0], maximum=LIGAND_COUNT[1]))
    if len(set(ligands)) != len(ligands):
        problems.append(_choose('ligands', 'ligands_are_not_distinct'))
    return problems


def prepare(ctx, request, commission):
    """The job of one launch: the staged files, the batch job and the identity kept in the handoff row. ``job_facts`` are what the
    ledger row says of the job (the size field is the target's length)."""
    query_ref, ligands = commission['query_ref'], request['ligands']
    sequence = target_sequence(ctx.store, query_ref)
    smiles = {component_id(ligand): chemcomp_smiles(component_id(ligand)) for ligand in ligands}
    settings = ctx.settings
    with ctx.store.transaction():
        inputs = {
            INPUT_FILES[0]: ctx.store.artifact(('>target\n' + sequence + '\n').encode('ascii'), 'text/plain'),
            INPUT_FILES[1]: ctx.store.artifact(json.dumps(smiles).encode('ascii'), 'application/json'),
            PROGRAM_NAME: ctx.store.artifact(RUN_CHAI_PY.encode('ascii'), 'text/plain')}
    return {'job': cofolding_batch_job(settings['chai_python_executable'], settings['allocation'],
                                       env=settings['chai_environment']),
            'inputs': inputs,
            'job_facts': {'ligands': len(ligands), 'residues': len(sequence)},
            'identity': {'query_ref': query_ref, 'ligands': list(ligands), 'smiles': smiles, 'smiles_source': SMILES_SOURCE,
                         'query_length': len(sequence)}}


def describe_identity(reader, handoff):
    """The controlled identity of a held job (kept by ``prepare`` in the handoff row's estimates)."""
    return handoff['detail']['estimates']['identity']


def extract(ctx, handoff_ref, request, commission):
    """Fetch ``scores.json`` of the finished job and grade it, in the same unit; keep through custody: the scores (labelled
    ``cofolding_results``), the grading artifact and a source of provider ``partner_cofolding`` over them, and the grading as a
    ``tool_grading_sheet`` data product. A fault of the result (not the ligands of the job, or not of the sheet's form) is returned
    once as ``grading_refused``."""
    store, query_ref = ctx.store, commission['query_ref']
    fetched = ctx.services['job_access'].fetch(ctx, handoff_ref, names=[OUTPUT_FILE])
    if fetched['status'] != 'completed':
        return {**_failed(fetched['failure']['code'], False), 'closure_ref': None}
    (result_ref,) = [item['ref'] for item in fetched['results'] if item['name'] == OUTPUT_FILE]
    identity = store.get(handoff_ref)['detail']['estimates']['identity']
    try:
        scores = json.loads(store.get_artifact(result_ref))
        if list(scores) != [component_id(ligand) for ligand in identity['ligands']]:
            raise ValueError('a102_partner_cofolding_scores_are_not_of_the_ligands_of_the_job')
        sheet = {**grade_partner_cofolding(scores),
                 'inputs': {'target_length': identity['query_length'], 'smiles': identity['smiles'],
                            'smiles_source': identity['smiles_source']}}
    except (ValueError, ContractError, KeyError, TypeError) as error:
        return {**_failed('grading_refused', False, reason=str(error)), 'closure_ref': fetched['closure_ref']}
    grading = {'sheet': sheet}
    sequence_ref = store.get(query_ref)['sequence_ref']
    remote = store.get(handoff_ref)['detail']['native']['job_id']
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=result_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': result_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [query_ref]}, origin='tool')
        product = record_product(
            store, artifact_ref=result_ref, kind=RESULTS_KIND, generated_by=handoff_ref, used=[sequence_ref],
            settings=cofolding_settings(identity['ligands']), locations=[{'service': 'pbs', 'path': remote + '/' + OUTPUT_FILE}])
        grading_product = record_grading_product(
            store, grading_ref=grading_ref, grading=grading, provider=PROVIDER, source_ref=source['id'],
            used=[result_ref], derived_from=[product['id']])
    refs = [source['id'], grading_ref, product['id'], grading_product['id']]
    values = [row['value'] for row in sheet['candidates']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'closure_ref': fetched['closure_ref'],
            'graded_refs': refs, 'record_refs': [*refs, fetched['closure_ref']], 'product_ref': product['id'],
            'ligand_count': sheet['ligand_count'], 'candidate_count': sheet['candidates_measured'],
            'sample_count': sum(row['sample_count'] for row in sheet['candidates']),
            'clashing_sample_count': sum(row['clashing_sample_count'] for row in sheet['candidates']),
            'highest_value': max(values), 'lowest_value': min(values)}


def graded_rows(reader):
    """The graded co-foldings the episode holds: one row per held source of provider ``partner_cofolding`` with its target, its
    ligands (``ligand:<id>``) and its counts."""
    rows = []
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        (entry,) = source_tool_grading_entries(reader, source['id'])
        sheet = entry['grading']['sheet']
        rows.append({'source_ref': source['id'], 'grading_ref': entry['artifact_ref'], 'query_ref': source['operand_refs'][0],
                     'ligands': [row['candidate'] for row in sheet['candidates']], 'ligand_count': sheet['ligand_count'],
                     'candidate_count': sheet['candidates_measured']})
    return rows


def check_commission(request, *, scope_subjects, sequences, held_ligands, resources, jobs, commissioned, cofolded):
    """The things to fix in the head's commission of this child (``request``: ``query_ref``, ``ligands``, ``resource_id``,
    ``until``), before any child is commissioned. ``sequences`` is ``{record: molecule}``; ``held_ligands`` the ligand candidate
    names the head holds (``ligand:<id>``); ``jobs`` the head's held jobs (``structure_search_child.held_jobs`` with ``APPLICATION``);
    ``commissioned`` the ``(query, frozenset of ligands)`` of the earlier commissions; ``cofolded`` ``{query: the ligand names
    already co-folded for it}`` (``graded_rows``). The conditions: the query is a protein sequence of the scope; the ligands are two to
    four, distinct, held, and none co-folded before for that query; the resource is a bound PBS resource; an outstanding job of
    this commission is continued (``until`` ``extracted``) and another one blocks it; the same set already commissioned and not
    outstanding is not commissioned again."""
    problems = []
    query, ligands = request['query_ref'], request['ligands']
    if query not in scope_subjects or sequences.get(query) != 'protein':
        problems.append(_choose('query_ref', 'query_is_not_a_protein_sequence_of_the_scope',
                                choose_from=[ref for ref in scope_subjects if sequences.get(ref) == 'protein']))
    problems.extend(field_problems(request, None))
    for ligand in ligands:
        if ligand not in held_ligands:
            problems.append(_choose('ligands', 'ligand_is_not_held', ligand=ligand))
        elif ligand in cofolded.get(query, ()):
            problems.append(_choose('ligands', 'ligand_already_cofolded_for_the_query', ligand=ligand))
    same = lambda job: (job['identity']['query_ref'] == query and set(job['identity']['ligands']) == set(ligands)
                        and job['resource_id'] == request['resource_id'])
    problems.extend(check_resource_and_continuation(request, route_kind=ROUTE_KIND, resources=resources, jobs=jobs, same=same))
    if (query, frozenset(ligands)) in commissioned and not any(job['outstanding'] and same(job) for job in jobs):
        problems.append(_choose('ligands', 'cofolding_already_commissioned'))
    return problems


APPLICATION = JobApplication(
    application=APPLICATION_NAME, child=CHILD, service=SERVICE, provider=PROVIDER, product_kind=RESULTS_KIND,
    request_fields=REQUEST_FIELDS, estimate_fields=('ligands',),
    field_schemas={'ligands': {'type': 'array', 'minItems': LIGAND_COUNT[0], 'maxItems': LIGAND_COUNT[1],
                               'items': {'type': 'string', 'minLength': 1}},
                   'resource_id': {'type': 'string', 'minLength': 1}},
    size_field='residues', kind=lambda fields: str(len(fields['ligands'])),
    field_problems=field_problems, prepare=prepare, extract=extract, describe_identity=describe_identity,
    route_kind=ROUTE_KIND, model_sources=(), first_job_seconds=FIRST_JOB_SECONDS)

__all__ = ['APPLICATION', 'CHILD', 'FIRST_JOB_SECONDS', 'LIGAND_COUNT', 'PROVIDER', 'RESULTS_KIND', 'REQUEST_FIELDS', 'ROUTE_KIND',
           'STATES', 'check_commission', 'cofolding_settings', 'component_id', 'graded_rows', 'reusable_cofolding',
           'target_sequence']
