"""A real held world for this episode: a Store with the problem, a reaction term and the proposed annotation (the claim),
the strategy's record of ONE query (a source whose ``request_ref`` artifact holds the request), the retained search
response that query returns when it is run (the provider call itself is no part of an offline test) and, when asked,
articles held in full; all passed to the entry Episode in custody."""
import json

from gene_annotation_episode.state import Store

FLAGS = ('assay_grading_population', 'ratio_source_population', 'controlled_response_population', 'gel_population',
         'completion_time_population', 'product_partition_population', 'active_site_population',
         'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population',
         'channel_population', 'ion_discrimination_population')
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'rate_population': False,
            **{name: False for name in FLAGS},
            'tool_registry': {'pdfinfo_executable': None, 'pdftotext_executable': None, 'pdftoppm_executable': None,
                              'job_limits': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
            'knowledge_library_directory': None, 'launch_instruction_directory': None}
# A real model run: each unit costs 0.1 credit, so the controller stops the Episode when its forecast yield of a
# further unit no longer exceeds that.
MODEL_SETTINGS = {**SETTINGS, 'cost': 0.1}


def hit(pmcid, pmid, doi, title):
    return {'id': pmid, 'source': 'MED', 'pmid': pmid, 'pmcid': pmcid, 'doi': doi, 'title': title,
            'journalInfo': {'journal': {'title': 'Journal of Tests'}}, 'pubYear': '2024',
            'abstractText': 'Abstract of ' + title + '.'}


# What a Europe PMC search returns (``public.literature.search`` retains it as one source): five entries, of which one has
# no PMCID (nothing to fetch), one repeats the first hit's PMCID and one is the same publication as the third by its DOI.
SEARCH_RESPONSE = {'version': '6.9', 'hitCount': 5, 'resultList': {'result': [
    hit('PMC100', '1', '10.1/a', 'PopZ binds ParB'),
    {'id': '2', 'source': 'MED', 'pmid': '2', 'doi': '10.1/b', 'title': 'No full text', 'abstractText': 'x'},
    hit('PMC100', '9', '10.1/z', 'PopZ binds ParB again'),
    hit('PMC300', '3', '10.1/c', 'A third article'),
    hit('PMC301', '4', '10.1/c', 'The third article, other record')]}}
HITS = ['PMC100', 'PMC300']
HIT_CANDIDATES = [
    {'result_id': 'PMC100', 'provider_rank': 1, 'title': 'PopZ binds ParB',
     'description': 'Journal of Tests, 2024. Abstract of PopZ binds ParB.'},
    {'result_id': 'PMC300', 'provider_rank': 2, 'title': 'A third article',
     'description': 'Journal of Tests, 2024. Abstract of A third article.'}]


def held_world(directory, held_articles=(), examined_articles=()):
    """The Store, the entry input of the episode at ``search_assignment_v1`` and the records the model would name.
    ``search_query_ref`` is the strategy's record of the query to run (``request``); ``search`` is the retained search
    response that query returns when it is run. ``held_articles`` are PMCIDs of articles held in full and
    ``examined_articles`` the held ones an earlier run's page examined (the assignment names them)."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    target = store.problem()['subject_refs'][0]
    scope = {'subject_refs': [target]}
    artifact = store.artifact('The question context.', 'text/plain')
    context = store.put('source', {'provider': 'synthetic_context', 'accession': None, 'uri': None,
                                   'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                   'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                        origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'hydrolysis', 'label': 'Hydrolysis',
                                  'term_type': 'reaction', 'source_ref': context, 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='reasoning')['id']
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    response = store.artifact(json.dumps(SEARCH_RESPONSE), 'application/json')
    search = store.put('source', {'provider': 'europepmc', 'accession': None,
                                  'uri': 'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                                  'artifact_ref': response, 'text_ref': None, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    query = store.artifact(json.dumps({'query': 'PopZ ParB binding assay', 'size': 25}), 'application/json')
    request = store.put('source', {'provider': 'europepmc_search_request', 'accession': None, 'uri': None,
                                   'artifact_ref': query, 'text_ref': None, 'request_ref': query,
                                   'version': None, 'retrieved_at': None}, origin='tool')['id']
    articles = []
    for pmcid in held_articles:
        full_text = store.artifact('Full text of ' + pmcid, 'text/plain')
        articles.append(store.put('source', {'provider': 'europepmc', 'accession': pmcid, 'uri': None,
                                             'artifact_ref': full_text, 'text_ref': full_text, 'request_ref': None,
                                             'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                                  origin='caller')['id'])
    held = [target, context, artifact, reaction, proposed, request, query, search, response, *articles]
    assignment = {'version': 'search_assignment_v1', 'question_context_refs': [context], 'search_query_ref': request,
                  'literature_task': task, 'proposed_annotation_ref': proposed, 'scope': scope,
                  'received_record_refs': held}
    if examined_articles:
        assignment['examined_article_refs'] = [ref for ref, pmcid in zip(articles, held_articles)
                                               if pmcid in examined_articles]
    names = {'store': store, 'target': target, 'context': context, 'reaction': reaction, 'proposed': proposed,
             'scope': scope, 'search': search, 'request': request, 'articles': articles}
    return {**names, 'input': {'assignment': assignment, 'message': {'objective': 'find the evidence'},
                               'selection': []}}
