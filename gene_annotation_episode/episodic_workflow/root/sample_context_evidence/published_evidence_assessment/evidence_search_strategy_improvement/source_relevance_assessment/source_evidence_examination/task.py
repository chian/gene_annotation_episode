"""The task (nano-graphrag's page): the page of ONE paper that a search handed it for the claim.

Automatic unit (code attached to a unit, no model call; ``decide`` returns the tool call itself):

- ``assess_content``: before the page plans, the paper's bytes are split into candidate input units (table regions and prose
  chunks), and Jev measures every candidate once against the information needs of the claim; this unit holds the
  assessment (``literature_page_content``, nano-graphrag ``PageChildProposer._ensure_content_assessment``).

The model's one choice: ONE leaf child per decision (``passage_evidence_extraction``: one unconsumed prose chunk;
``table_evidence_extraction``: one unconsumed table region; ``source_coverage_improvement``: every remaining prose chunk in
document order) from Jev's assessment of the unconsumed candidates. The page reads nothing, extracts nothing, commits no
reasoning and has no other task. A leaf grades what it extracted and saves its subscoring sheet in its own unit (the A108
sheets are the leaves'; the page has no sheet of its own to update). A candidate handed to a child is consumed and offered no
more. With no unconsumed candidate the page offers no unit; the page cannot end its Episode, only its yield estimator does
(``yield_estimator.py``)."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    assess_page_content, page_candidates)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import JevDecisionClient
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    canonical, obj, validate_schema)

CHILD_SLOTS = {
    'table_evidence_extraction': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction',
    'source_coverage_improvement': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement',
    'passage_evidence_extraction': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction',
}
SERVICES = ()
ASSESS = 'assess_content'
CANDIDATES_OF_SLOT = {'passage_evidence_extraction': 'unconsumed_chunk_ids',
                      'table_evidence_extraction': 'unconsumed_table_ids'}
CHILD_DESCRIPTIONS = {
    'table_evidence_extraction': (
        'A leaf extractor: reads ONE unconsumed table region of this paper (candidate_id, with the exact beginning of '
        'the region), extracts the organism-context observations it holds, grades them and saves its subscoring '
        'sheet. The region is consumed.'),
    'source_coverage_improvement': (
        'A leaf extractor that reads every remaining prose chunk of this paper in document order, extracts the '
        'organism-context observations it holds, grades them and saves its subscoring sheet. The chunks it reads are '
        'consumed.'),
    'passage_evidence_extraction': (
        'A leaf extractor: reads ONE unconsumed prose chunk of this paper (candidate_id), extracts the '
        'organism-context observations it holds, grades them and saves its subscoring sheet. The chunk is consumed.'),
}

BRIEF = (
    'THIS EPISODE: page (A108 organism-context evidence). One paper (context.literature_assignment: source_ref, '
    'representation) was found for ONE proposed annotation (context.commission.proposed_annotation_ref) and the organism '
    'context the caller supplied (context.commission.claim). You do not read the paper and you extract nothing: you '
    'choose which part of it a leaf child reads next. Whether the paper reports an organism-context observation is what '
    'the children find out; you do not need to know it beforehand.\n'
    'THE PAGE\'S CANDIDATES: the paper was split into candidate input units: every table region detected in it '
    '(source_table:<id>) and the prose chunks of the running text between them (prose_chunk:<index>), each with its byte '
    'interval (context.content_candidates). Jev has measured every candidate once against the information needs of this '
    'claim (context.content_assessment.information_needs: per kind of outside context, physiology, environment, '
    'availability and localization, the observation itself and the identity link to the supplied organism). '
    'context.content_assessment shows, for the candidates not yet consumed only, the top needs of each table region, the '
    'best single chunk per need group and the top chunks per need, each with Jev\'s probability that it could '
    'contribute. These probabilities are what you choose with. They do not admit evidence, assign credit or decide '
    'whether the page continues.\n'
    'YOUR CHOICE (context.child_options lists the children valid now, with what each would read): ONE leaf child per '
    'decision:\n'
    '- passage_evidence_extraction: ONE unconsumed prose chunk (candidate_id).\n'
    '- table_evidence_extraction: ONE unconsumed table region (candidate_id), with the exact beginning of the region.\n'
    '- source_coverage_improvement: every remaining prose chunk read in document order; the choice when useful pieces '
    'appear distributed across chunks.\n'
    'A candidate handed to a child is consumed: it is not offered again and its probabilities are no longer shown. No '
    'child is compulsory and no order is prescribed. The children grade what they extract and save the subscoring '
    'sheets; what they return is their credit, the controlled features of their sheets and the relevant source leads '
    '(context.child_reports).\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit, the controlled features code reads from the sheets your '
                   'children saved and the references the parent selected; no prose of yours and no raw record is '
                   'returned. Selecting a child does not end your work: only the numerical controller does.')


def available_slots(summary):
    """The child slots valid now (nano-graphrag ``PageChildProposer._valid_children``): the passage leaf while an
    unconsumed prose chunk remains, the table leaf while an unconsumed table region remains, the ordered reading while a
    remaining chunk can be read."""
    return [slot for slot in CHILD_SLOTS
            if (summary['report_windows'] if slot == 'source_coverage_improvement'
                else summary[CANDIDATES_OF_SLOT[slot]])]


def child_arguments(slot, summary):
    """The arguments a child takes now: for the passage and table leaves, one unconsumed candidate of their kind; the
    ordered reading takes none."""
    if slot == 'source_coverage_improvement':
        return obj({})
    return obj({'candidate_id': {'enum': list(summary[CANDIDATES_OF_SLOT[slot]]),
                                 'description': 'One unconsumed candidate of context.content_candidates'}})


def selection_schema(summary):
    """What the model answers with: one valid child slot and its arguments; a passage or table leaf names only an
    unconsumed candidate."""
    return obj({'selection': {'anyOf': [
        obj({'slot': {'const': slot}, 'arguments': child_arguments(slot, summary)}) for slot in available_slots(summary)]}})


def offered_actions(summary, ctx):
    """The action types offered at this decision, by the names the runner records. Before Jev has assessed the page's
    candidates the one action is ``assess_content``; otherwise each child slot valid now (only for unconsumed
    candidates)."""
    if summary['content_assessment_ref'] is None:
        return [ASSESS]
    return available_slots(summary)


async def assess_content(arguments, ctx):
    """The page's content assessment (nano-graphrag ``PageChildProposer._ensure_content_assessment`` with
    ``assess_page_content``): the paper's bytes are read through custody and split into the candidate input units
    (``page_candidates``, the same split the summary makes), Jev measures every candidate once against every
    information need of the claim, and this unit holds the assessment as an artifact the page keeps
    (``content_assessment_ref``). The library functions are pure; this unit alone writes. The Jev client reads its
    key (``TYPESAFE_API_KEY``) from the repository's ``.env`` at run time (``jev_client``); a missing key or a failed
    call raises."""
    content = representation_content(ctx.store, arguments['source_ref'], arguments['representation'])
    candidates = page_candidates(content)
    assessment = await assess_page_content(JevDecisionClient.from_repository_env(), goal=arguments['goal'],
                                           page_context=arguments['page_context'],
                                           needs=arguments['information_needs'], candidates=candidates,
                                           content=content)
    ref = ctx.store.artifact(canonical(assessment), 'application/json')
    return {'status': 'completed', 'assessment_ref': ref, 'candidate_count': len(candidates),
            'need_count': len(arguments['information_needs']), 'request_count': len(assessment['requests'])}


TOOLS = {ASSESS: assess_content}


def child_options(summary):
    """The children valid now (nano-graphrag ``_valid_children``): slot, description, the arguments it takes and what it
    would read: for the table leaf each unconsumed region (byte interval, parser hint, exact beginning), for the passage
    leaf each unconsumed prose chunk (byte interval), for the ordered reading the windows of the remaining chunks."""
    candidates = {item['candidate_id']: item for item in summary['content_candidates']}
    options = []
    for slot in available_slots(summary):
        if slot == 'source_coverage_improvement':
            reads = {'unprocessed_chunk_count': len(summary['unconsumed_chunk_ids']),
                     'reading_order': 'document_order', 'windows': summary['report_windows']}
        else:
            reads = {'candidates': [
                {'candidate_id': ref, 'start_offset': candidates[ref]['start'], 'end_offset': candidates[ref]['end'],
                 **({'parser_hint': candidates[ref]['parser_hint'],
                     'exact_table_beginning': summary['table_previews'][ref]}
                    if slot == 'table_evidence_extraction' else {})}
                for ref in summary[CANDIDATES_OF_SLOT[slot]]]}
        options.append({'slot': slot, 'description': CHILD_DESCRIPTIONS[slot],
                        'arguments': child_arguments(slot, summary), 'reads': reads})
    return options


def decide(summary, feedback, ctx):
    """The page's decision. Before Jev has assessed the paper's candidates the decision is the assessment itself: a tool
    call made by code, no model call (nano-graphrag assesses before its page proposer is asked). Otherwise the model
    chooses ONE leaf child, shown the commission, the unconsumed candidates with Jev's assessment and what its children
    returned; it is offered no tool."""
    if summary['content_assessment_ref'] is None:
        return ToolCall(ASSESS, {'source_ref': summary['page']['source_ref'],
                                 'representation': summary['page']['representation'],
                                 'goal': summary['jev_goal'], 'page_context': summary['jev_page_context'],
                                 'information_needs': summary['information_needs']})
    context = {'commission': summary['commission'], 'literature_assignment': summary['literature_assignment'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'child_reports': summary['child_reports'], 'finding': summary['finding'],
               'content_candidates': [item for item in summary['content_candidates']
                                      if item['candidate_id'] not in summary['consumed_candidate_ids']],
               'consumed_candidate_ids': summary['consumed_candidate_ids'],
               'content_assessment': summary['planner_context'], 'child_options': child_options(summary),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', BRIEF + RETURN_GUIDANCE, context, generation_schema(selection_schema(summary)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one child commission, or reject it (no unit). An answer that selects no valid slot or
    arguments that do not fit its schema is invalid. What the child commission names is not checked here: a wrong
    commission fails where the child is built."""
    schema = selection_schema(summary)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ChildCall(selection['slot'], selection['arguments'])
