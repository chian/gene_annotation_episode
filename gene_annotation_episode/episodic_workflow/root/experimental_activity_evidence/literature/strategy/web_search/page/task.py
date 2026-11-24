"""The task (nano-graphrag's page): the page of ONE paper that a search handed it for the claim.

Automatic units (code attached to a unit, no model call; ``decide`` returns the tool call itself):

- ``assess_content``: before the page plans, the paper's bytes are split into candidate input units (table regions and prose
  chunks), and Jev measures every candidate once against the information needs of the claim; this unit holds the
  assessment (``literature_page_content``, nano-graphrag ``PageChildProposer._ensure_content_assessment``).
- ``update_sheet`` (A105 scoring paradigm, OWNER_DECISION 10): whenever returned leaf records are not yet grouped, the
  leaf records the leaf children returned are grouped into graders and the persistent subscoring sheet, the credit and the
  per-annotation scores are updated. It is attached to the leaf's return, never a choice of the model.

The model's one choice: ONE leaf child per decision (``chunk``: one unconsumed prose chunk; ``table``: one unconsumed table
region; ``report``: every remaining prose chunk in document order) from Jev's assessment of the unconsumed candidates. The
page reads nothing, extracts nothing, commits no reasoning and has no other task: a leaf names the method it finds from the
relation the claim states (``messages/msg_to_child.py``). A candidate handed to a child is consumed and offered no more. With
no unconsumed candidate and no ungrouped record the page offers no unit; the page cannot end its Episode, only its yield
estimator does (``yield_estimator.py``)."""
import functools
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_claim import (
    PARTNER_VALUE_TYPES, claim_of_hypothesis, record_name)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_identity import (
    finalize_grader, group_leaf_records)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_page_update import (
    page_update)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    AXIS_CREDIT_CHANNEL)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    assess_page_content, page_candidates)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_subject_closeness import (
    subject_closeness)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_subject_resolution import (
    resolve_subject)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import JevDecisionClient
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting

CHILD_SLOTS = {
    'table': 'experimental_activity_evidence/literature/strategy/web_search/page/table',
    'report': 'experimental_activity_evidence/literature/strategy/web_search/page/report',
    'chunk': 'experimental_activity_evidence/literature/strategy/web_search/page/chunk',
}
# The service the BLAST comparison of the page's sheet update needs (A101's head declares it the same way). The page's settings
# hold ``blast_executable_directory`` (the directory that holds the BLAST programs, the key A101 uses) and ``blast_resource_id``
# (the bound local resource that runs them); ``literature_subject_closeness.subject_closeness`` reads both from ``ctx.settings``.
SERVICES = ('job_access',)
ASSESS = 'assess_content'
UPDATE = 'update_sheet'

CHILD_DESCRIPTIONS = {
    'table': (
        'A leaf extractor for ONE unconsumed table region of this paper (candidate_id): it reads the region, names every '
        'method able to support the claim that the region reports (or none) and extracts, for each one, exactly the inputs that '
        'method\'s grader needs, each with its quote. It grades and judges nothing and returns only the immutable leaf '
        'records. The region is consumed.'),
    'report': (
        'A leaf extractor that reads every remaining prose chunk of this paper in document order, window after window '
        '(consecutive chunks form one window), each once; for each window it names every method able to support the '
        'claim that the window reports (a window that reports none yields no record) and extracts, for each one, exactly the inputs '
        'that method\'s grader needs, each with its quote. It grades and judges nothing and returns only the immutable '
        'leaf records. The chunks it reads are consumed.'),
    'chunk': (
        'A leaf extractor: reads ONE unconsumed prose chunk of this paper (candidate_id), names every method able to '
        'support the claim that the chunk reports (or none) and extracts, for each one, exactly the inputs that method\'s grader '
        'needs, each with its quote. It grades and judges nothing and returns only the immutable leaf records. The chunk '
        'is consumed.'),
}
CANDIDATES_OF_SLOT = {'chunk': 'unconsumed_chunk_ids', 'table': 'unconsumed_table_ids'}

BRIEF = (
    'THIS EPISODE: page (A105 experimental evidence). One paper (context.literature_assignment: source_ref, '
    'representation) was found for ONE proposed annotation (context.commission.proposed_annotation_ref) whose claim states '
    'the relation context.claim_predicate (for example binds or catalyzes). You do not read the paper and you extract nothing: you choose which part of it '
    'a leaf child reads next. Whether the paper reports an experiment is what the children find out; you do not need to '
    'know it beforehand.\n'
    'THE PAGE\'S CANDIDATES: the paper was split into candidate input units: every table region detected in it '
    '(source_table:<id>) and the prose chunks of the running text between them (prose_chunk:<index>), each with its byte '
    'interval (context.content_candidates). Jev has measured every candidate once against the information needs of this '
    'claim (context.content_assessment.information_needs: the identity of the claim\'s molecules and its result). '
    'context.content_assessment shows, for the candidates not yet consumed only, the top needs of each table region, the '
    'best single chunk per need and the top chunks per need, each with Jev\'s probability that it could contribute. '
    'These probabilities are what you choose with. They do not admit evidence, assign credit or decide whether the page '
    'continues.\n'
    'YOUR CHOICE (context.child_options lists the children valid now, with what each would read): ONE leaf child per '
    'decision:\n'
    '- chunk: ONE unconsumed prose chunk (candidate_id).\n'
    '- table: ONE unconsumed table region (candidate_id), with the exact beginning of the region.\n'
    '- report: every remaining prose chunk read in document order, window after window, each once; the choice when '
    'useful pieces appear distributed across chunks.\n'
    'The child reads its window, names every method able to support the claim that the passage reports (or none, and then '
    'it returns no record) and fills the record form of each. You name no experiment type. A candidate handed to a '
    'child is consumed: it is not offered again and its probabilities are no longer shown. No child is compulsory and no '
    'order is prescribed.\n'
    'THE SHEET: the leaf records the children return are grouped into graders (one experiment = one grader; same document '
    'and experiment type merge unless a stated identity feature conflicts), converted, scored against the proposed '
    'annotation and used to update the persistent subscoring sheet, the main scoring sheet, the credit and the '
    'per-annotation scores. Code does this after a leaf returns records; you do not choose it. The credit of this episode '
    'is credit_unit times the largest credit any sheet update has reached so far (the latest is context.sheet_update): a '
    'later update can add to it and never takes from it. context.source_bytes is the byte length of '
    'the paper and context.covered_windows lists the byte windows (offset, end, experiment_type, slot) the leaf records '
    'already cover.\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit, the per-annotation scores and the features code reads '
                   'from the subscoring rows of your latest sheet update (evidence type, number of assays, '
                   'independent groups, relative deviation, support, opposition, net, status) and the references of '
                   'the persisted sheet states; no prose of yours and no raw record is returned. Selecting a child '
                   'does not end your work: only the numerical controller does.')


def available_slots(summary):
    """The child slots valid now (nano-graphrag ``PageChildProposer._valid_children``): chunk while an unconsumed prose
    chunk remains, table while an unconsumed table region remains, report while a remaining chunk can be read."""
    return [slot for slot in CHILD_SLOTS
            if (summary['report_windows'] if slot == 'report' else summary[CANDIDATES_OF_SLOT[slot]])]


def child_arguments(slot, summary):
    """The arguments a child takes now: for chunk and table, one unconsumed candidate of its kind; report takes none.
    No experiment type: the leaf names the method it reads."""
    if slot == 'report':
        return obj({})
    return obj({'candidate_id': {'enum': list(summary[CANDIDATES_OF_SLOT[slot]]),
                                 'description': 'One unconsumed candidate of context.content_candidates'}})


def selection_schema(summary):
    """What the model answers with: one valid child slot and its arguments; a chunk or table child names only an
    unconsumed candidate."""
    return obj({'selection': {'anyOf': [
        obj({'slot': {'const': slot}, 'arguments': child_arguments(slot, summary)}) for slot in available_slots(summary)]}})


def offered_actions(summary, ctx):
    """The action types offered at this decision, by the names the runner records. Before Jev has assessed the page's
    candidates the one action is ``assess_content``; while returned leaf records are not yet grouped it is
    ``update_sheet``; otherwise each child slot valid now (only for unconsumed candidates)."""
    if summary['content_assessment_ref'] is None:
        return [ASSESS]
    if summary['unused_leaf_record_refs']:
        return [UPDATE]
    return available_slots(summary)


def hypothesis_claim(store, hypothesis_ref):
    """The claim (predicate, subject, partner) of the proposed annotation's record, with the names read from the
    records it points at (``literature_claim.record_name``). A hypothesis that is no claim raises."""
    hypothesis = store.get(hypothesis_ref)
    refs = list(hypothesis['subject_refs'])
    if hypothesis['value']['type'] in PARTNER_VALUE_TYPES:
        refs.append(hypothesis['value']['ref'])
    return claim_of_hypothesis(hypothesis, {ref: record_name(store.get(ref)) for ref in refs})


def prior_sheet_state(store, state_refs):
    """The persistent subscoring sheet this page was given: {(sheet, assertion_ref): state}, one state per row."""
    prior = {}
    for ref in state_refs:
        held = json.loads(store.get_artifact(ref))
        key = (held['row']['sheet'], held['row']['assertion_ref'])
        if key in prior:
            raise ValueError(f'the sheet states passed to this page hold the row {key!r} twice')
        prior[key] = held
    return prior


async def update_sheet(arguments, ctx):
    """The page's update of the persistent subscoring sheet (OWNER_DECISION 10), automatic. Reads the immutable leaf records
    the leaf children returned and the sheet states passed in, groups the leaf records into graders (``group_leaf_records``:
    one experiment = one grader, default merge, split on a positive identity conflict), finalizes every grader
    (``finalize_grader``), and runs ``page_update`` (merged record, grade, convert, target match, relevance and direction against the claim of
    the proposed annotation, subscoring rows, main sheet, axis, credit, scores, features). Every call regroups ALL the leaf
    records from the states passed in, so a grader whose members grow is re-derived and never counted twice; the latest call
    is the page's whole result. The library functions are pure; this unit alone writes, through the custody store, each row
    state as an artifact (content-addressed; the row inside it carries its content-addressed ``row_ref``). The outcome holds
    controlled data only: the state references, the scores, the credit channel and the features."""
    store = ctx.store
    leaf_records = [json.loads(store.get_artifact(ref)) for ref in arguments['leaf_record_refs']]
    graders = [finalize_grader(grader) for grader in group_leaf_records(leaf_records)]
    by_ref = {record['experiment_ref']: record for record in leaf_records}
    items = [{'grader': grader, 'member_records': [by_ref[ref] for ref in grader['member_record_refs']]}
             for grader in graders]
    proposed = arguments['proposed_annotation_ref']
    update = await page_update(prior_sheet_state(store, arguments['base_state_refs']), items,
                               {proposed: hypothesis_claim(store, proposed)},
                               {proposed: store.get(proposed)['subject_refs'][0]},
                               functools.partial(resolve_subject, store), functools.partial(subject_closeness, ctx))
    state = update['sheet_state']
    refs = [store.artifact(canonical(state[key]), 'application/json') for key in sorted(state)]
    return {'status': 'completed',
            'sheet_update': {'sheet_state_refs': refs, 'grader_count': len(graders),
                             'scores': [update['scores'][name] for name in sorted(update['scores'])],
                             'credit': [{name: axis[name] for name in AXIS_CREDIT_CHANNEL} for axis in update['axis']],
                             'features': update['features']}}


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


TOOLS = {UPDATE: update_sheet, ASSESS: assess_content}


def child_options(summary):
    """The children valid now (nano-graphrag ``_valid_children``): slot, description, the arguments it takes and what it
    would read: for table each unconsumed region (byte interval, parser hint, exact beginning), for chunk each
    unconsumed prose chunk (byte interval), for report the windows of the remaining chunks in document order."""
    candidates = {item['candidate_id']: item for item in summary['content_candidates']}
    options = []
    for slot in available_slots(summary):
        if slot == 'report':
            reads = {'unprocessed_chunk_count': len(summary['unconsumed_chunk_ids']),
                     'reading_order': 'document_order', 'windows': summary['report_windows']}
        else:
            reads = {'candidates': [
                {'candidate_id': ref, 'start_offset': candidates[ref]['start'], 'end_offset': candidates[ref]['end'],
                 **({'parser_hint': candidates[ref]['parser_hint'],
                     'exact_table_beginning': summary['table_previews'][ref]} if slot == 'table' else {})}
                for ref in summary[CANDIDATES_OF_SLOT[slot]]]}
        options.append({'slot': slot, 'description': CHILD_DESCRIPTIONS[slot],
                        'arguments': child_arguments(slot, summary), 'reads': reads})
    return options


def decide(summary, feedback, ctx):
    """The page's decision. Before Jev has assessed the paper's candidates the decision is the assessment itself, and while
    returned leaf records are ungrouped it is the sheet update: both are tool calls made by code, no model call
    (nano-graphrag assesses before its page proposer is asked). Otherwise the model chooses ONE leaf child, shown the
    commission, the relation the claim states, the unconsumed candidates with Jev's assessment, what its children returned and
    the sheet; it is offered no tool."""
    if summary['content_assessment_ref'] is None:
        return ToolCall(ASSESS, {'source_ref': summary['page']['source_ref'],
                                 'representation': summary['page']['representation'],
                                 'goal': summary['jev_goal'], 'page_context': summary['jev_page_context'],
                                 'information_needs': summary['information_needs']})
    if summary['unused_leaf_record_refs']:
        return ToolCall(UPDATE, {'leaf_record_refs': summary['leaf_record_refs'],
                                 'base_state_refs': summary['base_state_refs'],
                                 'proposed_annotation_ref': summary['proposed_annotation_ref']})
    context = {'commission': summary['commission'], 'claim_predicate': summary['claim_predicate'],
               'literature_assignment': summary['literature_assignment'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'child_returns': summary['child_returns'], 'source_bytes': summary['source_bytes'],
               'covered_windows': summary['covered_windows'],
               'leaf_record_refs': summary['leaf_record_refs'], 'sheet_update': summary['sheet_update'],
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
