"""A102's one-shot tool ``ligand_transplants`` (row P3 of ``a102_tree.md``; design note ``docs/plan/designs/a102_ligand_transplants.md``):
which ligands and cofactors have a place in the target's AlphaFold DB model, as they sit in solved homologs (AlphaFill). SOP Step 3:
the model fills out one JSON, ONE deterministic check, ONE function that runs the unit and grades it.

THE REQUEST (controlled field): ``model_ref`` (a held data-product row of kind ``protein_structure_model`` whose origin is
``alphafold_db``: AlphaFill is keyed by the model's accession). ``check_ligand_transplants_request`` is the one check. It refuses,
with the fix list (the field, a code and what to choose from): a ``model_ref`` that is not a held model
(``model_is_not_a_held_model``); a model that is not an AlphaFold DB model (``model_is_not_from_alphafold_db``); a model already
tested (``ligand_transplant_test_already_run``). A request that passes it simply works.

THE UNIT. One request, ``GET https://alphafill.eu/v1/aff/<accession>/json`` (``fetch_alphafill``). Outcomes that are not failures:
HTTP 200 with hits (``transplants``); HTTP 200 with ``hits`` null (``no_transplants``: the model exists, nothing was transplanted);
HTTP 404 with AlphaFill's not-found body (``no_alphafill_entry``). Any other status, a body of another shape or a transport failure
raises. The answer is graded (``ligand_transplants_sheet``), kept as the data product ``ligand_transplant_results`` and the grading
retained with a source record (provider ``ligand_transplants``) and labelled a ``tool_grading_sheet``. Writes only through
``ctx.store``.

What exists and is called: ``target_model_sources`` (the User-Agent and the timeout), ``partner_contacts`` (the BioLiP additive list),
``tool_grading_artifacts``, ``data_products``."""
import json
import urllib.error
import urllib.parse
import urllib.request

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    BROWSER_USER_AGENT, TRANSPORT_TIMEOUT_SECONDS)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence import ligand_transplants_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products, record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence import foldseek_search
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_contacts import (
    ADDITIVE_FACTS, ADDITIVES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    _choose)

PROVIDER = sheets.PROVIDER
PRODUCT_KIND = 'ligand_transplant_results'
REQUEST_FIELDS = ('model_ref',)
ORIGIN = 'alphafold_db'
SERVICE = 'alphafill'
URL_FORM = 'https://alphafill.eu/v1/aff/<accession>/json'
# The record types that carry a sequence: what the model's target is found among.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')


def alphafill_url(accession):
    return 'https://alphafill.eu/v1/aff/' + urllib.parse.quote(accession, safe='') + '/json'


def fetch_alphafill(accession):
    """One request for ``accession``: ``{'outcome' (``ligand_transplants_sheet.OUTCOMES``), 'url', 'http_status', 'body' (the bytes
    as received), 'parsed' (the JSON)}``. Raises for any status other than 200 and 404, for a 404 whose body is not AlphaFill's
    not-found body, for a 200 whose body is not an object with ``hits`` null or a list, and for a transport failure."""
    url = alphafill_url(accession)
    request = urllib.request.Request(url, headers={'User-Agent': BROWSER_USER_AGENT, 'Accept': '*/*'})
    try:
        with urllib.request.urlopen(request, timeout=TRANSPORT_TIMEOUT_SECONDS) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    if status == 404:
        parsed = json.loads(body)
        if parsed != sheets.NOT_FOUND_BODY:
            raise ValueError('alphafill_not_found_body_differs')
        outcome = 'no_alphafill_entry'
    elif status == 200:
        parsed = json.loads(body)
        if not isinstance(parsed, dict) or not (parsed['hits'] is None or isinstance(parsed['hits'], list)):
            raise ValueError('alphafill_response_has_another_shape')
        outcome = 'no_transplants' if parsed['hits'] is None else 'transplants'
    else:
        raise RuntimeError('alphafill_http_' + str(status))
    return {'outcome': outcome, 'url': url, 'http_status': status, 'body': body, 'parsed': parsed}


def model_inputs(reader):
    """The AlphaFold DB models the caller holds, as ``{model row reference: {'origin', 'accession', 'query_ref'}}`` (every held
    model, the origin shown: the check names the ones it refuses); ``query_ref`` is the held record whose sequence the model was
    made from."""
    held = {ref: reader.get(ref).get('sequence_ref') for ref in reader.refs()
            if not ref.startswith('row_') and ref.split('_')[0] in SEQUENCE_RECORD_TYPES}
    return {row['id']: {'origin': row['settings']['origin'], 'accession': row['settings']['accession'],
                        'query_ref': next(ref for ref, sequence in held.items() if sequence is not None and sequence in row['used'])}
            for row in products(reader, foldseek_search.MODEL_KIND)}


def check_ligand_transplants_request(request, *, models, tested):
    """The things to fix in a ``ligand_transplants`` request, before anything runs; an empty list means it can run.

    ``request`` holds ``model_ref``. ``models`` is ``model_inputs``; ``tested`` the model references already tested
    (``candidate_measurements.held_transplant_models``)."""
    model = request['model_ref']
    offered = [ref for ref, held in models.items() if held['origin'] == ORIGIN and ref not in tested]
    if model not in models:
        return [_choose('model_ref', 'model_is_not_a_held_model', choose_from=offered)]
    if models[model]['origin'] != ORIGIN:
        return [_choose('model_ref', 'model_is_not_from_alphafold_db', choose_from=offered)]
    if model in tested:
        return [_choose('model_ref', 'ligand_transplant_test_already_run', choose_from=offered)]
    return []


def ligand_transplants(ctx, *, model_ref):
    """Ask AlphaFill for the transplants of the held model ``model_ref`` and grade them (see the module); keep the answer and the
    grading through custody. ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    row = {item['id']: item for item in products(store, foldseek_search.MODEL_KIND)}[model_ref]
    settings = row['settings']
    query_ref = model_inputs(store)[model_ref]['query_ref']
    got = fetch_alphafill(settings['accession'])
    held = {'model_ref': model_ref, 'accession': settings['accession'], 'sha256': settings['sha256'],
            'version': settings['model_version']}
    sheet = sheets.grade_ligand_transplants(got['outcome'], got['parsed'], model=held, additives=ADDITIVES, additive_list=ADDITIVE_FACTS)
    grading = {'sheet': sheet}
    product_settings = {'service': SERVICE, 'url_form': URL_FORM, 'accession': settings['accession'], 'http_status': got['http_status'],
                        'outcome': got['outcome']}
    with store.transaction():
        answer_ref = store.artifact(got['body'], 'application/json')
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=answer_ref, grading=grading)
        record = store.put('source', {
            'provider': PROVIDER, 'accession': settings['accession'], 'uri': got['url'], 'artifact_ref': answer_ref,
            'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref]}, origin='tool')
        product = record_product(store, artifact_ref=answer_ref, kind=PRODUCT_KIND, generated_by=record['id'],
                                 used=[row['artifact_ref']], derived_from=[model_ref], settings=product_settings)
        grading_product = record_grading_product(
            store, grading_ref=grading_ref, grading=grading, provider=PROVIDER, source_ref=record['id'],
            used=[answer_ref, row['artifact_ref']], derived_from=[product['id'], model_ref])
    refs = [record['id'], grading_ref, product['id'], grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': refs, 'record_refs': refs,
            'source_ref': record['id'], 'product_ref': product['id'], 'alphafill_outcome': sheet['outcome'],
            'hit_count': sheet['hit_count'], 'transplant_count': sheet['transplant_count'],
            'additive_count': sheet['additive_count'], 'candidates_measured': sheet['candidates_measured'],
            'model_version_differs': sheet['model_version_differs']}


__all__ = ['ORIGIN', 'PRODUCT_KIND', 'PROVIDER', 'REQUEST_FIELDS', 'SERVICE', 'alphafill_url', 'check_ligand_transplants_request',
           'fetch_alphafill', 'ligand_transplants', 'model_inputs']
