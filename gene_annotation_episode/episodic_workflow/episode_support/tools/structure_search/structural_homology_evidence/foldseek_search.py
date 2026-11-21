"""One structure search of one database with one model of the target on the Foldseek web server (the ``StructureSearch``
application, ``jobs/foldseek_job_route``), as plain library functions that the actions of the ``structure_search`` episode
call. The five job actions, their checks, the estimate gate, the credit and the ledger are ``structure_search_child`` (A102's own
copy of the job-child machinery); this module is the binding of the application to it (``APPLICATION``) and what is specific:

* ``obtain_model`` (the ``get_model`` unit): a model of the target from one source. ``alphafold_db``: the UniProt entries whose
  sequence is exactly the target's (``target_model_sources.uniprot_accessions_by_sequence``; no name is ever asked), then the
  AlphaFold DB model of the FIRST accession in that function's deterministic order (reviewed first, then annotation score, then
  accession); no exact entry, or no model for it, is the outcome ``not_found``: a COMPLETED unit that holds nothing and earns
  nothing (a discovered fact, not a failure; the source is not offered again). ``esmfold``: ``esmfold_model(sequence)``. A model
  found is kept through custody as an artifact (the PDB text), a source record of its provider (``alphafold_db`` or ``esmfold``)
  and the data product ``protein_structure_model`` (``generated_by`` that source record, ``used`` the target's sequence artifact,
  settings: origin, accession or null, model version, residues covered, mean pLDDT 0 to 100, SHA-256 of the file; locations: the
  source URL). pLDDT describes the model and is not similarity; it weighs nothing downstream.
* THE NUMBERING OF THE MODEL (``model_positions``): the server numbers the query residues by their order in the file, and the
  grading takes the model's C-alpha by that number as the target's position. AlphaFold DB (an entry F1 of an exactly matching
  sequence) and ESM Atlas write residue numbers 1..n in sequence order, and the child CHECKS it for every model (a model found by
  ``get_model`` and a model a commission passes): residue ``i`` is the ``i``-th C-alpha of the file, its three-letter name is the
  target's residue at position ``i``, and ``n`` is at most the target's length. A model that fails is refused with the first
  residue that differs.
* the job: ``{'application': 'StructureSearch', 'database', 'query_file': 'query.pdb'}`` with the model file staged as the one
  input; the mode is the route's fixed ``tmalign``. The job's identity (database, mode, the model's SHA-256 and facts, the
  target's length) is kept in the handoff row's ``estimates`` so the head and a continuation read it from the row; the
  extract reads the model file from the row's staged inputs (``detail.input_refs``) and never recomputes it.
* the extract (ONE unit): fetch the result through the route, keep it and label it ``structure_search_results``; parse it
  (``foldseek_result.parse_foldseek_result``); the model's C-alpha by target position; ``structure_search_sheet.measure_hits``
  (the superposition and B of every hit); the hits are named in rank order by UniProt (``uniprot_hit_names.name_hits``: the hit
  that is the model itself, the self control, is given no value in the picture); ``grade_structure_search``; the UniProt replies
  kept as the ``search_hit_metadata`` product; the grading retained (``retain_tool_grading``, with a source record of provider
  ``foldseek_search``) and labelled (``record_grading_product``).

The source providers: the Store admits a source of any provider text (``state.py`` constrains a source's operands, artifacts
and parents; the providers it names are those of records that need a particular source), so ``alphafold_db``, ``esmfold``,
``foldseek_search`` and ``uniprot_data`` are admitted without a central change (shown by the direct check in
``docs/plan/designs/a102_structure_search_episode.md``).

What exists and is called: ``target_model_sources`` (the three requests), ``foldseek_job_route`` (the route and its fixed
constants), ``foldseek_result``, ``structure_search_sheet``, ``uniprot_hit_names``, ``tool_grading_artifacts``,
``data_products``, ``job_records.returned_with_names`` (by the episode's summary)."""
import hashlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    ESMFOLD_URL, alphafold_model, esmfold_model, uniprot_accessions_by_sequence)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.structure_search_sheet import (
    grade_structure_search, is_model_itself, measure_hits)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import (
    DATABASES, MODE, RESULT_FILE)
from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.foldseek_result import (
    parse_foldseek_result)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import (
    find_reusable, products, record_product, require_product)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, canonical)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    FAILURE_CODES, JobApplication, _choose, _failed, check_resource_and_continuation)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.uniprot_hit_names import (
    BATCH, FIELDS as UNIPROT_FIELDS, SEARCH_URL as UNIPROT_URL, SETTLE, name_hits)

CHILD = 'structure_search'
SERVICE = 'foldseek'
PROVIDER = 'foldseek_search'
METADATA_PROVIDER = 'uniprot_data'
APPLICATION_NAME = 'StructureSearch'
QUERY_FILE = 'query.pdb'
MODEL_KIND = 'protein_structure_model'
RESULTS_KIND = 'structure_search_results'
METADATA_KIND = 'search_hit_metadata'
REQUEST_FIELDS = ('database', 'resource_id')
MODEL_ORIGINS = ('alphafold_db', 'esmfold')
RESIDUES = {'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C', 'GLN': 'Q', 'GLU': 'E', 'GLY': 'G', 'HIS': 'H',
            'ILE': 'I', 'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P', 'SER': 'S', 'THR': 'T', 'TRP': 'W',
            'TYR': 'Y', 'VAL': 'V'}


def target_sequence(reader, query_ref):
    """The target's sequence (upper case) read from the held subject record."""
    return reader.get_artifact(reader.get(query_ref)['sequence_ref']).decode('ascii').strip().upper()


# -- the model ---------------------------------------------------------------------------------------------------------
def model_positions(pdb_bytes, sequence):
    """``{target position (1-based): (x, y, z)}`` of the C-alpha atoms of the model file, after the check that the file's
    numbering IS the target's positions: the ``i``-th C-alpha of the file has residue number ``i`` and the three-letter name of
    the target's residue ``i``, and the file has at most as many residues as the target. ``ValueError`` names the first
    difference."""
    positions = {}
    for line in pdb_bytes.decode('ascii').splitlines():
        if line.startswith('ATOM') and line[12:16].strip() == 'CA':
            ordinal = len(positions) + 1
            number, name = int(line[22:26]), line[17:20]
            if number != ordinal:
                raise ValueError('model_residue_numbers_are_not_the_target_positions:ordinal_' + str(ordinal) + '_has_number_'
                                 + str(number))
            if ordinal > len(sequence) or RESIDUES.get(name) != sequence[ordinal - 1]:
                raise ValueError('model_residue_is_not_the_target_residue:position_' + str(ordinal) + '_is_' + name)
            positions[ordinal] = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
    if not positions:
        raise ValueError('pdb_model_has_no_c_alpha_atoms')
    return positions


def model_settings(*, origin, accession, version, residues, mean_plddt, sha256):
    """The settings of a model as a data product (closed JSON): the facts that weigh nothing downstream."""
    return {'origin': origin, 'accession': accession, 'model_version': version, 'residues_covered': residues,
            'mean_plddt': mean_plddt, 'sha256': sha256}


def held_model(reader):
    """The model of the target the episode holds (a data product of kind ``protein_structure_model``: one it obtained, or the
    one its commission passed), as ``{'row_ref', 'artifact_ref', 'origin', 'accession', 'model_version', 'residues',
    'mean_plddt', 'sha256'}``, or ``None``."""
    rows = products(reader, MODEL_KIND)
    if len(rows) > 1:
        raise ValueError('structure_search_holds_more_than_one_model')
    if not rows:
        return None
    settings = rows[0]['settings']
    return {'row_ref': rows[0]['id'], 'artifact_ref': rows[0]['artifact_ref'], 'origin': settings['origin'],
            'accession': settings['accession'], 'model_version': settings['model_version'],
            'residues': settings['residues_covered'], 'mean_plddt': settings['mean_plddt'], 'sha256': settings['sha256']}


def job_model(handoff):
    """The model the held job was given, from its handoff row (identity and staged input), for a continuation."""
    identity = handoff['detail']['estimates']['identity']
    return {'row_ref': None, 'artifact_ref': handoff['detail']['input_refs'][QUERY_FILE],
            'origin': identity['model_origin'], 'accession': identity['model_accession'],
            'model_version': identity['model_version'], 'residues': identity['model_residues'],
            'mean_plddt': identity['model_mean_plddt'], 'sha256': identity['model_sha256']}


def passed_model(reader, ref, sequence_ref):
    """The model the commission passed (``ref``: a held data-product row of kind ``protein_structure_model`` made from this
    target's sequence artifact), as ``held_model`` gives it. A row that is not one, or not of this target, raises."""
    row, problem = require_product(reader, ref, MODEL_KIND)
    if problem is not None:
        raise ValueError('structure_search_model_' + problem)
    if sequence_ref not in row['used']:
        raise ValueError('structure_search_model_is_not_of_the_target')
    return held_model(reader)


def model_problems(model, reader, sequence):
    """The things to fix in the model a launch would stage: its numbering is not the target's positions."""
    try:
        model_positions(reader.get_artifact(model['artifact_ref']), sequence)
    except ValueError as error:
        return [_choose('action', 'model_numbering_is_not_the_target_positions', reason=str(error))]
    return []


def obtain_model(ctx, *, source, query_ref):
    """The ``get_model`` unit: a model of the target from ``source``. ``not_found`` is a completed unit that holds nothing;
    a model found is kept as an artifact, a source record and the ``protein_structure_model`` product (see the module). A
    fault of the source after a passed check is returned once as ``failed`` (``model_source_request_failed``: the transport
    or an HTTP status the service should not give; ``model_source_response_invalid``: a reply not of the documented form, or a
    model whose numbering is not the target's positions)."""
    store = ctx.store
    sequence_ref = store.get(query_ref)['sequence_ref']
    sequence = target_sequence(store, query_ref)
    try:
        if source == 'alphafold_db':
            found = uniprot_accessions_by_sequence(sequence)
            if found['status'] == 'not_found':
                return _not_found(source, 'no_exact_uniprot_entry')
            model = alphafold_model(found['accessions'][0]['accession'])
        else:
            model = esmfold_model(sequence)
        if model['status'] == 'not_found':
            return _not_found(source, 'no_model_for_the_entry')
        model_positions(model['model_bytes'], sequence)
    except (RuntimeError, OSError) as error:
        return {**_failed('model_source_request_failed', False, source=source, reason=str(error)), 'model_status': None}
    except (ValueError, KeyError, TypeError) as error:
        return {**_failed('model_source_response_invalid', False, source=source, reason=str(error)), 'model_status': None}
    sha256 = hashlib.sha256(model['model_bytes']).hexdigest()
    url = model.get('model_url', ESMFOLD_URL)
    version = model.get('model_version')
    with store.transaction():
        artifact = store.artifact(model['model_bytes'], 'chemical/x-pdb')
        record = store.put('source', {
            'provider': source, 'accession': model.get('accession'), 'uri': url, 'artifact_ref': artifact,
            'text_ref': None, 'request_ref': None, 'version': None if version is None else str(version),
            'retrieved_at': None, 'auxiliary_artifact_refs': [], 'operand_refs': [query_ref]}, origin='tool')
        row = record_product(
            store, artifact_ref=artifact, kind=MODEL_KIND, generated_by=record['id'], used=[sequence_ref],
            settings=model_settings(origin=source, accession=model.get('accession'), version=version,
                                    residues=model['residue_count'], mean_plddt=model['plddt_mean'], sha256=sha256),
            locations=[{'service': source, 'path': url}])
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'model_status': 'found',
            'residues': model['residue_count'], 'mean_plddt': model['plddt_mean'], 'model_ref': row['id'],
            'record_refs': [record['id'], artifact, row['id']]}


def _not_found(source, reason):
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'model_status': 'not_found',
            'residues': None, 'mean_plddt': None, 'model_ref': None, 'reason': reason, 'record_refs': []}


# -- the search ----------------------------------------------------------------------------------------------------------
def search_settings(database):
    """The settings of a search's result as a data product (closed JSON): the reuse key and the product's settings."""
    return {'service': SERVICE, 'application': APPLICATION_NAME, 'database': database, 'mode': MODE}


def reusable_search(reader, model_artifact_ref, database):
    """The held result product of exactly this model file and database, or ``None``."""
    return find_reusable(reader, RESULTS_KIND, [model_artifact_ref], search_settings(database))


def metadata_settings():
    """The settings of the hit metadata as a data product (closed JSON): the data service, the fields asked of each hit's
    entry, the batch and the settling step of the naming (``uniprot_hit_names.name_hits``)."""
    return {'service': METADATA_PROVIDER, 'url': UNIPROT_URL, 'fields': UNIPROT_FIELDS, 'batch': BATCH, 'settle': SETTLE}


def field_problems(request, commission):
    problems = []
    if request['database'] not in DATABASES:
        problems.append(_choose('database', 'database_is_not_offered', choose_from=list(DATABASES)))
    return problems


def prepare(ctx, request, commission):
    """The job of one launch: the model the launch was checked with (``commission['model']``, its artifact staged as the one
    input ``query.pdb``) and the identity kept in the handoff row. ``job_facts`` are what the ledger row says of the job
    (the size field is the model's residue count)."""
    model, query_ref = commission['model'], commission['query_ref']
    length = len(target_sequence(ctx.store, query_ref))
    return {'job': {'application': APPLICATION_NAME, 'database': request['database'], 'query_file': QUERY_FILE},
            'inputs': {QUERY_FILE: model['artifact_ref']},
            'job_facts': {'database': request['database'], 'mode': MODE, 'residues': model['residues']},
            'identity': {'query_ref': query_ref, 'database': request['database'], 'mode': MODE,
                         'model_sha256': model['sha256'], 'query_length': length, 'model_origin': model['origin'],
                         'model_accession': model['accession'], 'model_version': model['model_version'],
                         'model_residues': model['residues'], 'model_mean_plddt': model['mean_plddt']}}


def describe_identity(reader, handoff):
    """The controlled identity of a held job (kept by ``prepare`` in the handoff row's estimates: the head holds the row, not
    the model file the job was given)."""
    return handoff['detail']['estimates']['identity']


def extract(ctx, handoff_ref, request, commission):
    """Fetch the result of the finished job and grade it, in the same unit; keep through custody: the result (labelled
    ``structure_search_results``), the grading artifact and a source of provider ``foldseek_search`` over the result, the UniProt
    replies (``search_hit_metadata``, with a source of provider ``uniprot_data``) and the grading as a ``tool_grading_sheet``
    data product. What the job was given is read from the handoff row (its identity and its staged model file). A fault of the
    parsing or grading is returned once as ``grading_refused`` (or ``result_of_another_query``)."""
    store, query_ref = ctx.store, commission['query_ref']
    fetched = ctx.services['job_access'].fetch(ctx, handoff_ref, names=[RESULT_FILE])
    if fetched['status'] != 'completed':
        return {**_failed(fetched['failure']['code'], False), 'closure_ref': None}
    (result_ref,) = [item['ref'] for item in fetched['results'] if item['name'] == RESULT_FILE]
    handoff = store.get(handoff_ref)
    identity = handoff['detail']['estimates']['identity']
    model_ref = handoff['detail']['input_refs'][QUERY_FILE]
    sequence = target_sequence(store, query_ref)
    facts = {'origin': identity['model_origin'], 'accession': identity['model_accession'],
             'mean_plddt': identity['model_mean_plddt'], 'residues_covered': identity['model_residues'],
             'model_sha256': identity['model_sha256']}
    try:
        model_bytes = store.get_artifact(model_ref)
        if hashlib.sha256(model_bytes).hexdigest() != identity['model_sha256']:
            raise ValueError('grading_refused')
        parsed = parse_foldseek_result(json.loads(store.get_artifact(result_ref)), identity['database'])
        if parsed['query_sequence'] != sequence[:len(parsed['query_sequence'])]:
            raise ValueError('result_of_another_query')
        model_ca = model_positions(model_bytes, sequence)
        measured = measure_hits(parsed['hits'], model_ca, len(sequence))
        ordered = [(hit['accession'], None if is_model_itself(hit, facts) else value['B'])
                   for hit, value in zip(parsed['hits'], measured)]
        found = name_hits(ordered)
        sheet = grade_structure_search(parsed['hits'], model_ca, len(sequence),
                                       {'products': found['products'], 'asked': found['asked']},
                                       database=identity['database'], mode=identity['mode'], model_facts=facts,
                                       measured=measured)
    except (ValueError, ContractError) as error:
        code = str(error) if str(error) in FAILURE_CODES else 'grading_refused'
        return {**_failed(code, False, reason=str(error)), 'closure_ref': fetched['closure_ref']}
    grading = {'sheet': sheet}
    remote = handoff['detail']['native']['remote_id']
    metadata = {'service': METADATA_PROVIDER, 'url': UNIPROT_URL, 'fields': UNIPROT_FIELDS, 'batch': BATCH, 'settle': SETTLE,
                'replies': [{'url': reply['url'], 'status': reply['status'], 'sha256': reply['sha256'],
                             'media_type': reply['media_type'], 'body': json.loads(reply['content'])}
                            for reply in found['replies']],
                'failures': found['failures'], 'products': found['products'], 'metadata': found['metadata'],
                'naming': found['naming']}
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=result_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': result_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [query_ref]}, origin='tool')
        metadata_ref = store.artifact(canonical(metadata), 'application/json')
        metadata_source = store.put('source', {
            'provider': METADATA_PROVIDER, 'accession': None, 'uri': UNIPROT_URL, 'artifact_ref': metadata_ref,
            'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None,
            'auxiliary_artifact_refs': [], 'operand_refs': [query_ref]}, origin='tool')
        model_rows = [row['id'] for row in products(store, MODEL_KIND) if row['artifact_ref'] == model_ref]
        product = record_product(
            store, artifact_ref=result_ref, kind=RESULTS_KIND, generated_by=handoff_ref, used=[model_ref],
            derived_from=model_rows, settings=search_settings(identity['database']),
            locations=[{'service': 'foldseek_server', 'path': '/api/result/' + remote + '/0'}])
        metadata_product = record_product(
            store, artifact_ref=metadata_ref, kind=METADATA_KIND, generated_by=metadata_source['id'], used=[result_ref],
            derived_from=[product['id']], settings=metadata_settings())
        grading_product = record_grading_product(
            store, grading_ref=grading_ref, grading=grading, provider=PROVIDER, source_ref=source['id'],
            used=[result_ref, metadata_ref], derived_from=[product['id'], metadata_product['id']])
    refs = [source['id'], grading_ref, metadata_source['id'], product['id'], metadata_product['id'], grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'closure_ref': fetched['closure_ref'],
            'graded_refs': refs, 'record_refs': [*refs, fetched['closure_ref']], 'product_ref': product['id'],
            'hit_count': sheet['hit_count'], 'named_count': sheet['named_count'], 'not_asked_count': sheet['not_asked_count'],
            'control_count': sheet['control_count'],
            'candidate_count': sum(1 for row in sheet['candidates'] if row['mean_B'] is not None),
            'metadata_request_count': len(found['replies']) + len(found['failures']),
            'metadata_failure_count': len(found['failures']), 'naming_batch_count': found['naming']['batches'],
            'naming_stopped': found['naming']['stopped']}


def graded_rows(reader):
    """The graded searches the episode holds: one row per held source of provider ``foldseek_search`` with its sheet's counts,
    the database, the target and the model's facts."""
    rows = []
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        (entry,) = source_tool_grading_entries(reader, source['id'])
        sheet = entry['grading']['sheet']
        rows.append({'source_ref': source['id'], 'grading_ref': entry['artifact_ref'], 'query_ref': source['operand_refs'][0],
                     'database': sheet['database'], 'model_sha256': sheet['model']['model_sha256'],
                     'hit_count': sheet['hit_count'], 'named_count': sheet['named_count'],
                     'not_asked_count': sheet['not_asked_count'], 'no_name_count': sheet['no_name_count'],
                     'control_count': sheet['control_count'], 'valued_count': sheet['valued_count'],
                     'candidate_count': sum(1 for row in sheet['candidates'] if row['mean_B'] is not None)})
    return rows


def check_commission(request, *, scope_subjects, sequences, resources, jobs, commissioned, models, searches):
    """The things to fix in the head's commission of this child (``request``: ``query_ref``, ``database``, ``resource_id``,
    ``until``, ``model_ref`` (a held data-product row of kind ``protein_structure_model``, or ``None``)), before any child is
    commissioned. ``sequences`` is ``{record: molecule}``; ``models`` is ``{row reference: that row}`` of the head's held
    model products; ``jobs`` the head's held jobs (``structure_search_child.held_jobs``); ``searches`` ``graded_rows``;
    ``commissioned`` the ``(query, database, model row or None)`` of the earlier commissions. The conditions: the query is a
    protein sequence of the scope; the database is offered; the model, when given, is a held model product made from the
    query's sequence; the resource is a bound Foldseek service; an outstanding job of this commission is continued (``until``
    ``extracted``, and no model given: the job reads its own) and another one blocks it; a search of the same query, database
    and model already held, or already commissioned and not outstanding, is not commissioned again."""
    problems = []
    query, database, model_ref = request['query_ref'], request['database'], request['model_ref']
    if query not in scope_subjects or sequences.get(query) != 'protein':
        problems.append(_choose('query_ref', 'query_is_not_a_protein_sequence_of_the_scope',
                                choose_from=[ref for ref in scope_subjects if sequences.get(ref) == 'protein']))
    problems.extend(field_problems(request, None))
    model = None
    if model_ref is not None:
        model = models.get(model_ref)
        if model is None or model['kind'] != MODEL_KIND:
            problems.append(_choose('model_ref', 'model_is_not_a_held_protein_structure_model', choose_from=list(models)))
    same = lambda job: (job['identity']['query_ref'] == query and job['identity']['database'] == database
                        and job['resource_id'] == request['resource_id']
                        and (model is None or job['identity']['model_sha256'] == model['settings']['sha256']))
    problems.extend(check_resource_and_continuation(request, resources=resources, jobs=jobs, same=same))
    if model is not None and any(row['query_ref'] == query and row['database'] == database
                                 and row['model_sha256'] == model['settings']['sha256'] for row in searches):
        problems.append(_choose('database', 'search_already_held'))
    if (query, database, model_ref) in commissioned and not any(job['outstanding'] and same(job) for job in jobs):
        problems.append(_choose('database', 'search_already_commissioned'))
    return problems


APPLICATION = JobApplication(
    application=APPLICATION_NAME, child=CHILD, service=SERVICE, provider=PROVIDER, product_kind=RESULTS_KIND,
    request_fields=REQUEST_FIELDS, estimate_fields=('database',),
    field_schemas={'database': {'type': 'string', 'enum': list(DATABASES)},
                   'resource_id': {'type': 'string', 'minLength': 1}},
    size_field='residues', kind=lambda fields: MODE + ':' + fields['database'],
    field_problems=field_problems, prepare=prepare, extract=extract, describe_identity=describe_identity)

__all__ = ['APPLICATION', 'CHILD', 'METADATA_PROVIDER', 'MODEL_KIND', 'MODEL_ORIGINS', 'PROVIDER', 'QUERY_FILE',
           'REQUEST_FIELDS', 'RESULTS_KIND', 'check_commission', 'graded_rows', 'held_model', 'job_model', 'model_positions',
           'model_problems', 'obtain_model', 'passed_model', 'reusable_search', 'target_sequence']
