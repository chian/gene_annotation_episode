"""Jev's measurement of a search parent's returned results and the planner's candidate view of them, ported from
nano-graphrag (axis-neutral: every evidence axis's search parent calls these with its own Search Goal and results).

nano-graphrag's Search parent (``question_pipeline/episode_binding/web_search_binding.py``; ``docs/ACQUISITION_LOOP.md``,
"Concretely, on the provider surface") obtains, once, one Jev relevance probability for each buffered search result from
its inline text and the immutable Search Goal (``assess_page_candidate``: one Noul question per request, the text cut into
windows so that the whole request stays within ``JEV_PAGE_TEXT_TOKEN_LIMIT``, the result's probability the maximum over
its windows) and persists that estimate per possible Page child (``PageCandidateAssessment``). On every pull it passes
its planning model every UNPROCESSED result's Jev measurement, provider rank and description and the compact measured
outcomes of the prior Page children (``SearchPageProposer._candidate_options``, ``propose_search_page``); the model
selects one result, which is consumed. Jev is planning evidence, not the selection policy
(``SEARCH_PAGE_SELECTION_VERSION``).

What differs here, and why:

- A result is ``{'result_id', 'provider_rank', 'title', 'description', 'text'}``: ``result_id`` is the id the parent's
  planner selects (nano-graphrag's ``option_id``), ``text`` is the result's held text (nano-graphrag's inline-scraped
  ``markdown``/``content``). As in nano-graphrag a result without text is measured on its description, and one with
  neither on the empty text (``text_source``).
- Token counts are the client's UTF-8 byte bound of ``o200k_base`` tokens (``jev_client.token_bound``), so the windows
  are only smaller than nano-graphrag's.
- The Jev client here has the multi-question ``nouls`` call; a request asks it the one named question nano-graphrag's
  ``noul`` asks.

Nothing here writes the Store; ``article_sources`` only reads through the custody reader it is handed. The parent
holds the assessment record it is handed. A search result is one hit of a provider's result list (``ranked_hits``),
not a fetched document."""
from __future__ import annotations

import json

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import (
    JEV_EVALUATION_TOKEN_BUDGET, JEV_TOKEN_BOUND, JEV_TOKEN_ESTIMATE_MULTIPLIER, JEV_TOKEN_HEADROOM, token_bound,
    window_text)

SEARCH_PAGE_SELECTION_VERSION = 'model_planned_from_jev_evidence_v5'      # nano-graphrag's version name
JEV_PAGE_TEXT_TOKEN_LIMIT = JEV_EVALUATION_TOKEN_BUDGET - JEV_TOKEN_HEADROOM   # nano-graphrag's limit
QUESTION = 'search_result_relevance'
INSTRUCTIONS = ('Does `candidate_text_window` contain evidence that could fill at least one result requested by '
                '`search_goal`, for an identifiable subject of that goal? Judge possible contribution to the declared '
                'result, not general topical similarity.')
CRITERIA = {
    'true': ('The text contains a reported value, an evidence-based basis for a permitted estimate, or '
             'identity/context needed to connect such a value to a requested subject.'),
    'false': 'The text cannot contribute any requested result even if it mentions the broad topic.'}
PLANNING_MEANING = ('Each unprocessed candidate carries its original provider rank and a Jev probability that the '
                    'result can contribute to the Search Goal. These are measurements for your planning, not a rule '
                    'that the largest probability must be selected. Use the candidate\'s title, description, provider '
                    'rank, Jev assessment and the realized results of previous Page children to choose the next result '
                    'worth processing. You choose which result to try; the numerical controller alone decides whether '
                    'the search continues.')


def _measured_text(result):
    """nano-graphrag's ``_candidate_text_source`` order: the held text, else the description, else empty."""
    for name in ('text', 'description'):
        value = str(result.get(name) or '')
        if value.strip():
            return value, name
    return '', 'empty'


def _candidate(result):
    """The compact candidate metadata Jev sees beside the window (nano-graphrag ``search_result_observation``)."""
    observation = {'result_id': str(result['result_id']), 'provider_rank': int(result['provider_rank']),
                   'title': str(result.get('title') or ''), 'description': str(result.get('description') or '')}
    return {key: value for key, value in observation.items() if value not in ('', None)}


def _questions():
    return {QUESTION: {'instructions': INSTRUCTIONS, 'criteria': dict(CRITERIA)}}


def _check(results):
    if not results:
        raise ValueError('search result assessment requires search results')
    ids = [str(result['result_id']) for result in results]
    ranks = [result['provider_rank'] for result in results]
    if len(set(ids)) != len(ids):
        raise ValueError('search result ids must be distinct')
    if any(isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0 for rank in ranks):
        raise ValueError('search result provider_rank must be a positive integer')
    if len(set(ranks)) != len(ranks):
        raise ValueError('search result provider ranks must be distinct')


async def _assess_one(jev, goal, result):
    """nano-graphrag ``assess_page_candidate`` for one result."""
    text, text_source = _measured_text(result)
    candidate = _candidate(result)

    def state_for(window, index, count):
        return {'search_goal': goal, 'candidate': candidate, 'candidate_text_window': window,
                'window_index': index, 'window_count': count}

    page_budget = JEV_PAGE_TEXT_TOKEN_LIMIT
    while True:
        windows = window_text(text, budget=page_budget) or ['']
        request_tokens = [jev.nouls_request_token_count(state=state_for(window, index, len(windows)),
                                                        questions=_questions())
                          for index, window in enumerate(windows, start=1)]
        # One question per request: bounding the whole request bounds its shared state plus question.
        overflow = max(request_tokens) - JEV_PAGE_TEXT_TOKEN_LIMIT
        if overflow <= 0:
            break
        if not text or page_budget <= overflow:
            raise ValueError('Jev Search assessment metadata exceeds its '
                             f'{JEV_PAGE_TEXT_TOKEN_LIMIT:,}-token packing target before result text can be included')
        page_budget -= max(1, int(overflow / JEV_TOKEN_ESTIMATE_MULTIPLIER))
    probabilities, models, input_tokens, output_tokens, attempts = [], [], 0, 0, 0
    for index, window in enumerate(windows, start=1):
        decision = await jev.nouls(state=state_for(window, index, len(windows)), questions=_questions())
        probabilities.append(float(decision.probabilities[QUESTION]))
        models.append(decision.response.model)
        input_tokens += decision.response.input_tokens
        output_tokens += decision.response.output_tokens
        attempts += decision.response.attempts
    return {'result_id': candidate['result_id'], 'provider_rank': candidate['provider_rank'],
            'title': str(result.get('title') or ''), 'description': str(result.get('description') or ''),
            'relevance_probability': max(probabilities), 'window_probabilities': probabilities,
            'window_token_counts': [token_bound(window) for window in windows], 'token_encoding': JEV_TOKEN_BOUND,
            'model_ids': list(dict.fromkeys(models)), 'input_tokens': input_tokens, 'output_tokens': output_tokens,
            'attempts': attempts, 'text_source': text_source, 'text_chars': len(text),
            'text_tokens': token_bound(text)}


async def assess_search_results(jev, *, goal, results):
    """Measure every search result once against the immutable Search Goal ``goal`` (a JSON mapping), before the
    parent plans; the assessment record the parent holds. ``results`` is a list of ``{'result_id', 'provider_rank',
    'title', 'description', 'text'}``; ``jev`` is a ``JevDecisionClient``."""
    results = list(results)
    _check(results)
    assessments = [await _assess_one(jev, dict(goal), result) for result in results]
    return {'version': SEARCH_PAGE_SELECTION_VERSION, 'token_bound': JEV_TOKEN_BOUND,
            'text_token_limit': JEV_PAGE_TEXT_TOKEN_LIMIT, 'question': {'instructions': INSTRUCTIONS,
                                                                       'criteria': dict(CRITERIA)},
            'search_goal': dict(goal),
            'assessments': sorted(assessments, key=lambda item: item['provider_rank'])}


def search_planner_context(assessment, unconsumed_ids, prior_outcomes):
    """nano-graphrag's candidate view (``SearchPageProposer._candidate_options`` and the ``propose_search_page``
    inputs) over the held assessment record: the unconsumed results only, in provider-rank order, each with its provider
    rank, title, description and Jev measurement, and the compact measured outcomes of the prior Page children
    (``prior_outcomes``, passed as given). An unconsumed id the assessment does not hold raises."""
    held = {item['result_id']: item for item in assessment['assessments']}
    allowed = list(dict.fromkeys(str(value) for value in unconsumed_ids))
    missing = [value for value in allowed if value not in held]
    if missing:
        raise ValueError('search planner context names unassessed results: ' + ', '.join(missing))
    candidates = sorted((held[value] for value in allowed), key=lambda item: item['provider_rank'])
    return {'selection_version': assessment['version'], 'meaning': PLANNING_MEANING,
            'result_buffer': {'buffered_results': len(held), 'assessed_results': len(held),
                              'processed_results': len(held) - len(candidates),
                              'unprocessed_results': len(candidates)},
            'unprocessed_page_candidates': [
                {'option_id': item['result_id'], 'provider_rank': item['provider_rank'], 'title': item['title'],
                 'description': item['description'],
                 'jev_assessment': {'relevance_probability': item['relevance_probability'],
                                    'window_probabilities': list(item['window_probabilities']),
                                    'text_source': item['text_source'], 'text_tokens': item['text_tokens']}}
                for item in candidates],
            'previous_page_children': [dict(item) for item in prior_outcomes]}


# ---------------------------------------------------------------------------------------------------------------
# The unit of a search result: ONE HIT of a provider's result list (nano-graphrag: one Firecrawl result), never a
# whole fetched document and never the response that holds the list. The functions below read the hits out of the
# retained Europe PMC search responses (the sources ``public.literature.search`` stores) and say which articles a
# Store already holds in full (and under which source), so a held article is opened without a second fetch.
# ---------------------------------------------------------------------------------------------------------------
SEARCH_PROVIDER = 'europepmc'
SEARCH_URI = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
IDENTIFIERS = ('pmcid', 'pmid', 'doi')


def is_search_response(source):
    """Whether a source record is a retained Europe PMC search response (a hit list), not a fetched article."""
    return source['provider'] == SEARCH_PROVIDER and source['uri'] == SEARCH_URI


def is_article(source):
    """Whether a source record is a fetched article: a full text (``public.literature.read``) of a publication, which
    carries its PMCID as the accession and a text representation."""
    return (source['provider'] == SEARCH_PROVIDER and not is_search_response(source) and bool(source['accession'])
            and bool(source['text_ref']))


def source_kind(source):
    """What a source record is for the search route: ``search_response`` (a provider's hit list), ``article`` (a fetched
    full text with a PMCID) or ``other`` (for example a PMC file listing or version listing, or a caller's file)."""
    if is_search_response(source):
        return 'search_response'
    return 'article' if is_article(source) else 'other'


def provider_hits(content):
    """The hits of one retained search response, in the provider's order. A hit carries its identifiers, title,
    journal, year and the abstract the provider returned. Only a hit with a PMCID is an item: the PMCID is what the
    full-text fetch (``public.literature.read``) takes."""
    hits = []
    for entry in json.loads(content)['resultList']['result']:
        if not entry.get('pmcid'):
            continue
        hits.append({'pmcid': entry['pmcid'], 'pmid': entry.get('pmid'), 'doi': entry.get('doi'),
                     'title': entry.get('title') or '',
                     'journal': ((entry.get('journalInfo') or {}).get('journal') or {}).get('title') or '',
                     'year': str(entry.get('pubYear') or ''), 'abstract': entry.get('abstractText') or ''})
    return hits


def ranked_hits(contents):
    """The distinct publications of the retained responses ``contents`` (bytes, in the order the parent holds them),
    each once, with its provider rank: the 1-based position in the order they were returned. Two hits that share any
    identifier (PMCID, PMID or DOI) are one publication and the first keeps its rank."""
    seen = {name: set() for name in IDENTIFIERS}
    ranked = []
    for content in contents:
        for hit in provider_hits(content):
            if any(hit[name] in seen[name] for name in IDENTIFIERS if hit[name]):
                continue
            for name in IDENTIFIERS:
                if hit[name]:
                    seen[name].add(hit[name])
            ranked.append({**hit, 'provider_rank': len(ranked) + 1})
    return ranked


def article_sources(records):
    """The articles ``records`` (a custody reader) already holds in full: for each PMCID the source references (sorted)
    of the sources ``public.literature.read`` stored (accession the PMCID, a text representation). Holding an article
    is not the work done on it: whether a page examined it is carried as record references by the episodes."""
    held = {}
    for ref in sorted(records.refs()):
        if not ref.startswith('source_'):
            continue
        source = records.get(ref)
        if source['provider'] == SEARCH_PROVIDER and source['accession'] and source['text_ref']:
            held.setdefault(source['accession'], []).append(ref)
    return held


def hit_candidate(hit):
    """One hit as a possible page child: its id (the PMCID the planner selects), its provider rank, its title and its
    description (journal, year and the abstract the provider returned, which Jev measures when the result has no
    other text, as nano-graphrag does)."""
    return {'result_id': hit['pmcid'], 'provider_rank': hit['provider_rank'], 'title': hit['title'],
            'description': f"{hit['journal']}, {hit['year']}. {hit['abstract']}"}


__all__ = ['JEV_PAGE_TEXT_TOKEN_LIMIT', 'SEARCH_PAGE_SELECTION_VERSION', 'article_sources',
           'assess_search_results', 'hit_candidate', 'is_article', 'is_search_response', 'provider_hits', 'ranked_hits',
           'search_planner_context', 'source_kind']
