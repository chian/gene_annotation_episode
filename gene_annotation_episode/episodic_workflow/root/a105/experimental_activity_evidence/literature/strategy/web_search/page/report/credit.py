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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    classified_task_credit)
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
    return classified_task_credit(summary, records)


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (``arguments`` is not needed: the
    bound is over every arguments the action can take).

    The credit is ``credit_unit`` times a count of answers (for an ``a105_experiments`` task, times the sum of the
    graded shares, each at most 1, of the commissioned experiments' sheets). The count of answers can never pass
    ``answer_cap``: the number of distinct commissioned experiments for ``a105_experiments``, and one answer for
    every other task kind (screening, assessment, measurement, aggregation) because each of those looks for a single
    answer. So no unit can lift the credit above ``credit_unit * answer_cap``, and the rise is at most that less the
    credit already held (``headroom``).

    - Access tools (``state_query``, ``source_read``, ``source_locate``, ``source_pdf_*``, ``source_archive_*``,
      ``source_sequence_references``, ``source_experimental_records``): they save no sheet, assessment or lead and
      write no outcome that a credit answer reads, so they cannot earn: 0.
    - ``reason``: it saves the assessment and grading sheets, the no-applicable-evidence declarations that cover
      screening spans, and at most ONE source lead. For a ``verified_source_leads`` task (credit is
      ``credit_unit`` per relevant lead, no finite target) one unit adds at most one lead, so the ceiling is
      ``credit_unit``. For every other task kind it is ``headroom``.
    - Population operations (the ``*_populate`` tools and ``literature_a105_aggregate``), when the settings offer
      them: they save reader, grading or aggregation sheets, which can complete a measurement, grading or
      aggregation answer, so for those kinds the ceiling is ``headroom``. They write no lead and no screening
      declaration, so for ``verified_source_leads`` and for screening tasks they cannot earn: 0. A population
      operation the settings do not offer cannot be taken: 0."""
    from .task import ACCESS_NAMES, TOOL_NAMES, offered_populations
    task = summary['task']
    unit = task['credit_unit']
    access = {TOOL_NAMES[name] for name in ACCESS_NAMES}
    populations = {TOOL_NAMES[name] for name in offered_populations(ctx.settings)}
    if action_type in access:
        return 0
    if action_type == 'reason':
        if task['kind'] == 'verified_source_leads':
            return max(0, unit)
    elif action_type in populations:
        if task['kind'] == 'verified_source_leads' or task.get('answer_kind') == 'screening':
            return 0
    elif action_type in {TOOL_NAMES[name] for name in TOOL_NAMES}:
        return 0
    else:
        raise ValueError('ceiling_unknown_action_type')
    cap = (len({item['experiment_ref'] for item in task['experiments']}) if task['kind'] == 'a105_experiments'
           else 1)
    return max(0, unit * cap - credit(summary, records))
