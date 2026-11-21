"""A102's one-shot tool ``site_correspondence``: the check of its request and the library function that runs and grades it (SOP
Step 3: the model fills out one JSON, ONE deterministic check, ONE function that runs the unit and grades it).

THE REQUEST (controlled fields): ``search_ref`` (the reference of a held graded structure search: the source of provider
``foldseek_search`` that ``foldseek_search.extract`` made) and ``site_source`` (``annotated``: UniProt's active-site, binding-site
and site features of the hits' accessions; ``catalytic``: the M-CSA catalytic residues). Nothing else is chosen: the hits whose
sites are asked are those of the search that can enter a candidate's mean (``site_correspondence_sheet.asked_hits``: not a
control, with a product and a B), in rank order.

``check_site_correspondence_request`` is the one check. It refuses, with the fix list (one entry per problem: the field, a code
and what to choose from): a ``site_source`` that is not offered (``site_source_is_not_offered``); a ``search_ref`` that is not a
held graded search (``search_is_not_a_held_graded_search``); a search whose raw result or model the caller does not hold
(``search_result_or_model_not_held``); a (search, site source) already graded (``site_test_already_graded``). A request that
passes it simply works.

``site_correspondence`` runs a request that passed, as one unit: read the search's sheet, its raw result and its model through
custody; ask the site source for the asked hits' accessions (``site_annotations``: UniProt in batches of 100 in rank order, or
the M-CSA catalogue in ONE request; both are asked in full, because every hit asked is a hit of a candidate and the unit has no
stopping rule of its own: stopping is the yield estimator's); grade (``site_correspondence_sheet``); keep the replies as the
data product ``functional_site_annotations``, retain the grading with a source record (provider ``site_correspondence``) and
label it as a ``tool_grading_sheet`` data product. Writes only through ``ctx.store``. A fault of the environment after a passed
check is returned once as ``failed`` with a code of ``structure_search_child.FAILURE_CODES`` and ``retryable`` false.

What exists and is called: ``foldseek_search`` (``graded_rows``, ``model_positions``, ``target_sequence``, the product kinds),
``foldseek_result.parse_foldseek_result``, ``structure_search_sheet._fit`` (through the grader), ``tool_grading_artifacts``
(``retain_tool_grading``, ``record_grading_product``, ``source_tool_grading_entries``), ``data_products``."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    asked_hits, grade_site_correspondence)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.foldseek_result import (
    parse_foldseek_result)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products, record_product
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, canonical)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence import (
    foldseek_search)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.site_annotations import (
    BATCH, MCSA_URL, SITE_SOURCES, UNIPROT_FIELDS, site_annotations)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    _choose, _failed)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.uniprot_hit_names import (
    SEARCH_URL as UNIPROT_URL)

PROVIDER = 'site_correspondence'
PRODUCT_KIND = 'functional_site_annotations'
REQUEST_FIELDS = ('search_ref', 'site_source')


def search_inputs(reader):
    """The graded searches the caller holds, as ``{search source reference: {'row': foldseek_search.graded_rows row,
    'result_ref', 'model_ref', 'result_held', 'model_held'}}``: the raw result is the source's artifact; the model is the
    artifact the result's data product (``structure_search_results``) was made from."""
    rows = {row['source_ref']: row for row in foldseek_search.graded_rows(reader)}
    made = {row['artifact_ref']: row for row in products(reader, foldseek_search.RESULTS_KIND)}
    held = {}
    for reference, row in rows.items():
        result_ref = reader.get(reference)['artifact_ref']
        model_ref = made[result_ref]['used'][0] if result_ref in made else None
        held[reference] = {'row': row, 'result_ref': result_ref, 'model_ref': model_ref,
                           'result_held': reader.holds(result_ref),
                           'model_held': model_ref is not None and reader.holds(model_ref)}
    return held


def check_site_correspondence_request(request, *, searches, graded):
    """The things to fix in a site-correspondence request, before anything runs; an empty list means it can run.

    ``request`` holds ``search_ref`` and ``site_source``. ``searches`` is ``search_inputs``; ``graded`` the
    ``(search source reference, site source)`` pairs already graded (``candidate_measurements.held_site_tests``)."""
    search, source = request['search_ref'], request['site_source']
    problems = []
    if source not in SITE_SOURCES:
        problems.append(_choose('site_source', 'site_source_is_not_offered', choose_from=list(SITE_SOURCES)))
    if search not in searches:
        problems.append(_choose('search_ref', 'search_is_not_a_held_graded_search', choose_from=list(searches)))
    elif not (searches[search]['result_held'] and searches[search]['model_held']):
        problems.append(_choose('search_ref', 'search_result_or_model_not_held', choose_from=[
            reference for reference, held in searches.items() if held['result_held'] and held['model_held']]))
    if search in searches and source in SITE_SOURCES and (search, source) in graded:
        problems.append(_choose('site_source', 'site_test_already_graded',
                                choose_from=[name for name in SITE_SOURCES if (search, name) not in graded]))
    return problems


def annotation_settings(site_source):
    """The settings of the replies as a data product (closed JSON): the service, the site source and what is asked of it."""
    if site_source == 'annotated':
        return {'service': 'uniprot', 'site_source': site_source, 'url': UNIPROT_URL, 'fields': UNIPROT_FIELDS,
                'batch': BATCH}
    return {'service': 'mcsa', 'site_source': site_source, 'url': MCSA_URL, 'fields': 'residue_sequences', 'batch': None}


def _code(failure):
    """The code of the fixed failure vocabulary for the code a site source gave."""
    if failure.endswith('_reply_invalid'):
        return 'provider_result_response_invalid'
    if '_http_' in failure:
        return 'provider_http_error'
    return 'provider_request_timeout' if failure.endswith(':TimeoutError') else 'provider_connection_failed'


def site_correspondence(ctx, *, search_ref, site_source):
    """Grade the held structure search ``search_ref`` with the sites of ``site_source`` (see the module) and keep the grading
    through custody. ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    source = store.get(search_ref)
    query_ref = source['operand_refs'][0]
    (entry,) = source_tool_grading_entries(store, search_ref)
    search_sheet = entry['grading']['sheet']
    result_ref = source['artifact_ref']
    result_row = {row['artifact_ref']: row for row in products(store, foldseek_search.RESULTS_KIND)}[result_ref]
    model_ref = result_row['used'][0]
    try:
        sequence = foldseek_search.target_sequence(store, query_ref)
        model_ca = foldseek_search.model_positions(store.get_artifact(model_ref), sequence)
        result = json.loads(store.get_artifact(result_ref))
        parsed = parse_foldseek_result(result, search_sheet['database'])
        (rows,) = [item['alignments'][0] for item in result['results'] if item['db'] == search_sheet['database']]
        asked = asked_hits(search_sheet)
    except (ValueError, ContractError) as error:
        return _failed('grading_refused', False, reason=str(error))
    found = site_annotations(site_source, list(dict.fromkeys(row['accession'] for row in asked)))
    if found['failure'] is not None:
        return _failed(_code(found['failure']), False, reason=found['failure'], site_source=site_source)
    try:
        sheet = grade_site_correspondence(search_sheet, parsed['hits'], [row['tSeq'] for row in rows], model_ca,
                                          parsed['query_sequence'], found['sites'], site_source=site_source,
                                          search_source_ref=search_ref)
    except (ValueError, ContractError) as error:
        return _failed('grading_refused', False, reason=str(error))
    grading = {'sheet': sheet}
    settings = annotation_settings(site_source)
    annotations = {**settings, 'replies': [{**reply} for reply in found['replies']], 'not_returned': found['not_returned']}
    with store.transaction():
        annotations_ref = store.artifact(canonical(annotations), 'application/json')
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=annotations_ref, grading=grading)
        record = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': settings['url'], 'artifact_ref': annotations_ref,
            'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref]}, origin='tool')
        product = record_product(store, artifact_ref=annotations_ref, kind=PRODUCT_KIND, generated_by=record['id'],
                                 used=[result_ref], derived_from=[result_row['id']], settings=settings)
        grading_product = record_grading_product(
            store, grading_ref=grading_ref, grading=grading, provider=PROVIDER, source_ref=record['id'],
            used=[annotations_ref, result_ref, model_ref], derived_from=[product['id'], result_row['id']])
    refs = [record['id'], grading_ref, product['id'], grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': refs, 'record_refs': refs,
            'source_ref': record['id'], 'product_ref': product['id'], 'hits_asked': sheet['hits_asked'],
            'hits_with_sites': sheet['hits_with_sites'], 'candidates_measured': sheet['candidates_measured'],
            'candidates_without_site': sheet['candidates_without_site'], 'request_count': len(found['replies'])}


__all__ = ['PRODUCT_KIND', 'PROVIDER', 'REQUEST_FIELDS', 'annotation_settings',
           'check_site_correspondence_request', 'search_inputs', 'site_correspondence']
