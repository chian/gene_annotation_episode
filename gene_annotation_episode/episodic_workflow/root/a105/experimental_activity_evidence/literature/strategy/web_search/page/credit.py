"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission
(the old ``credit.py``: ``credit_kind`` 'scientific', ``credit_projector`` ``LiteratureTaskCredit``), computed by the
library's ``literature_task_answers.classified_task_credit`` over this episode's summary and held records. Per task
kind the answers are: the relevant source leads (``verified_source_leads``); the screening of every commissioned span
(``screening``); one current anchored retained assessment (``assessment``); a populated quantity sheet of the
commissioned selection (``measurement``); one aggregation sheet over the commissioned experiments
(``a105_assembly``); and for ``a105_experiments`` the current grading sheet of each commissioned experiment, matched
to a current assessment, which earns the share of the unit its fields earn.

The credit of a grading sheet rests on the classification of the fields it leaves unknown, not on the sheet existing
(owner, 19 November 2026; AGENTS.md "Required literature evidence processing"). A field the grading entered earns its
share. A field it left unknown (a null quantity, a null prediction model, a criterion ``unknown``) earns its share
when the classification holds it justified (the source windows the Episode read do not state it: the partial or
unresolved grading a missing measurement requires) and nothing when it holds it unjustified (those windows state it:
the grading missed it) or when no classification is held. A sheet of nothing but unjustified unknowns earns nothing.
Never bounded, clamped or rescaled.

``classify_unknowns`` makes that classification. It is credit assignment and is automatic: the unit that saves a
sheet (``task.py`` ``reason``) calls it as its tail, the model never selects it and no tool offers it. It is one typed
model call per sheet through ``ctx.model`` (recorded with the unit and replayed), answered in a closed schema (one of
``justified`` / ``unjustified`` per unknown field, validated by code) and saved as a record the Episode holds.
``credit`` stays a pure read of the summary and the held records."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    answers, classified_task_credit)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    classification_record, classification_request, classification_result, unknown_fields, window_texts)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)


async def classify_unknowns(outcome, scope, windows, ctx):
    """The tail of a grading unit: classify the unknown fields of each sheet the unit saved against ``windows`` (the
    spans of the source this Episode read) and save each result as a held record. ``outcome`` is the unit's outcome;
    it is returned with ``unknown_classifications`` (per sheet: the sheet, the saved record, the status of each
    unknown field). A sheet that leaves no field unknown has nothing to classify, and without a read window there is
    nothing to classify against: its unknown fields stay unclassified and earn nothing."""
    processing = outcome.get('evidence_processing')
    if processing is None or processing['kind'] != 'graded':
        return outcome
    texts, repository, classified = window_texts(ctx.store, windows), LiteratureAssayGradingRepository(ctx.store), []
    for grading in processing['gradings']:
        sheet_ref = grading['result']['sheet_ref']
        selection = repository.read(sheet_ref)['selection']
        if not unknown_fields(selection) or not texts:
            continue
        request = classification_request(sheet_ref, selection, texts)
        answer = await ctx.model.complete('REASONING', request['instructions'], request['context'],
                                          generation_schema(request['output_schema']))
        result = classification_result(sheet_ref, selection, decode_response(answer, request['output_schema']))
        record = ctx.store.put('source', classification_record(ctx.store.artifact(canonical(result),
                                                                                  'application/json')),
                               origin='tool', scope=scope)
        classified.append({'sheet_ref': sheet_ref, 'classification_ref': record['id'], 'fields': result['fields']})
    return {**outcome, 'unknown_classifications': classified}


def credit(summary, records):
    """For an ``a105_experiments`` task the credit is ``credit_unit`` times the larger of two measures of progress: the
    best credit of a leaf child, ``chunk``, ``table`` or ``report`` (the share of the asked fields it newly stated: the uncertainty it lessened) and the
    credit of the page's latest sheet update (A105 scoring paradigm, OWNER_DECISION 10: the update of the subscoring sheet
    produces the credit in the same step: the change of the resolution R of the rows, then of 1 - mean R over the
    commissioned classes at the main level, for the commissioned candidate). A repeat of a held fact earns nothing. Every
    update regroups all the leaf records from the states the page was given, so the latest update is the page's whole
    sheet credit, not an increment. The other task kinds keep the library's classified task credit."""
    task = summary['task']
    if task['kind'] != 'a105_experiments':
        return classified_task_credit(summary, records)
    update = summary['sheet_update']
    # The chunk's own progress counts: when a leaf extractor states fields of the experiment, the uncertainty about it has
    # lessened, whether or not the sheet has been updated yet (the share of the asked fields it newly stated). The page's
    # credit is the larger of that and the sheet update's credit, so it never falls when the update comes (EXPERT_REVIEW:
    # owner's choice of how the two measures of progress combine).
    leaf = max((child['credit'] for child in summary['child_returns']), default=0.0)   # every child is a leaf extractor
    sheet = 0.0 if update is None else math.fsum(item['credit'] for item in update['credit'])
    value = task['credit_unit'] * max(leaf, sheet)
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the episode's credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over
    every arguments that type can take now). The bound does not depend on the arguments or on ``ctx``. ``action_type`` is the name
    the runner records: a tool name (``task.TOOLS``) or a child slot (``task.CHILD_SLOTS``); any other name raises.

    a105_experiments task. The credit is ``credit_unit`` times the larger of the best leaf child credit and the latest
    ``update_sheet`` credit, each at most 1: a leaf's credit is a share of its asked fields (newly stated / asked; for
    ``report`` half a share of windows plus half such a share), and the sheet credit is the one axis of the one commissioned
    candidate (``page_update`` is handed one claim and ``merge_main`` refuses any other candidate's row), the mean over its
    commissioned classes of R(after) - R(before) with R in [0, 1]. So the credit is at most ``credit_unit`` and a rise is
    at most ``credit_unit`` minus the credit held now (not below 0). This bound is ``yield_estimator.CEILING_VERSION``. Only a leaf child, ``chunk``, ``table`` or ``report`` (its credit is a share of fields stated), and
    ``update_sheet`` (with a leaf record held; without one a sheet update cannot exist) can raise it; every other action
    (tools, ``reason``) has ceiling 0.

    Every other task kind: the credit is ``credit_unit`` for each answer, and a task holds at most one answer
    (``verified_source_leads``: one per relevant source). The tail ``classify_unknowns`` of ``reason`` earns nothing for
    these kinds. The children are leaf extractors: they return no lead, no screening and no sheet, so their ceiling is 0.
    verified_source_leads: one ``reason`` carries at most one source lead and so changes at most one source's
    disposition: ceiling ``credit_unit``; the access tools, population operations and ``update_sheet`` produce none: 0.
    screening: answered once the commissioned spans are covered, by a ``reason`` declaring no applicable evidence:
    ``credit_unit`` if not covered now, else 0; other actions 0.
    assessment, measurement, a105_assembly: one answer, a retained assessment, a quantity sheet or an aggregation
    sheet, saved by ``reason`` or a population operation: ``credit_unit`` times (1 - answers held now) for those actions
    (a loose bound: it does not tell which of them can make this kind's record), 0 for the access tools, the children
    and ``update_sheet``."""
    from . import task as episode_task
    if action_type not in episode_task.TOOLS and action_type not in episode_task.CHILD_SLOTS:
        raise ValueError('ceiling_unknown_action_type:' + repr(action_type))
    task = summary['task']
    unit = task['credit_unit']
    populations = {episode_task.TOOL_NAMES[name] for name in episode_task.POPULATIONS}
    if task['kind'] == 'a105_experiments':
        if action_type in episode_task.CHILD_SLOTS or (action_type == 'update_sheet'
                                                      and summary['unused_leaf_record_refs']):
            return max(0.0, unit - credit(summary, records))
        return 0.0
    remaining = unit * (1 - len(answers(summary, records)))
    if task['kind'] == 'verified_source_leads':
        return float(unit) if action_type == 'reason' else 0.0
    if task.get('answer_kind') == 'screening':
        return float(remaining) if action_type == 'reason' else 0.0
    if action_type == 'reason' or action_type in populations:
        return float(max(0.0, remaining))
    return 0.0
